# kafka_consumer/Dockerfile
FROM python:3.9

WORKDIR /app

COPY kafka_consumer.py .
RUN pip install kafka-python requests

CMD ["python", "kafka_consumer.py"]