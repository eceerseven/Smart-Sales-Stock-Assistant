from django.urls import path
from .views import stock_home, stok_analizi

urlpatterns = [
    path("", stock_home),
    path("stok-analizi/", stok_analizi, name="stok-analizi"),
]
