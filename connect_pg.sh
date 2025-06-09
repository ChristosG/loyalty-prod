docker exec -it my-scraper-app-postgres-1 psql -U user -d mydatabase

curl -X POST http://localhost:8084/connectors \
     -H "Content-Type: application/json" \
     -d @debezium-connector.json
