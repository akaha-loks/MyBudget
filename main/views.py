from django.shortcuts import render, redirect, get_object_or_404
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
from decimal import Decimal, InvalidOperation



@login_required
def index(request):
    user = request.user

    # Доходы и расходы для прогресс-бара
    income = Transaction.objects.filter(user=user, type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    expenses = Transaction.objects.filter(user=user, type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = income - expenses

    total = income + expenses
    income_percent = round(income / total * 100, 1) if total else 0
    expense_percent = round(expenses / total * 100, 1) if total else 0

    # Последние 10 транзакций
    transactions = Transaction.objects.filter(user=user).order_by('-date')[:10]

    return render(request, 'main/index.html', {
        'balance': balance,
        'income': income,
        'expenses': expenses,
        'income_percent': income_percent,
        'expense_percent': expense_percent,
        'transactions': transactions,
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
    goals = Goal.objects.filter(user=request.user)
    return render(request, 'main/goals/list.html', {'goals': goals})


@login_required
def goal_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        target = request.POST.get('target_amount')
        deadline = request.POST.get('deadline')

        if not name or not target or not deadline:
            messages.error(request, "Заполните все поля!")
        else:
            try:
                target_amount = Decimal(target)
                if target_amount <= 0:
                    raise ValueError
            except (InvalidOperation, ValueError):
                messages.error(request, "Некорректная сумма цели!")
            else:
                Goal.objects.create(
                    user=request.user,
                    name=name,
                    target_amount=target_amount,
                    current_amount=Decimal('0.0'),
                    deadline=deadline,
                    created_at=timezone.now()  # <-- обязательно добавляем
                )
                messages.success(request, "Цель успешно добавлена!")
                return redirect('main:goals_list')

    return render(request, 'main/goals/add.html')


@login_required
def add_to_goal(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)

    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0')
        try:
            amount = Decimal(amount_str)  # <-- конвертируем в Decimal
            if amount <= 0:
                messages.error(request, 'Введите положительную сумму.')
            else:
                goal.current_amount += amount
                goal.save()
                messages.success(request, f'Добавлено {amount} сом к цели "{goal.name}".')
                return redirect('main:goals_list')
        except (InvalidOperation, ValueError):
            messages.error(request, 'Некорректное значение суммы.')

    return render(request, 'main/goals/add_to_goal.html', {'goal': goal})


@login_required
def goal_edit(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)

    if request.method == 'POST':
        goal.name = request.POST.get('name')
        target_amount_str = request.POST.get('target_amount')
        current_amount_str = request.POST.get('current_amount')
        goal.deadline = request.POST.get('deadline')

        try:
            goal.target_amount = Decimal(target_amount_str)
            goal.current_amount = Decimal(current_amount_str)
        except (InvalidOperation, ValueError):
            messages.error(request, 'Некорректная сумма!')
            return render(request, 'main/goals/edit.html', {'goal': goal})

        goal.save()
        messages.success(request, "Цель обновлена!")
        return redirect('main:goals_list')

    return render(request, 'main/goals/edit.html', {'goal': goal})


@login_required
def goal_delete(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    if request.method == 'POST':
        goal.delete()
        messages.success(request, "Цель удалена.")
        return redirect('main:goals_list')
    return redirect('main:goals_list')


@login_required
def reports(request):
    user = request.user

    # Суммируем доходы и расходы
    income = Transaction.objects.filter(user=user, type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    expenses = Transaction.objects.filter(user=user, type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    balance = income - expenses

    # Суммируем расходы по категориям
    category_data = (
        Transaction.objects
        .filter(user=user, type='expense')
        .values('category__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    context = {
        'income': income,
        'expenses': expenses,
        'balance': balance,
        'category_data': category_data,
        'today': date.today(),
    }
    return render(request, 'main/reports.html', context)


@login_required
def transactions_list(request):
    user = request.user
    transactions = Transaction.objects.filter(user=user).order_by('-date')

    # Подсчёт доходов и расходов
    income = transactions.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
    expenses = transactions.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0

    total = income + expenses
    income_percent = round(income / total * 100, 1) if total else 0
    expense_percent = round(expenses / total * 100, 1) if total else 0

    return render(request, 'main/transactions/list.html', {
        'transactions': transactions,
        'income': income,
        'expenses': expenses,
        'income_percent': income_percent,
        'expense_percent': expense_percent,
    })


@login_required()
def transaction_add(request, type):
    now = timezone.localtime()
    categories = Category.objects.filter(user=request.user, type=type)

    type_map = {'income': 'Доход', 'expense': 'Расход'}
    type_display = type_map.get(type, type)

    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0')
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                messages.error(request, "Введите положительную сумму.")
                return redirect(request.path)
        except InvalidOperation:
            messages.error(request, "Некорректное значение суммы.")
            return redirect(request.path)

        category_id = request.POST.get('category')
        category = None
        if category_id:
            category = Category.objects.filter(id=category_id, user=request.user).first()

        description = request.POST.get('description')
        date_str = request.POST.get('date')
        time_str = request.POST.get('time')

        if date_str and time_str:
            try:
                datetime_obj = timezone.make_aware(
                    timezone.datetime.fromisoformat(f"{date_str}T{time_str}")
                )
            except ValueError:
                datetime_obj = now
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
        messages.success(request, f"{type_display} добавлен: {amount} сом")
        return redirect('main:index')

    return render(request, 'main/transactions/add.html', {
        'type': type,
        'type_display': type_display,
        'categories': categories,
        'now_date': now.date(),
        'now_time': now.strftime('%H:%M')
    })


@login_required
def transaction_edit(request, pk):
    transaction = get_object_or_404(Transaction, id=pk, user=request.user)
    categories = Category.objects.filter(user=request.user, type=transaction.type)

    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0')
        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                messages.error(request, "Введите положительную сумму.")
                return redirect(request.path)
        except InvalidOperation:
            messages.error(request, "Некорректное значение суммы.")
            return redirect(request.path)

        transaction.amount = amount
        category_id = request.POST.get('category')
        transaction.category = Category.objects.filter(id=category_id, user=request.user).first()
        transaction.description = request.POST.get('description')

        date_str = request.POST.get('date')
        time_str = request.POST.get('time')
        if date_str and time_str:
            try:
                transaction.date = timezone.make_aware(
                    timezone.datetime.fromisoformat(f"{date_str}T{time_str}")
                )
            except ValueError:
                pass

        transaction.save()
        messages.success(request, "Транзакция обновлена!")
        return redirect('main:transactions_list')

    return render(request, 'main/transactions/edit.html', {'transaction': transaction, 'categories': categories})


@login_required
def transaction_delete(request, pk):
    transaction = get_object_or_404(Transaction, id=pk, user=request.user)
    if request.method == 'POST':
        transaction.delete()
        messages.success(request, "Транзакция удалена.")
        return redirect('main:transactions_list')
    return render(request, 'main/transactions/delete.html', {'transaction': transaction})



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
