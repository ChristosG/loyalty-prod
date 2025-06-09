# recommendation_backend/app/scraping/scraper_module.py 
import os 
import json
import random 
import re 
import time 
import requests 
import cloudscraper 
from bs4 import BeautifulSoup 
from readability import Document 


try: 
    from requests_html import HTMLSession
    HAS_REQUESTS_HTML = True 
except ImportError: 
    HAS_REQUESTS_HTML = False 

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
    if not HAS_REQUESTS_HTML: 
        raise ImportError("requests-html is not installed. Cannot use strategy_requests_html.") 
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
            print(f"Trying {strat.__name__} for {url}")  
            html = strat(url) 
            article = extract_article(html) 
            if is_valid_content(article): 
                return article, strat.__name__ 
        except Exception as e: 
            print(f"{strat.__name__} failed: {str(e)}")
        time.sleep(1) 
    return "Failed to extract valid content.", None 


def search_and_scrape(query):  
    from app.core.config import settings 
    SEARXNG_URL = settings.searxng_url 
    params = {"q": query, "format": "json", "count": 8, "engines": "google"} 
    try: 
        response = requests.get(SEARXNG_URL, params=params, headers=get_random_headers(), timeout=15) 
        response.raise_for_status() 
        results = response.json().get("results", []) 
    except Exception as e: 
        print(f"SearxNG Error: {str(e)}")  
        return [], []  

    urls = [res["url"] for res in results if res.get("url")] 
    return results, urls
