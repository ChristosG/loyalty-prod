# recommendation_backend/app/services/recommendation_service.py
import json
import logging
from app.db.db_module import get_db_session, CompanyData, Reward
from app.redis.redis_cache_module import get_cached_data, set_cached_data, invalidate_cache
from app.scraping.scraper_module import search_and_scrape, try_scrape
from app.llm.llm_module import askLLM_for_tags_json
from sentence_transformers import SentenceTransformer
import torch
import torch.nn.functional as F
from typing import List, Optional, Dict, Any
import abc
import os  
from tavily import TavilyClient  


# --- Embedding Setup ---
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

# --- Strategy Selection ---
STRATEGY = 1 

TAVILY_API_KEY = ""

if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY environment variable not set.")
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)


class ScrapingStrategy(abc.ABC):
    """Abstract base class for scraping strategies."""

    @abc.abstractmethod
    def scrape_company_data(self, company_name: str) -> Optional[str]:
        """Scrapes data for the given company.

        Args:
            company_name: The name of the company to scrape.

        Returns:
            Combined scraped content as a string, or None if scraping fails.
        """
        pass


class OriginalScrapingStrategy(ScrapingStrategy):
    """Strategy using the original scraping logic."""

    def scrape_company_data(self, company_name: str) -> Optional[str]:
        search_results, _ = search_and_scrape(company_name)
        if not search_results:
            logging.warning(f"No search results for '{company_name}'.")
            return None

        combined_content = ""
        for result in search_results:
            url = result.get('url')
            if url:
                content, _ = try_scrape(url)
                if "Failed" not in content:
                    combined_content += content + "\n\n---\n\n"

        if not combined_content:
            logging.warning(f"Failed to scrape content for '{company_name}'.")
            return None

        return combined_content


class AlternativeScrapingStrategy(ScrapingStrategy):
    """Uses Tavily for searching, with fallback to original strategy."""

    def scrape_company_data(self, company_name: str) -> Optional[str]:
        logging.info(f"Using AlternativeScrapingStrategy (Tavily) for '{company_name}'")
        try:
            response = tavily_client.search(
                query=company_name,
                search_depth="advanced",
                include_answer="advanced",
                max_results=5  
            )
            answer = response.get('answer', 'No answer provided.')
            if answer != "No answer provided.":
                logging.info(f"Tavily found an answer for '{company_name}'")
                return answer 

            else:
                logging.warning(f"Tavily did not provide an answer for '{company_name}'. Falling back to original strategy.")
                original_strategy = OriginalScrapingStrategy()
                return original_strategy.scrape_company_data(company_name)


        except Exception as e:
            logging.error(f"Error during Tavily search for '{company_name}': {e}. Falling back to original strategy.")
            original_strategy = OriginalScrapingStrategy()
            return original_strategy.scrape_company_data(company_name)



def compute_embedding(text):
    embedding_vector = embedding_model.encode(text, convert_to_tensor=True)
    return embedding_vector.tolist() 


def get_company_recommendation_data(company_name: str):
    """Retrieves or generates company data, prioritizing Redis."""
    cache_key = f"company_data:{company_name}"
    cached_data_str = get_cached_data(cache_key)
    if cached_data_str:
        logging.info(f"Data found in Redis cache for '{company_name}'.")
        return json.loads(cached_data_str)

    db_session = get_db_session()
    try:
        company_data = db_session.query(CompanyData).filter(CompanyData.company_name == company_name).first()
        if company_data:
            logging.info(f"Data found in PostgreSQL for '{company_name}'. Updating Redis.")
            company_data_dict = {
                "company_name": company_data.company_name,
                "tags": company_data.tags,
                "tag_embeddings": company_data.tag_embeddings.tolist(),  # Convert to list
                "last_updated_at": company_data.last_updated_at.isoformat() if company_data.last_updated_at else None,
            }
            set_cached_data(cache_key, json.dumps(company_data_dict))
            return company_data_dict

        # --- Scraping and Processing (Strategy Pattern) ---
        logging.info(f"No data found for '{company_name}'. Scraping and processing.")

        if STRATEGY == 0:
            scraping_strategy = OriginalScrapingStrategy()
        elif STRATEGY == 1:
            scraping_strategy = AlternativeScrapingStrategy()
        else:
            raise ValueError(f"Invalid STRATEGY value: {STRATEGY}")

        combined_content = scraping_strategy.scrape_company_data(company_name)

        if not combined_content:
            logging.warning(f"Failed to scrape content for '{company_name}'.")
            return None

        generated_tags = askLLM_for_tags_json(company_name, combined_content)
        if not generated_tags:
            return None
        tag_embeddings = compute_embedding(" ".join(generated_tags))

        # Persist to PostgreSQL
        try:
            company_data = CompanyData(
                company_name=company_name,
                tags=generated_tags,
                tag_embeddings=tag_embeddings
            )
            db_session.add(company_data)
            db_session.commit()
            logging.info(f"Processed data persisted for '{company_name}'.")

            # Update Redis
            company_data_dict = {
                "company_name": company_data.company_name,
                "tags": company_data.tags,
                "tag_embeddings": company_data.tag_embeddings.tolist(),
                "last_updated_at": company_data.last_updated_at.isoformat() if company_data.last_updated_at else None,
            }
            set_cached_data(cache_key, json.dumps(company_data_dict))
            return company_data_dict

        except Exception as e:
            db_session.rollback()
            logging.error(f"Error persisting data: {e}")
            return None

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None
    finally:
        db_session.close()

