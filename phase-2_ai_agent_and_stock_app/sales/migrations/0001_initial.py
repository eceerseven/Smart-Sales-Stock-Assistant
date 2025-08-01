# Generated by Django 5.2.4 on 2025-07-30 18:43

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SalesRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('upload_date', models.DateTimeField(auto_now_add=True)),
                ('hedef_adet', models.IntegerField()),
                ('hedef_gelir', models.FloatField()),
                ('toplam_adet', models.IntegerField()),
                ('toplam_gelir', models.FloatField()),
                ('gunluk_ortalama', models.FloatField()),
                ('kalan_gunluk_gerekli', models.FloatField()),
                ('tamamlama_yuzdesi', models.FloatField()),
                ('yorum', models.TextField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
