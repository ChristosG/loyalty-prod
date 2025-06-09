# recommendation_backend/app/llm/llm_module.py
import os
import logging
from typing import Optional, List
import requests
from langchain.llms.base import LLM
from langchain.callbacks.manager import CallbackManagerForLLMRun
from transformers import AutoTokenizer
import json # Import json for JSON handling
import re
from app.core.config import settings # Import settings
from pydantic import BaseModel, Extra

LLAMA_MODEL_NAME = settings.llm_model_name
TRITON_SERVER_URL = settings.triton_server_url
TOKENIZER_PATH = settings.tokenizer_path

class TritonLLM(LLM): 
    llm_url: str = f"http://{TRITON_SERVER_URL}/v2/models/{LLAMA_MODEL_NAME}/generate"
    class Config:
        extra = 'forbid'  

    @property 
    def _llm_type(self) -> str:
        return "Triton LLM"
    def _call(
        self,
        prompt: str,
        temperature: float,
        stop: Optional[list] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> str: 
        if stop is not None:
            raise ValueError("stop kwargs are not permitted.") 
        payload = { 
            "text_input": prompt, 
            "parameters": { 
                "max_tokens": 16384, 
                "temperature": temperature, 
                "top_k": 50,
                "repetition_penalty": 1.1,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.1,
            } 
        } 
        headers = {"Content-Type": "application/json"} 
        try: 
            response = requests.post(self.llm_url, json=payload, headers=headers) 
            response.raise_for_status() 
            translation = response.json().get('text_output', '') 
            if not translation:
                raise ValueError("No 'text_output' field in the response.")
            return translation 
        except requests.exceptions.RequestException as e:
            logging.error(f"LLM request failed: {e}") 
            return "" 
        except ValueError as ve:
            logging.error(f"LLM response error: {ve}") 
            return "" 
    @property
    def _identifying_params(self) -> dict:
        return {"llmUrl": self.llm_url}

llm = TritonLLM() 

try: 
    tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_PATH)
    logging.info("Tokenizer loaded successfully in llm_module.")
except Exception as e:
    logging.error(f"Failed to load tokenizer in llm_module: {e}")
    exit(1)




def extract_json_from_response(response: str) -> dict:
    """
    Attempt to extract and parse a JSON object from the LLM response, even if
    it has extra text, code fences, or other noise. Returns an empty dict if unable to parse.
    """

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        pass  

    fenced_match = re.search(r"```json(.*)```", response, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        fenced_content = fenced_match.group(1).strip()
        try:
            return json.loads(fenced_content)
        except json.JSONDecodeError:
            pass

    brace_match = re.search(r"\{[\s\S]*\}", response)
    if brace_match:
        json_snippet = brace_match.group(0)
        try:
            return json.loads(json_snippet)
        except json.JSONDecodeError:
            pass

    return {}

def askLLM_for_tags_json(company_name: str, scrap: str) -> Optional[List[str]]:
    """
    Asks the LLM to generate tags for a company based on scraped text and returns tags as a JSON list.
    Handles potential JSON parsing errors and ensures a list of tags is always returned (even if empty on error).
    """
    messages = [
        {
            "role": "system",
            "content": f"""
            Analyze the following text describing the company '{company_name}'. 
            Identify 10 keywords or short phrases that best describe this company. 
            Focus on aspects relevant to consumers, such as industry, products/services, customer type, and brand attributes.
            Please dont include specific information such as telephone numbers or emails, but include addresses or if you are able instead add a city, town or country where this company opperates. Use maximum 2 tags to specify location.
            Tags should be concise, lowercase, and descriptive, mostly describing what this company is, what is its sector, or what categories are best describing this company.
            After analyzing and arriving at your conclusion, respond with a JSON object like {{ "tags": [...] }}.

            *Please never provide any explanation or any other information but just the JSON in the structure: {{ "tags" : [tags] }}*
            *Generate up to 10 tags, then finish and return the JSON.*
            *ENSURE the response is VALID JSON always.*
            """
        },
        {
            "role": "user",
            "content": f"Please generate 10 tags in a JSON format, for the company: {company_name}, based on this online scraped data: {scrap}"
        }
    ]

    prompt = tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    llm_advice_str = llm(prompt=prompt, temperature=0.1)

    print(llm_advice_str)

    if not llm_advice_str:
        logging.warning(f"LLM returned empty response for company: {company_name}. Returning empty tags.")
        return []

    advice_json = extract_json_from_response(llm_advice_str)
    tags = advice_json.get("tags", [])

    if not isinstance(tags, list):
        logging.error(
            f"LLM JSON response 'tags' is not a list. "
            f"Response was: {llm_advice_str}. Parsed JSON was: {advice_json}. "
            "Returning empty tags."
        )
        return []

    return tags
