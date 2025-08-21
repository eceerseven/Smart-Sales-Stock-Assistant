# sales/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.sales_form_view, name='sales-form'),
]
