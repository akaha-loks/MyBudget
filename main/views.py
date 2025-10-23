from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
import re
from django.utils import timezone
from .models import Goal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from .models import Transaction, Category
from datetime import date, datetime, timedelta
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal, InvalidOperation
import time
from captcha.models import CaptchaStore
from captcha.helpers import captcha_image_url



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

    # выборка целей
    goals = Goal.objects.filter(user=user).order_by('deadline')[:5]

    # --- Данные для мини-графика доходов/расходов за неделю ---
    today = date.today()
    week_ago = today - timedelta(days=6)  # последние 7 дней включая сегодня
    last_week_dates = [(week_ago + timedelta(days=i)) for i in range(7)]
    labels = [d.strftime('%d.%m') for d in last_week_dates]

    income_data = []
    expense_data = []
    for d in last_week_dates:
        start_of_day = timezone.make_aware(datetime.combine(d, datetime.min.time()))
        end_of_day = timezone.make_aware(datetime.combine(d, datetime.max.time()))
        day_income = \
        Transaction.objects.filter(user=user, type='income', date__range=(start_of_day, end_of_day)).aggregate(
            Sum('amount'))['amount__sum'] or 0
        day_expense = \
        Transaction.objects.filter(user=user, type='expense', date__range=(start_of_day, end_of_day)).aggregate(
            Sum('amount'))['amount__sum'] or 0
        income_data.append(day_income)
        expense_data.append(day_expense)

    return render(request, 'main/index.html', {
        'balance': balance,
        'income': income,
        'expenses': expenses,
        'income_percent': income_percent,
        'expense_percent': expense_percent,
        'transactions': transactions,
        'goals': goals,
        'week_labels': labels,
        'week_income_data': [float(x) for x in income_data],
        'week_expense_data': [float(x) for x in expense_data],
    })


def user_register(request):
    if request.method == 'POST':
        nickname = request.POST.get('nickname')
        username = request.POST.get('username')
        password = request.POST.get('password')
        captcha_key = request.POST.get('captcha_0')
        captcha_value = request.POST.get('captcha_1')

        # Проверка капчи
        try:
            captcha = CaptchaStore.objects.get(hashkey=captcha_key)
            if captcha.response != captcha_value.lower():
                raise Exception
        except Exception:
            new_key = CaptchaStore.generate_key()
            new_image = captcha_image_url(new_key)
            return render(request, 'main/auth/register.html', {
                'error': 'Неверно введена капча',
                'captcha': f'<img src="{new_image}" alt="captcha"><input type="hidden" name="captcha_0" value="{new_key}"><input type="text" name="captcha_1" class="form-control form-control-sm mt-2" required>'
            })

        # Проверка email и пароля
        if not re.match(r"[^@]+@[^@]+\.[^@]+", username):
            return render(request, 'main/auth/register.html', {'error': 'Введите корректный email @'})
        if len(password) < 5:
            return render(request, 'main/auth/register.html', {'error': 'Пароль должен быть минимум 5 символов'})
        if User.objects.filter(username=username).exists():
            return render(request, 'main/auth/register.html', {'error': 'Пользователь с таким email уже существует'})

        user = User.objects.create_user(username=username, password=password, first_name=nickname)
        login(request, user)
        return redirect('/')
    else:
        # Генерируем новую капчу при загрузке страницы
        new_key = CaptchaStore.generate_key()
        new_image = captcha_image_url(new_key)
        return render(request, 'main/auth/register.html', {
            'captcha': f'<img src="{new_image}" alt="captcha"><input type="hidden" name="captcha_0" value="{new_key}"><input type="text" name="captcha_1" class="form-control form-control-sm mt-2" required>'
        })

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
    # текущая дата + 1 месяц (30 дней)
    now_struct = time.localtime()
    today_date = datetime.fromtimestamp(time.mktime(now_struct)).date()
    default_deadline = today_date + timedelta(days=30)

    if request.method == 'POST':
        name = request.POST.get('name')
        target = request.POST.get('target_amount')
        deadline = request.POST.get('deadline') or str(default_deadline)

        if not name or not target:
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
                    created_at=timezone.now()
                )
                messages.success(request, "Цель успешно добавлена!")
                return redirect('main:goals_list')

    return render(request, 'main/goals/add.html', {
        'default_deadline': default_deadline.isoformat()
    })


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
    period = int(request.GET.get('period', 30))
    today = date.today()
    start_date = today - timedelta(days=period-1)

    # Транзакции за выбранный период
    transactions = Transaction.objects.filter(user=user, date__date__range=[start_date, today])

    # Данные по дням
    labels = []
    income_data = []
    expense_data = []

    for i in range(period):
        day = start_date + timedelta(days=i)
        labels.append(day.strftime('%d.%m'))
        daily_income = transactions.filter(type='income', date__date=day).aggregate(Sum('amount'))['amount__sum'] or 0
        daily_expense = transactions.filter(type='expense', date__date=day).aggregate(Sum('amount'))['amount__sum'] or 0
        income_data.append(float(daily_income))
        expense_data.append(float(daily_expense))

    # Суммарные значения
    income = sum(income_data)
    expenses = sum(expense_data)
    balance = income - expenses

    # Данные по категориям
    income_categories = (
        transactions.filter(type='income')
        .values('category__name')
        .annotate(total=Sum('amount'))
    )
    expense_categories = (
        transactions.filter(type='expense')
        .values('category__name')
        .annotate(total=Sum('amount'))
    )

    # Преобразуем в списки для Chart.js
    income_labels = [item['category__name'] for item in income_categories]
    income_totals = [float(item['total']) for item in income_categories]

    expense_labels = [item['category__name'] for item in expense_categories]
    expense_totals = [float(item['total']) for item in expense_categories]

    context = {
        'income': income,
        'expenses': expenses,
        'balance': balance,
        'labels': labels,
        'income_data': income_data,
        'expense_data': expense_data,
        'today': today,
        'period': period,
        'income_labels': income_labels,
        'income_totals': income_totals,
        'expense_labels': expense_labels,
        'expense_totals': expense_totals,
    }
    return render(request, 'main/reports.html', context)


