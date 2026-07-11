from src.system.logger import setup_logger
logger = setup_logger('llm_router')
import os
import json
import time
from typing import List, Dict, Optional
from src.config.config import Config
from src.crm.database import log_llm_usage
from src.utils.groq_manager import GroqManager

# Clients
try:
    from google import genai
    from google.genai import types as genai_types
except ImportError:
    genai = None

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class FakeMessage:
    def __init__(self, content):
        self.content = content

class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)

class FakeUsage:
    def __init__(self, total_tokens):
        self.total_tokens = total_tokens

class FakeResponse:
    def __init__(self, content, tokens=0):
        self.choices = [FakeChoice(content)]
        self.usage = FakeUsage(tokens)


class LLMRouter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LLMRouter, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.groq_manager = GroqManager()
        
        self.gemini_client = None
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key and genai:
            try:
                self.gemini_client = genai.Client(api_key=gemini_key)
            except Exception as e:
                logger.info(f"[LLMRouter] Failed to initialize Gemini Client: {e}")

        self.openrouter_client = None
        or_key = os.environ.get("OPENROUTER_API_KEY")
        if or_key and OpenAI:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=or_key
            )

        self.routes = {
            "outreach": ["gemini", "openrouter", "groq"],
            "reasoning": ["openrouter", "gemini", "groq"],
            "utility": ["groq", "gemini", "openrouter"]
        }

        self.openrouter_models = [
            "deepseek/deepseek-chat",
            "qwen/qwen-2.5-72b-instruct",
            "meta-llama/llama-3-70b-instruct"
        ]

    def chat_completion(self, messages: List[Dict], temperature: float = 0.2, response_format: Optional[Dict] = None, intent: str = "utility") -> FakeResponse:
        providers = self.routes.get(intent, ["groq", "gemini", "openrouter"])
        fallback_count = 0
        
        for provider in providers:
            try:
                start_time = time.time()
                
                if provider == "gemini":
                    content, tokens, model_used = self._call_gemini(messages, temperature, response_format)
                elif provider == "openrouter":
                    content, tokens, model_used = self._call_openrouter(messages, temperature, response_format)
                elif provider == "groq":
                    content, tokens, model_used = self._call_groq(messages, temperature, response_format)
                else:
                    continue
                    
                latency = time.time() - start_time
                log_llm_usage(intent, provider, model_used, tokens, latency, fallback_count)
                return FakeResponse(content, tokens)
                
            except Exception as e:
                logger.info(f"[LLMRouter] Provider {provider} failed on intent '{intent}': {e}")
                fallback_count += 1
                
        raise Exception(f"All LLM providers failed for intent: {intent}")

    def _call_gemini(self, messages: List[Dict], temperature: float, response_format: Optional[Dict]):
        if not self.gemini_client:
            raise Exception("Gemini client not initialized.")
            
        # Convert messages to a single string prompt
        prompt = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
        
        # Determine format
        mime_type = "text/plain"
        if response_format and response_format.get("type") == "json_object":
            mime_type = "application/json"
            
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type=mime_type
        )
        
        model_name = "gemini-2.0-flash"
        response = self.gemini_client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=config
        )
        
        tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            tokens = response.usage_metadata.total_token_count
            
        return response.text, tokens, model_name

    def _call_openrouter(self, messages: List[Dict], temperature: float, response_format: Optional[Dict]):
        if not self.openrouter_client:
            raise Exception("OpenRouter client not initialized.")
            
        kwargs = {
            "messages": messages,
            "temperature": temperature
        }
        if response_format:
            kwargs["response_format"] = response_format
            
        last_error = None
        for model in self.openrouter_models:
            kwargs["model"] = model
            try:
                response = self.openrouter_client.chat.completions.create(**kwargs)
                tokens = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0
                return response.choices[0].message.content, tokens, model
            except Exception as e:
                logger.info(f"[LLMRouter] OpenRouter model {model} failed: {e}")
                last_error = e
                
        raise Exception(f"All OpenRouter fallback models failed. Last error: {last_error}")

    def _call_groq(self, messages: List[Dict], temperature: float, response_format: Optional[Dict]):
        # We assume the default model is llama-3.1-8b-instant for utility
        model_name = "llama-3.1-8b-instant"
        response = self.groq_manager.chat_completion(
            model=model_name,
            messages=messages,
            temperature=temperature,
            response_format=response_format
        )
        tokens = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else 0
        return response.choices[0].message.content, tokens, model_name
