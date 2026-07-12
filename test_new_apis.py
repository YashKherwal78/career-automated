import os
from dotenv import load_dotenv

# Load env variables
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

print("--- Testing New API Keys ---")

# 1. Test Gemini
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Say 'Gemini is working'")
    print(f"[Gemini] SUCCESS! Output: {response.text.strip()}")
except Exception as e:
    print(f"[Gemini] FAILED: {e}")

# 2. Test OpenRouter
try:
    from openai import OpenAI
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    completion = client.chat.completions.create(
        model="google/gemini-2.0-flash-exp:free", # free test model
        messages=[{"role": "user", "content": "Say 'OpenRouter is working'"}],
    )
    print(f"[OpenRouter] SUCCESS! Output: {completion.choices[0].message.content.strip()}")
except Exception as e:
    print(f"[OpenRouter] FAILED: {e}")

# 3. Test DeepSeek
try:
    from openai import OpenAI
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": "You are a helpful assistant."},
                  {"role": "user", "content": "Say 'DeepSeek is working'"}],
        stream=False
    )
    print(f"[DeepSeek] SUCCESS! Output: {response.choices[0].message.content.strip()}")
except Exception as e:
    print(f"[DeepSeek] FAILED: {e}")

print("----------------------------")
