# recommendation_backend/app/db/db_module.py 
import os 
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func, exists 
from sqlalchemy.ext.declarative import declarative_base 
from sqlalchemy.orm import sessionmaker, scoped_session 
from sqlalchemy.dialects.postgresql import JSONB 
from app.core.config import settings
from pgvector.sqlalchemy import Vector 

POSTGRES_URL = settings.postgres_url 
engine = create_engine(POSTGRES_URL) 
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False) 
Base = declarative_base() 

def get_db_session(): 
    """Function to get a database session.""" 
    return scoped_session(SessionLocal) 

# --- Define CompanyData Model --- 
class CompanyData(Base): 
    __tablename__ = 'company_data' 
    id = Column(Integer, primary_key=True) 
    company_name = Column(String, unique=True, index=True)  
    tags = Column(JSONB)
    tag_embeddings = Column(Vector(384)) 
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()) 

class Reward(Base): 
    __tablename__ = 'rewards' 
    id = Column(Integer, primary_key=True) 
    reward_name = Column(String, index=True) 
    company_name = Column(String, index=True) 
    reward_tags = Column(JSONB) 
    reward_tag_embeddings = Column(Vector(384))
    created_at = Column(DateTime(timezone=True), server_default=func.now()) 


def db_setup(): 
    Base.metadata.create_all(engine)
