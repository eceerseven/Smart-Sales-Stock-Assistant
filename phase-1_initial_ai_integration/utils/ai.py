# utils/ai.py


import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# .env’i proje kökünden yükle
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_sales_suggestion(prompt: str) -> str:
    if not openai_client.api_key:
        return "AI yanıtı alınamadı: OPENAI_API_KEY bulunamadı."
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen bir satış asistanısın. Kısa, sayısal ve somut öneriler ver."},
                {"role": "user",   "content": prompt}
            ],
            max_tokens=400,     # eskiden 150 idi, uzun çıktı için 400
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI yanıtı alınamadı: {e}"
