from django.shortcuts import render

# Create your views here.
# stock/views.py

from django.http import HttpResponse

def test_page(request):
    return HttpResponse("Stock app aktif!")