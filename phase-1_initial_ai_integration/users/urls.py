# users/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),  # Giriş formu
    path('home/', views.user_home, name='user-home'),  # Giriş sonrası yönlendirme
    path('register/', views.register_view, name='register'),
]