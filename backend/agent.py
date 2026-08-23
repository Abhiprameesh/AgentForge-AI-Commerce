from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI

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

base_llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7
)

import time
class RateLimitedLLM:
    def __init__(self, base_llm):
        self.base_llm = base_llm
    
    def invoke(self, *args, **kwargs):
        retries = 6
        delay = 5.0
        for i in range(retries):
            try:
                return self.base_llm.invoke(*args, **kwargs)
            except Exception as e:
                err_str = str(e)
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower():
                    print(f"\n⚠️ Rate Limit hit. Retrying in {delay} seconds (Attempt {i+1}/{retries})...")
                    time.sleep(delay)
                    delay *= 1.8  # Backoff factor
                else:
                    raise e
        # Try one last time
        return self.base_llm.invoke(*args, **kwargs)

llm = RateLimitedLLM(base_llm)