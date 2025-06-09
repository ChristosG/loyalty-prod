# scraper/Dockerfile
FROM python:3.9-slim

WORKDIR /app

RUN pip install Flask requests cloudscraper beautifulsoup4 readability-lxml sqlalchemy psycopg2-binary redis requests-html kafka-python sentence-transformers
RUN pip install lxml[html_clean]
RUN pip install lxml_html_clean
# Copy requirements first for cache efficiency.
#COPY requirements.txt .

# Install Python dependencies.
#RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application.
COPY . .

EXPOSE 5000

CMD ["python", "scraper.py"]
