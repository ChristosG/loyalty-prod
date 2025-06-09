# recommendation_backend/app/main.py 
from fastapi import FastAPI 
from app.api import router as api_router 
import logging 
from app.redis.redis_cache_module import populate_redis_from_postgres_company_data 
from app.db.db_module import get_db_session, CompanyData, db_setup  

logging.basicConfig(level=logging.INFO)  

app = FastAPI(title="Reward Recommendation Backend") 

app.include_router(api_router) 

@app.get("/healthcheck") 
async def health_check(): 
    return {"status": "OK"} 

db_setup() 
db_session = get_db_session() 

try: 
    if db_session.query(CompanyData).first(): 
        populate_redis_from_postgres_company_data() 
except Exception as e: 
    logging.error(f"Error during initial Redis population: {e}") 
finally: 
    db_session.close() 

if __name__ == "__main__": 
    import uvicorn 
    uvicorn.run(app, host="0.0.0.0", port=8123, reload=False)
