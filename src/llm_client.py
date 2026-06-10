import os
import json
import time
import random
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI

class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        load_dotenv()
        aws_key = os.getenv("AWS_API_KEY")
        if aws_key:
            print("Using AWS Bedrock")
            self.api_key = aws_key.strip()
            self.base_url = "https://bedrock-mantle.us-east-1.api.aws/v1"
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.model = "deepseek.v3.1"
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("Neither AWS_API_KEY nor OPENAI_API_KEY found in environment.")
            self.client = OpenAI(api_key=self.api_key)
            self.model = "gpt-4.1"

    def call_llm_json(self, prompt: str, system_message: str = "You are a helpful assistant.", temperature: float = 0.1, max_retries: int = 5, base_delay: float = 1.0) -> Dict[str, Any]:
        """
        Queries the LLM API with JSON Mode (if not Bedrock) and handles rate limits (429) using exponential backoff with jitter.
        Returns the parsed JSON dictionary.
        """
        is_bedrock = hasattr(self, "base_url") and "bedrock-mantle" in self.base_url

        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "timeout": 30.0
                }
                # Bedrock Mantle has issues with response_format, so we only pass it for OpenAI
                if not is_bedrock:
                    kwargs["response_format"] = {"type": "json_object"}

                response = self.client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content.strip()
                
                # Robustly clean markdown block markers if present
                if content.startswith("```json"):
                    content = content[7:]
                elif content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()
                
                return json.loads(content)
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "rate_limit" in err_msg.lower() or "rate limit" in err_msg.lower():
                    # Calculate exponential backoff with random jitter
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"  [!] LLM Rate limit hit (Attempt {attempt+1}/{max_retries}). Retrying in {delay:.2f}s...")
                    time.sleep(delay)
                    continue
                else:
                    print(f"  [-] LLM Call failed: {e}")
                    raise e
                    
        raise RuntimeError("Max retries exceeded for LLM call.")

# Central client instance (lazy initialized or instantiated directly)
_client_instance = None

def get_llm_client(api_key: Optional[str] = None) -> LLMClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = LLMClient(api_key)
    return _client_instance


# Example usage:
if __name__ == "__main__":
    client = get_llm_client()
    response = client.call_llm_json("What is the capital of France?")
    print(response)
