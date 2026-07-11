from src.system.logger import setup_logger
logger = setup_logger('rate_limiter')
import time
import random
from typing import Callable, Any

class RateLimiter:
    """
    Handles per-provider request limits, exponential backoff, retries, jitter, 
    and global request budgets. Protects the backend from bans.
    """
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.global_budget = 1000 # Example budget

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        if self.global_budget <= 0:
            raise Exception("Global rate limit budget exceeded.")
            
        retries = 0
        while retries <= self.max_retries:
            try:
                self.global_budget -= 1
                return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries > self.max_retries:
                    raise Exception(f"Max retries reached: {e}")
                
                # Exponential backoff with jitter
                delay = (self.base_delay * (2 ** retries)) + random.uniform(0, 1)
                logger.info(f"Request failed: {e}. Retrying in {delay:.2f}s (Attempt {retries}/{self.max_retries})")
                time.sleep(delay)