@login_required
def transactions_list(request):
    user = request.user
    sort = request.GET.get('sort', '-date')  # сортировка по умолчанию: дата по убыванию
    category_id = request.GET.get('category', '')  # выбранная категория

    # разрешённые поля для сортировки
    allowed_sorts = ['date', '-date', 'amount', '-amount', 'type', '-type']
    if sort not in allowed_sorts:
        sort = '-date'

    # получаем все категории пользователя для фильтра
    categories = Category.objects.filter(user=user)

    # базовый queryset
    transactions = Transaction.objects.filter(user=user)

    # фильтр по категории, если выбрана
    if category_id:
        transactions = transactions.filter(category_id=category_id)

    # применяем сортировку
    transactions = transactions.order_by(sort)

    # Подсчёт доходов и расходов (по отфильтрованным транзакциям)
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
        'current_sort': sort,
        'categories': categories,
        'selected_category': category_id
    })

@login_required
def transaction_add(request, type):
    # Получаем текущую локальную дату и время через time
    now_struct = time.localtime()
    now_date = time.strftime("%Y-%m-%d", now_struct)  # для input[type=date]
    now_time = time.strftime("%H:%M", now_struct)     # для input[type=time]
    tz = timezone.get_current_timezone()

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
        category = Category.objects.filter(id=category_id, user=request.user).first() if category_id else None

        description = request.POST.get('description', '').strip()
        date_str = request.POST.get('date', '').strip()   # "YYYY-MM-DD"
        time_str = request.POST.get('time', '').strip()   # "HH:MM"

        # создаём aware datetime с использованием time
        if date_str and time_str:
            naive_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        elif date_str:
            # если только дата — ставим текущее время
            t = time.localtime()
            naive_dt = datetime.strptime(date_str, "%Y-%m-%d").replace(hour=t.tm_hour, minute=t.tm_min)
        elif time_str:
            # если только время — используем сегодняшнюю дату
            today = time.strftime("%Y-%m-%d", now_struct)
            naive_dt = datetime.strptime(f"{today} {time_str}", "%Y-%m-%d %H:%M")
        else:
            naive_dt = datetime.fromtimestamp(time.mktime(now_struct))  # fallback

        datetime_obj = timezone.make_aware(naive_dt, tz)

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
        'now_date': now_date,
        'now_time': now_time
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
