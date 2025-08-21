# mailagent/management/commands/send_reminders.py

from django.core.management.base import BaseCommand
from mailagent.smolagent_package.tools import send_reminder_email

class Command(BaseCommand):
    help = 'Kullanıcılara satış verisi girmeleri için hatırlatma gönderir'

    def handle(self, *args, **kwargs):
        send_reminder_email()
        self.stdout.write(self.style.SUCCESS("Hatırlatma işlemi tamamlandı."))