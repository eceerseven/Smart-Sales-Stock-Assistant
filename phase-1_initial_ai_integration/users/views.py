from django.shortcuts import render

# Create your views here.
# users/views.py

from django.http import HttpResponse

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/users/home/')  # 🔄 Güncellendi
        else:
            return HttpResponse("Giriş başarısız. Lütfen tekrar deneyin.")
    return render(request, "users/login.html")


@login_required
def user_home(request):
    return render(request, "users/home.html")

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        if User.objects.filter(username=username).exists():
            return HttpResponse("Bu kullanıcı adı zaten alınmış.")
        user = User.objects.create_user(username=username, password=password)
        user.save()
        return redirect('/users/')  # Kayıt sonrası login sayfasına yönlendir
    return render(request, "users/register.html")