import os
import json
import random
import re
import time

from flask import Flask, request, jsonify

import requests
import cloudscraper
from bs4 import BeautifulSoup
from readability import Document

# Optional JS-rendering fallback.
try:
    from requests_html import HTMLSession
    HAS_REQUESTS_HTML = True
except ImportError:
    HAS_REQUESTS_HTML = False

# --- SQLAlchemy Setup ---
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func, exists
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.dialects.postgresql import JSONB

POSTGRES_URL = os.environ.get("POSTGRES_URL")
engine = create_engine(POSTGRES_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# --- Redis Setup ---
import redis
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)

# --- (Optional) Embedding Setup ---
def compute_embedding(text):
    return json.dumps([random.random() for _ in range(5)])

# --- Define the Persistence Model ---
class ScrapedResult(Base):
    __tablename__ = 'scraped_results'
    id = Column(Integer, primary_key=True)
    query = Column(String, index=True)
    title = Column(Text)
    url = Column(Text, unique=True, index=True)
    description = Column(Text)
    engine_name = Column(String)
    searxng_json = Column(JSONB)
    extracted_content = Column(Text)
    embedding = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

Base.metadata.create_all(engine)

# --- Flask Application ---
app = Flask(__name__)

# --- User-Agent Rotation ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
]
def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com",
    }

# --- Cleaning Helpers ---
def remove_cookie_banners(text):
    cookie_patterns = [r'we use cookies', r'cookie policy', r'accept all', r'reject all', r'gdpr', r'privacy settings']
    cleaned_lines = []
    for line in text.splitlines():
        lw = line.lower()
        if len(line.split()) < 15 and any(re.search(pat, lw) for pat in cookie_patterns):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def remove_navigation(text):
    nav_phrases = ["log in", "sign up", "menu", "what can i help with"]
    cleaned_lines = []
    for line in text.splitlines():
        lw = line.lower().strip()
        if any(phrase in lw for phrase in nav_phrases) and len(lw.split()) <= 5:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

def clean_extracted_text(text):
    text = remove_cookie_banners(text)
    text = remove_navigation(text)
    return text.strip()

def is_valid_content(text, min_words=50):
    words = text.split()
    return len(words) >= min_words and not text.lower().startswith(("we use cookies", "cookie policy"))

# --- Scraping Strategies ---
def strategy_requests(url):
    return requests.get(url, headers=get_random_headers(), timeout=15).text

def strategy_cloudscraper(url):
    scraper = cloudscraper.create_scraper()
    return scraper.get(url, headers=get_random_headers(), timeout=15).text

def strategy_requests_html(url):
    session = HTMLSession()
    r = session.get(url, headers=get_random_headers(), timeout=15)
    r.html.render(timeout=20)
    return r.html.html

def extract_article(html):
    try:
        doc = Document(html)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, "lxml")
        content = soup.get_text(separator='\n', strip=True)
    except Exception:
        content = ""
    if len(content.split()) < 50:
        soup = BeautifulSoup(html, "lxml")
        content = soup.get_text(separator='\n', strip=True)
    return clean_extracted_text(content)

def try_scrape(url):
    strategies = [strategy_requests, strategy_cloudscraper]
    if HAS_REQUESTS_HTML:
        strategies.append(strategy_requests_html)
    
    for strat in strategies:
        try:
            app.logger.debug(f"Trying {strat.__name__} for {url}")
            html = strat(url)
            article = extract_article(html)
            if is_valid_content(article):
                return article
        except Exception as e:
            app.logger.debug(f"{strat.__name__} failed: {str(e)}")
        time.sleep(1)
    return "Failed to extract valid content."

# --- Persistence & Caching ---
def persist_result(query, result, scraped_content):
    db_session = SessionLocal()
    try:
        embedding = compute_embedding(scraped_content)
        new_result = ScrapedResult(
            query=query,
            title=result.get("title", "No Title")[:500],
            url=result.get("url"),
            description=result.get("content", "No Description")[:1000],
            engine_name=result.get("engine", "Unknown"),
            searxng_json=result,
            extracted_content=scraped_content[:10000],
            embedding=embedding
        )
        db_session.add(new_result)
        db_session.commit()
        redis_client.set(f"scraped:{new_result.url}", 1, ex=86400)  # Cache for 24h
    except Exception as e:
        db_session.rollback()
        app.logger.error(f"DB error: {str(e)}")
    finally:
        db_session.close()

def get_existing_urls(urls):
    db_session = SessionLocal()
    existing = db_session.query(ScrapedResult.url).filter(ScrapedResult.url.in_(urls)).all()
    db_session.close()
    return {url for (url,) in existing}

def compress_results(results):
    unique_lines = set()
    for result in results:
        unique_lines.update(result.extracted_content.splitlines())
    return "\n".join(unique_lines)

# --- Core Logic ---
def search_and_scrape(query):
    SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8081/search")
    params = {"q": query, "format": "json", "count": 20, "engines": "google,bing,duckduckgo"}
    
    try:
        response = requests.get(SEARXNG_URL, params=params, headers=get_random_headers(), timeout=15)
        response.raise_for_status()
        results = response.json().get("results", [])
    except Exception as e:
        app.logger.error(f"SearxNG Error: {str(e)}")
        return []

    urls = [res["url"] for res in results if res.get("url")]
    existing_urls = get_existing_urls(urls)
    
    for result in results:
        url = result.get("url")
        if not url:
            continue
            
        if redis_client.exists(f"scraped:{url}") or url in existing_urls:
            app.logger.info(f"Skipping processed URL: {url}")
            continue
            
        app.logger.info(f"Processing new URL: {url}")
        content = try_scrape(url)
        if "Failed" not in content:
            persist_result(query, result, content)
            redis_client.set(f"scraped:{url}", 1, ex=86400)
        time.sleep(1)  # Be polite

# --- Flask Endpoints ---
@app.route("/scrape", methods=["GET"])
def scrape_query():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter"}), 400
    
    redis_key = f"results:{query}"
    cached = redis_client.get(redis_key)
    if cached:
        return jsonify({"query": query, "data": cached.decode()})
    
    search_and_scrape(query)
    
    db_session = SessionLocal()
    results = db_session.query(ScrapedResult).filter(ScrapedResult.query.ilike(f"%{query}%")).all()
    db_session.close()
    
    compressed = compress_results(results)
    if compressed:
        redis_client.setex(redis_key, 300, compressed)
    
    return jsonify({"query": query, "data": compressed})

@app.route("/results", methods=["GET"])
def get_results():
    query = request.args.get("q", "")
    db_session = SessionLocal()
    results = db_session.query(ScrapedResult).filter(ScrapedResult.query.ilike(f"%{query}%")).limit(50).all()
    db_session.close()
    return jsonify([{
        "title": r.title,
        "url": r.url,
        "content": r.extracted_content[:500] + "..." if len(r.extracted_content) > 500 else r.extracted_content
    } for r in results])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("DEBUG", "false").lower() == "true")
