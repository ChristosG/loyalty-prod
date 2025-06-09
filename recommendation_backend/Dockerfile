# recommendation_backend/Dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install gunicorn==23.0.0 uvicorn==0.34.0 uvicorn[all]  
RUN pip install lxml[html_clean]==5.3.1
RUN pip install lxml_html_clean==0.4.1
RUN pip install langchain==0.3.19
RUN pip install pgvector==0.3.6
RUN pip install tavily-python==0.5.1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8123"]
#CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8123"]