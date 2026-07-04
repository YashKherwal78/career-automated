import json
from groq import Groq
from src.config.config import Config

class GroqManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GroqManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.keys = list(set(Config.GROQ_KEYS))  # Remove duplicates
        if not self.keys:
            raise ValueError("No GROQ_KEYS found in configuration.")
        
        self.clients = [Groq(api_key=key) for key in self.keys]
        self.active_index = 0
        self.token_usage = {
            "intelligence": 0,
            "generation": 0,
            "critic": 0
        }

    def reset_tokens(self):
        self.token_usage = {"intelligence": 0, "generation": 0, "critic": 0}

    def get_active_client(self) -> Groq:
        return self.clients[self.active_index]

    def rotate_key(self):
        self.active_index = (self.active_index + 1) % len(self.clients)
        print(f"[GroqManager] Rotated to API Key {self.active_index + 1}/{len(self.clients)}")

    def chat_completion(self, model: str, messages: list, temperature: float = 0.2, response_format: dict = None, stage: str = "generation") -> dict:
        """
        Executes a chat completion. If a 429 Rate Limit is hit, it automatically 
        rotates to the next available API key and retries until all keys are exhausted.
        """
        attempts = 0
        max_attempts = len(self.clients)

        while attempts < max_attempts:
            client = self.get_active_client()
            try:
                kwargs = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature
                }
                if response_format:
                    kwargs["response_format"] = response_format
                    
                response = client.chat.completions.create(**kwargs)
                
                # Track tokens
                if hasattr(response, 'usage') and response.usage:
                    tokens = response.usage.total_tokens
                    if stage in self.token_usage:
                        self.token_usage[stage] += tokens
                        
                return response
                
            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "Rate limit" in error_str:
                    print(f"[GroqManager] 429 Rate Limit Hit on Key {self.active_index + 1}. Rotating...")
                    self.rotate_key()
                    attempts += 1
                else:
                    # Non-rate-limit error (e.g., parsing, bad request)
                    raise e
                    
        raise Exception("All Groq API keys have been rate-limited or exhausted.")
