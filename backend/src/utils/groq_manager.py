import json
import os
from dotenv import load_dotenv
load_dotenv()
from groq import Groq
import tenacity
from tenacity import retry, stop_after_attempt, wait_exponential
from langsmith import traceable
from src.config.config import Config
from src.system.logger import setup_logger
from src.common.credential_provider import CredentialFactory, Credential, RateLimitException, AuthException

logger = setup_logger("GroqManager")

def retry_if_transient_error(exception):
    error_str = str(exception).lower()
    if any(x in error_str for x in ["400", "401", "403", "invalid api key", "unauthorized"]):
        return False # Fail immediately
    return True # Retry on 429, 500, timeouts, etc.

class GroqManager:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GroqManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.credentials = CredentialFactory.get("GROQ")
        self.token_usage = {
            "intelligence": 0,
            "generation": 0,
            "critic": 0
        }

    def reset_tokens(self):
        self.token_usage = {"intelligence": 0, "generation": 0, "critic": 0}

    # traceable outermost (not between this and @retry) -- one trace per
    # logical chat_completion() call, with tenacity's internal retries
    # folded into that single span's latency, rather than one trace per
    # individual retry attempt. No-op (zero overhead, no network call)
    # unless LANGSMITH_TRACING=true and LANGSMITH_API_KEY are set.
    @traceable(run_type="llm", name="groq_chat_completion")
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), retry=tenacity.retry_if_exception(retry_if_transient_error))
    def chat_completion(self, model: str, messages: list, temperature: float = 0.2, response_format: dict = None, stage: str = "generation") -> dict:
        """
        Executes a chat completion. Uses tenacity for exponential backoff.
        If a 429 Rate Limit is hit, the credential provider automatically rotates to the next available API key.
        """
        def fetch(credential: Credential):
            # Groq client instances are cheap, but ideally we'd cache them in Credential.config. 
            # For now, we can just instantiate one per request or use a cached one.
            client = credential.config.get("client")
            if not client:
                client = Groq(api_key=credential.secret)
                credential.config["client"] = client
                
            try:
                # Ensure the word 'json' is in messages if response_format is json_object
                call_messages = list(messages)
                if response_format and response_format.get("type") == "json_object":
                    has_json_word = any("json" in m.get("content", "").lower() for m in call_messages)
                    if not has_json_word:
                        call_messages[0] = {
                            "role": call_messages[0]["role"],
                            "content": call_messages[0]["content"] + "\n\nRespond with valid JSON only."
                        }

                kwargs = {
                    "model": model,
                    "messages": call_messages,
                    "temperature": temperature
                }
                if response_format:
                    kwargs["response_format"] = response_format
                    
                try:
                    response = client.chat.completions.create(**kwargs)
                except Exception as e_json:
                    if "json_validate_failed" in str(e_json).lower() or "400" in str(e_json):
                        # Retry without response_format and rely on prompt instructions
                        kwargs.pop("response_format", None)
                        response = client.chat.completions.create(**kwargs)
                    else:
                        raise e_json
                return response
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "rate limit" in error_str.lower():
                    raise RateLimitException(error_str)
                elif any(x in error_str.lower() for x in ["401", "403", "unauthorized", "invalid api key"]):
                    raise AuthException(error_str)
                raise e
                
        response = self.credentials.execute_sync(fetch)
        
        # Track tokens
        if hasattr(response, 'usage') and response.usage:
            tokens = response.usage.total_tokens
            if stage in self.token_usage:
                self.token_usage[stage] += tokens
                
        return response
