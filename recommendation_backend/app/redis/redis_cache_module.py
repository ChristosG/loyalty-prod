# recommendation_backend/app/redis/redis_cache_module.py 
import os 
import redis 
from app.core.config import settings  
import json  
from app.db.db_module import get_db_session, CompanyData  

REDIS_HOST = settings.redis_host 
REDIS_PORT = settings.redis_port 
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0) 

def get_cached_data(key): 
    """Retrieves data from Redis cache.""" 
    cached_value = redis_client.get(key) 
    return cached_value.decode('utf-8') if cached_value else None 

def set_cached_data(key, value, expiry=86400 * 7):  
    """Sets data in Redis cache with optional expiry.""" 
    redis_client.setex(key, expiry, value) 

def invalidate_cache(key_pattern): 
    """Invalidates cache entries matching a key pattern (prefix*).""" 
    keys_to_delete = redis_client.keys(key_pattern) 
    if keys_to_delete: 
        redis_client.delete(*keys_to_delete) 
        print(f"Invalidated cache keys matching pattern: {key_pattern}") 
    else: 
        print(f"No cache keys found matching pattern: {key_pattern}") 

def clear_all_cache(): 
    """Clears all data in Redis cache (use with caution!).""" 
    redis_client.flushdb() 
    print("All Redis cache cleared.") 


def populate_redis_from_postgres_company_data(): 
    """ 
    Populates Redis with CompanyData from PostgreSQL. 
    """ 
    db_session = get_db_session()  
    try: 
        companies = db_session.query(CompanyData).all() 
        for company in companies: 
            cache_key = f"company_data:{company.company_name}" 
            company_data_dict = {  
                "company_name": company.company_name, 
                "tags": company.tags, 
                "tag_embeddings": company.tag_embeddings.tolist(), 
                "last_updated_at": company.last_updated_at.isoformat() if company.last_updated_at else None, 
            } 
            set_cached_data(cache_key, json.dumps(company_data_dict), expiry=86400 * 7)  
        print(f"Populated Redis cache with {len(companies)} CompanyData entries.") 
    except Exception as e: 
        print(f"Error populating Redis from Postgres CompanyData: {e}") 
    finally: 
        db_session.close()
