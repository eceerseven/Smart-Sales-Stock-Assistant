# mailagent/urls.py

from django.urls import path
from .views import agent_run_view

urlpatterns = [
    path('run/', agent_run_view, name='agent-run'),
]