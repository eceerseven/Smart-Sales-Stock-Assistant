# agents/reminder_agent.py

from smolagent import Agent
from sales.models import SalesRecord
from django.contrib.auth.models import User
import datetime
from django.core.mail import send_mail

def run_reminder_agent():
    today = datetime.date.today()
    current_period = today.strftime("%Y-%m")

    agent = Agent(
        system_prompt=(
            "Sen Smart Sales Assistant projesi icin calisan bir AI agentsin. "
            "Eger bir kullanici belirtilen ayda hic satis verisi yuklememisse, "
            "neden verilerin zamaninda girilmesi gerektigini anlatan nazik ama ikna edici bir e-posta metni hazirla."
        ),
        model="gpt-4",  # veya "gpt-3.5-turbo"
    )

    for user in User.objects.all():
        veri_var = SalesRecord.objects.filter(user=user, period__startswith=current_period).exists()
        if not veri_var:
            mesaj = f"Kullanici {user.username} {current_period} ayinda hic satis verisi girmedi."
            eposta_metni = agent.run(mesaj)

            send_mail(
                subject="[Hatirlatici] {0} ayi icin satis verisi girilmedi".format(current_period),
                message=eposta_metni,
                from_email="noreply@smartsales.com",
                recipient_list=[user.email],
                fail_silently=True
            )
