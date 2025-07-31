from django.contrib import admin

# Register your models here.
# sales/admin.py
from django.contrib import admin
from .models import SalesRecord

@admin.register(SalesRecord)
class SalesRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'upload_date', 'hedef_adet', 'toplam_adet', 'tamamlama_yuzdesi')
    list_filter = ('user', 'upload_date')
    search_fields = ('user__username',)