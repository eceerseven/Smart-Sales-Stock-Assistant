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
def openai_stok_analiz_prompt(df):
    import openai
    import os
    from dotenv import load_dotenv

    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")

    pivot = df.groupby("Yaş Aralığı")["Ürün Adı"].count().to_string()

    prompt = f"""
Aşağıda stok yaş aralıklarına göre kaç ürünün hangi segmentte olduğu yer alıyor. Buna göre bir analiz ve öneri yaz:
{pivot}
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Sen deneyimli bir stok yöneticisisin."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )

    return response["choices"][0]["message"]["content"]

get_ai_response = get_sales_suggestion