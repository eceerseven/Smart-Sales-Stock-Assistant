# mailagent/smolagent_package/tools.py


import datetime
from sales.models import SalesRecord
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .agent import SmolAgent

User = get_user_model()
agent = SmolAgent(name="SalesReminderAgent")

def check_sales_data_uploaded(user):
    today = datetime.date.today()
    this_month = today.strftime('%Y-%m')
    return SalesRecord.objects.filter(user=user, period__startswith=this_month).exists()

def send_reminder_email():
    subject = "Satış Verisi Hatırlatması"
    message = "Merhaba,\n\nBu ay için henüz satış verisi yüklemediniz. Lütfen sistemimize gerekli verileri yükleyin.\n\nİyi çalışmalar."
    from_email = settings.DEFAULT_FROM_EMAIL

    users = User.objects.all()
    for user in users:
        if not check_sales_data_uploaded(user):
            recipient = user.email
            if recipient:
                decision = agent.act(f"Kullanıcı {user.username} henüz satış verisi girmemiş. Hatırlatma gönderilsin mi?")
                print("AI kararı:", decision)
                if "evet" in decision.lower():
                    send_mail(subject, message, from_email, [recipient])
                    agent.memory.add_interaction(f"{user.username} için e-posta gönderildi.")
