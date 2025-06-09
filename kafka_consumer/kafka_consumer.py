# kafka_consumer.py
from kafka import KafkaConsumer
import json
import logging
import requests  # Import the requests library

# Assuming your backend is accessible as 'recommendation-backend' on port 8123
BACKEND_URL = "http://recommendation-backend:8123/invalidate-cache/"

logging.basicConfig(level=logging.INFO)

def consume_kafka_messages():
    consumer = KafkaConsumer(
        'dbserver1.public.company_data',  
         bootstrap_servers=['kafka:29092'],
         auto_offset_reset='earliest',
         enable_auto_commit=True,
         group_id='my-group',
         value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    for message in consumer:
        try:
            company_name = message.value.get('after', {}).get('company_name')
            if company_name:
                # Call the backend API to invalidate the cache
                response = requests.post(BACKEND_URL, json={"company_name": company_name})
                response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
                logging.info(f"Sent invalidation request for {company_name}. Response: {response.json()}")

        except Exception as e:
            logging.error(f"Error processing Kafka message: {e}")

if __name__ == '__main__':
    consume_kafka_messages()




