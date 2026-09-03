import os
import time
import requests
import json
from dotenv import load_dotenv

from tools import (
    get_current_time,
    motivational_quote,
    resume_tip,
    generate_ml_interview_question,
    web_search,
    analyze_resume
)

load_dotenv()

tools = [
    get_current_time,
    motivational_quote,
    resume_tip,
    generate_ml_interview_question,
    web_search,
    analyze_resume
]

import hashlib

class DirectGeminiClient:
    def __init__(self, api_key: str, model: str = "gemini-3.6-flash"):
        self.api_key = api_key
        self.model = model
        self.cache_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "llm_cache.json")
        self.cache = {}
        self._load_cache()
        
    def _load_cache(self):
        try:
            if os.path.exists(self.cache_path):
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
        except Exception as e:
            print(f"Error loading LLM cache: {e}")
            self.cache = {}

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving LLM cache: {e}")

    def _call_api(self, prompt_text: str, model_name: str) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        payload = {
            "contents": [{
                "parts": [{"text": prompt_text}]
            }]
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 404:
            raise LookupError(f"Model {model_name} not found")
            
        if response.status_code == 503 or "UNAVAILABLE" in response.text:
            raise LookupError(f"Model {model_name} currently unavailable")
            
        if response.status_code != 200:
            raise Exception(f"Gemini API Error (Status {response.status_code}): {response.text}")
            
        res_json = response.json()
        try:
            return res_json["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise Exception(f"Failed to parse Gemini response: {res_json}. Error: {e}")

    def invoke(self, prompt, **kwargs):
        # Translate LangChain prompt object if passed
        if hasattr(prompt, "to_messages"):
            prompt_text = "\n".join([m.content for m in prompt.to_messages()])
        elif isinstance(prompt, list):
            prompt_text = "\n".join([m.content if hasattr(m, "content") else str(m) for m in prompt])
        else:
            prompt_text = str(prompt)
            
        model_to_use = self.model
        
        # Check cache
        cache_key = hashlib.sha256(f"{model_to_use}:{prompt_text}".encode("utf-8")).hexdigest()
        if cache_key in self.cache:
            text = self.cache[cache_key]
            class MockResponse:
                def __init__(self, content):
                    self.content = content
            return MockResponse(text)
            
        retries = 6
        delay = 5.0
        last_exception = None
        
        for i in range(retries):
            try:
                text = self._call_api(prompt_text, model_to_use)
                
                # Update and save cache
                self.cache[cache_key] = text
                self._save_cache()
                
                # Mock LangChain response object
                class MockResponse:
                    def __init__(self, content):
                        self.content = content
                return MockResponse(text)
                
            except LookupError as e:
                # If model is genuinely not found or unavailable, raise lookup error
                raise e
                    
            except Exception as e:
                last_exception = e
                err_str = str(e)
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower():
                    print(f"\n⚠️ Rate Limit hit. Retrying in {delay} seconds (Attempt {i+1}/{retries})...")
                    time.sleep(delay)
                    delay *= 1.8
                else:
                    raise e
                    
        if last_exception:
            raise last_exception
        raise Exception("Failed to invoke LLM after multiple attempts.")

# Initialize global LLM client
api_key = os.getenv("GOOGLE_API_KEY")
llm = DirectGeminiClient(api_key=api_key, model="gemini-3.6-flash")