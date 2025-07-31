from django.db import models

# sales/models.py

from django.db import models
from django.contrib.auth.models import User

class SalesRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    upload_date = models.DateTimeField(auto_now_add=True)
    period = models.CharField(max_length=20, null=True, blank=True)
    hedef_adet = models.IntegerField()
    hedef_gelir = models.FloatField()
    toplam_adet = models.IntegerField()
    toplam_gelir = models.FloatField()
    gunluk_ortalama = models.FloatField()
    kalan_gunluk_gerekli = models.FloatField()
    tamamlama_yuzdesi = models.FloatField()
    yorum = models.TextField()

    def __str__(self):
        return f"{self.user.username} - {self.upload_date.strftime('%Y-%m-%d')}"
