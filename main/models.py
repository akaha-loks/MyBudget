from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from datetime import date
from dateutil.relativedelta import relativedelta


class Category(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories')  # ← добавлено
    TYPE_CHOICES = [
        ('income', 'Доход'),
        ('expense', 'Расход'),
    ]

    name = models.CharField(max_length=50, verbose_name='Название категории')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name='Тип')

    def __str__(self):
        return f"{self.name} ({'Доход' if self.type == 'income' else 'Расход'})"


TYPE_CHOICES = [
    ('income', 'Доход'),
    ('expense', 'Расход'),
]

class Transaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=18, choices=TYPE_CHOICES, verbose_name='Тип операции')

    def __str__(self):
        return f"{self.get_type_display()} — {self.amount} сом"


class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deadline = models.DateField()
    created_at = models.DateField(auto_now_add=True)

    @property
    def progress_percent(self):
        if self.target_amount == 0:
            return 0
        return round((self.current_amount / self.target_amount) * 100, 1)

    @property
    def months_left(self):
        today = date.today()
        if self.deadline <= today:
            return 0
        diff = relativedelta(self.deadline, today)
        return diff.years * 12 + diff.months or 1

    @property
    def monthly_needed(self):
        remaining = max(self.target_amount - self.current_amount, 0)
        months = self.months_left
        return remaining / months if months else remaining