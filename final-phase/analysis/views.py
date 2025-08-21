from django.shortcuts import render

# Create your views here.
# analysis/views.py

from django.http import HttpResponse

def test_page(request):
    return HttpResponse("Analysis app aktif!")