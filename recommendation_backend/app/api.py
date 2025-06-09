# recommendation_backend/app/api.py 
from fastapi import APIRouter, HTTPException, Body
from app.services.recommendation_service import get_company_recommendation_data, recommend_rewards_for_company, create_new_reward_service, recommend_rewards_for_chat
from pydantic import BaseModel  
from typing import List, Dict, Any, Optional 
import logging 
from app.redis.redis_cache_module import invalidate_cache 

router = APIRouter() 

# --- Request and Response Models (Pydantic) --- 
class RecommendationRequest(BaseModel): 
    company_name: str 

class RecommendationResponse(BaseModel): 
    company_name: str 
    recommended_rewards: List[Dict[str, Any]]  

class RewardRequest(BaseModel): 
    company_name: str 
    reward_name: str 
    custom_reward_tags: Optional[List[str]] = None  

class RewardResponse(BaseModel): 
    reward_id: int 
    reward_name: str 
    company_name: str 
    reward_tags: List[str] 

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    response: str


@router.post("/recommendations/", response_model=RecommendationResponse)  
async def get_recommendations(request_body: RecommendationRequest): 
    """ 
    Endpoint to get reward recommendations for a given company. 
    """ 
    company_name = request_body.company_name.strip()  
    if not company_name: 
        raise HTTPException(status_code=400, detail="Company name cannot be empty.") 

    company_data = get_company_recommendation_data(company_name)  
    if not company_data: 
        raise HTTPException(status_code=404, detail=f"Could not retrieve or generate data for company: {company_name}. Recommendation unavailable.") 

    recommended_rewards = recommend_rewards_for_company(company_data)  

    return RecommendationResponse(company_name=company_name, recommended_rewards=recommended_rewards)  


@router.post("/chat/", response_model=ChatResponse)
async def chat_endpoint(request_body: ChatRequest):
    """
    Endpoint that accepts a user chat question, computes its embedding,
    finds the top reward recommendations based on cosine similarity,
    and passes the context to an LLM endpoint for generating a response.
    """
    question = request_body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    recommended_rewards = recommend_rewards_for_chat(question)
    if not recommended_rewards:
        raise HTTPException(status_code=404, detail="No reward recommendations available for the given question.")

    context_lines = []
    for reward in recommended_rewards:
        tags = reward["reward_tags"]
        if isinstance(tags, list):
            tags = ", ".join(tags)
        context_lines.append(f"Company: {reward['company_name']}, Reward: {reward['reward_name']}, Tags: {tags}")
    context = "\n".join(context_lines)

    prompt = f"Based on the following reward details:\n{context}\nAnswer the question: {question}"

    return ChatResponse(response=prompt)

@router.post("/rewards/", response_model=RewardResponse) 
async def create_reward(reward_request: RewardRequest): 
    """ 
    Endpoint to add a new reward associated with a company. 
    """ 
    company_name = reward_request.company_name.strip() 
    reward_name = reward_request.reward_name.strip() 
    custom_reward_tags = reward_request.custom_reward_tags if reward_request.custom_reward_tags else []  

    if not company_name: 
        raise HTTPException(status_code=400, detail="Company name cannot be empty.") 
    if not reward_name: 
        raise HTTPException(status_code=400, detail="Reward name cannot be empty.") 

    reward_data = await create_new_reward_service(company_name, reward_name, custom_reward_tags)  

    if not reward_data: 
        raise HTTPException(status_code=500, detail="Failed to create reward.") 

    return RewardResponse(**reward_data)


@router.post("/invalidate-cache/")
async def invalidate_cache_endpoint(company_name: str = Body(..., embed=True)):
    """
    Endpoint to invalidate the cache for a specific company.
    Expects a JSON body like: {"company_name": "Some Company"}
    """
    if not company_name:
        raise HTTPException(status_code=400, detail="company_name is required")

    invalidate_cache(f"company_data:{company_name}")
    logging.info(f"Cache invalidated for {company_name} via API endpoint.")
    return {"message": f"Cache invalidated for {company_name}"}
