# recommendation_backend/app/core/config.py
import os

class Settings:
    postgres_url: str = os.environ.get("POSTGRES_URL", "postgresql://user:password@localhost:5432/mydatabase")
    redis_host: str = os.environ.get("REDIS_HOST", "localhost")
    redis_port: int = int(os.environ.get("REDIS_PORT", 6379))
    searxng_url: str = os.environ.get("SEARXNG_URL", "http://localhost:8080/search")
    llm_model_name: str = os.environ.get("LLM_MODEL_NAME", "ensemble") 
    triton_server_url: str = os.environ.get("TRITON_SERVER_URL", 'localhost:8000') 
    tokenizer_path: str = os.environ.get("TOKENIZER_PATH", '/mnt/nvme512/engines/DeepSeek-R1-Distill-Llama-8B/') # "/mnt/nvme512/engines/Meta-Llama-3.1-8B-Instruct") 

settings = Settings()
