from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
import re
from django.utils import timezone
from .models import Goal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Transaction, Category
from datetime import date, datetime
from django.contrib import messages
from django.urls import reverse

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

@login_required()
def transaction_add(request, type):
    now = timezone.localtime()
    categories = Category.objects.filter(user=request.user, type=type)

    type_map = {
        'income': 'Доход',
        'expense': 'Расход',
    }
    type_display = type_map.get(type, type)  # сразу передаем в шаблон

    if request.method == 'POST':
        amount = request.POST.get('amount')
        category_id = request.POST.get('category')
        category = Category.objects.get(id=category_id) if category_id else None
        description = request.POST.get('description')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')

        if date_str and time_str:
            datetime_obj = timezone.make_aware(
                timezone.datetime.fromisoformat(f"{date_str}T{time_str}")
            )
        else:
            datetime_obj = now

        Transaction.objects.create(
            user=request.user,
            category=category,
            amount=amount,
            description=description,
            date=datetime_obj,
            type=type
        )
        return redirect('main:index')

    return render(request, 'main/transactions/add.html', {
        'type': type,
        'type_display': type_display,  # <-- передаем сюда
        'categories': categories,
        'now_date': now.date(),
        'now_time': now.strftime('%H:%M')
    })


@login_required
def categories_list(request):
    categories = Category.objects.filter(user=request.user).order_by('type', 'name')
    return render(request, 'main/categories/list.html', {'categories': categories})


@login_required
def category_add(request):
    next_url = request.GET.get('next', reverse('main:index'))

    if request.method == 'POST':
        name = request.POST.get('name')
        type_ = request.POST.get('type')

        if not name:
            messages.error(request, 'Введите название категории.')
        else:
            Category.objects.create(user=request.user, name=name, type=type_)
            messages.success(request, 'Категория добавлена.')
            return redirect(next_url)

    return render(request, 'main/categories/add.html', {'next_url': next_url})


@login_required
def category_edit(request, pk):
    category = Category.objects.get(id=pk, user=request.user)
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.type = request.POST.get('type')
        category.save()
        messages.success(request, 'Категория обновлена.')
        return redirect('main:categories_list')
    return render(request, 'main/categories/edit.html', {'category': category})


@login_required
def category_delete(request, pk):
    category = Category.objects.get(id=pk, user=request.user)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Категория удалена.')
        return redirect('main:categories_list')
    return render(request, 'main/categories/delete.html', {'category': category})
