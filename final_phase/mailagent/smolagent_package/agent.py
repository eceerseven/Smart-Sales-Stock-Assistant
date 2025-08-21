
# mailagent/smolagent_package/agent.py

# mailagent/smolagent_package/agent.py

import os
from openai import OpenAI
from .memory import AgentMemory

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ReminderAgent:
    def __init__(self, name="AI Reminder Agent"):
        self.name = name
        self.memory = AgentMemory()

    def act(self, prompt):
        full_prompt = f"{self.memory.recall()}\nKullanıcıdan gelen mesaj: {prompt}\nAI kararı:"
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sen akıllı bir hatırlatma asistanısın. Kısa ve net kararlar ver."},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.4
            )
            answer = response.choices[0].message.content.strip()
            return answer
        except Exception as e:
            return f"Hata oluştu: {str(e)}"

    def remember(self, new_info):
        self.memory.store(new_info)

class SmolAgent:
    def __init__(self, name):
        self.name = name
        self.memory = AgentMemory()

    def act(self, prompt):
        self.memory.add_interaction(prompt)
        response = self.query_llm(prompt)
        self.memory.add_interaction(response)
        return response

    def query_llm(self, prompt):
        try:
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Sen bir satış asistanısın. Satış verisi girmemiş kullanıcıları değerlendirip, e-posta hatırlatması gönderilip gönderilmeyeceğine karar ver."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            return f"Hata oluştu: {str(e)}"
