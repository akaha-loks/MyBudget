from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
import re

def index(request):
    return render(request, 'main/index.html')

def user_register(request):
    if request.method == 'POST':
        nickname = request.POST.get('nickname')
        username = request.POST.get('username')
        password = request.POST.get('password')
        if not re.match(r"[^@]+@[^@]+\.[^@]+", username):
            return render(request, 'main/auth/register.html', {'error': 'Введите корректный email @'})
        if len(password) < 5:
            return render(request, 'main/auth/register.html', {'error': 'Пароль должен быть минимум 5 символов'})
        if User.objects.filter(username=username).exists():
            return render(request, 'main/auth/register.html', {'error': 'Пользователь с таким email уже существует'})
        user = User.objects.create_user(username=username, password=password, first_name=nickname)
        login(request, user)
        return redirect('/')
    return render(request, 'main/auth/register.html')


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        else:
            return render(request, 'main/auth/login.html', {'error': 'Неверный логин или пароль'})
    return render(request, 'main/auth/login.html')

def user_logout(request):
    logout(request)
    return redirect('main:login')

