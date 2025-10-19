from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
import re
from .models import Goal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Transaction, Category
from datetime import date

@login_required
def index(request):
    user = request.user  # type: ignore[assignment]
    income: float = Transaction.objects.filter(user=user, type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    expenses: float = Transaction.objects.filter(user=user, type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = income - expenses

    total = income + expenses
    income_percent = round(income / total * 100, 1) if total else 0
    expense_percent = round(expenses / total * 100, 1) if total else 0

    return render(request, 'main/index.html', {
        'balance': balance,
        'income': income,
        'expenses': expenses,
        'income_percent': income_percent,
        'expense_percent': expense_percent,
    })


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

@login_required
def goals_list(request):
    goals = Goal.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'main/goals/goals.html', {'goals': goals})

@login_required
def goal_add(request):
    return HttpResponse("Здесь будет форма добавления цели (в разработке).")

@login_required
def reports(request):
    user = request.user

    # Суммируем доходы и расходы
    total_income = Transaction.objects.filter(user=user, type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = Transaction.objects.filter(user=user, type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = total_income - total_expense

    # Суммируем расходы по категориям
    category_data = (
        Transaction.objects
        .filter(user=user, type='expense')
        .values('category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    context = {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
        'category_data': category_data,
        'today': date.today(),
    }
    return render(request, 'main/reports.html', context)