async def create_new_reward_service(company_name: str, reward_name: str, custom_reward_tags: List[str] = None):
    """Creates a new reward, using provided tags or company tags."""
    db_session = get_db_session()
    try:
        company_data = get_company_recommendation_data(company_name)
        if not company_data:
            logging.error(f"Company '{company_name}' not found. Cannot create reward.")
            return None

        reward_tags = custom_reward_tags if custom_reward_tags else company_data["tags"]
        reward_tag_embeddings = compute_embedding(" ".join(reward_tags))

        new_reward = Reward(
            reward_name=reward_name,
            company_name=company_name,
            reward_tags=reward_tags,
            reward_tag_embeddings=reward_tag_embeddings
        )
        db_session.add(new_reward)
        db_session.commit()
        logging.info(f"Reward '{reward_name}' created for '{company_name}'.")

        return {
            "reward_id": new_reward.id,
            "reward_name": new_reward.reward_name,
            "company_name": new_reward.company_name,
            "reward_tags": new_reward.reward_tags,
        }

    except Exception as e:
        db_session.rollback()
        logging.error(f"Error creating reward: {e}")
        return None
    finally:
        db_session.close()

def recommend_rewards_for_company(company_data):
    """Recommends rewards based on cosine similarity."""
    if not company_data:
        return []

    company_embeddings = torch.tensor(company_data.get("tag_embeddings"))
    if company_embeddings.numel() == 0:
        logging.warning("Company embeddings are empty.")
        return []

    db_session = get_db_session()
    try:
        all_rewards = db_session.query(Reward).all()
        if not all_rewards:
            logging.warning("No rewards found in the database.")
            return []

        recommendations = []
        for reward in all_rewards:
            reward_embeddings = torch.tensor(reward.reward_tag_embeddings)
            if reward_embeddings.numel() == 0:
                continue

            try:
                similarity = F.cosine_similarity(company_embeddings, reward_embeddings, dim=0).item()
                recommendations.append({
                    "reward_id": reward.id,
                    "reward_name": reward.reward_name,
                    "company_name": reward.company_name,
                    "similarity_score": similarity
                })
            except Exception as e:
                logging.error(f"Error calculating similarity for reward {reward.id}: {e}")
                continue

        recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
        return recommendations[:5]

    except Exception as e:
        logging.error(f"Error during recommendation: {e}")
        return []
    finally:
        db_session.close()

def recommend_rewards_for_chat(question: str) -> List[Dict[str, Any]]:
    """
    Recommends rewards based on cosine similarity between the embedding
    of the chat question and reward_tag_embeddings stored in the database.
    """
    question_embedding = compute_embedding(question)
    question_embedding = torch.tensor(question_embedding)
    
    db_session = get_db_session()
    try:
        all_rewards = db_session.query(Reward).all()
        if not all_rewards:
            logging.warning("No rewards found in the database.")
            return []

        recommendations = []
        for reward in all_rewards:

            reward_embedding = torch.tensor(reward.reward_tag_embeddings)
            if reward_embedding.numel() == 0:
                continue

            try:
                logging.info(f" sims {question_embedding}, {reward_embedding}")
                similarity = F.cosine_similarity(question_embedding, reward_embedding, dim=0).item()
                recommendations.append({
                    "reward_id": reward.id,
                    "reward_name": reward.reward_name,
                    "company_name": reward.company_name,
                    "reward_tags": reward.reward_tags,
                    "similarity_score": similarity
                })
            except Exception as e:
                logging.error(f"Error calculating similarity for reward {reward.id}: {e}")
                continue

        recommendations.sort(key=lambda x: x['similarity_score'], reverse=True)
        return recommendations[:5]
    finally:
        db_session.close()
