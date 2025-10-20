from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User


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
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name='Тип операции')  # ← вот это новое поле

    def __str__(self):
        return f"{self.get_type_display()} — {self.amount} сом"



class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    name = models.CharField(max_length=100, verbose_name='Название цели')
    target_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Целевая сумма')
    current_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Текущая сумма')
    deadline = models.DateField(verbose_name='Срок достижения')
    created_at = models.DateTimeField(auto_now_add=True)

    def progress_percent(self):
        if self.target_amount == 0:
            return 0
        return round((self.current_amount / self.target_amount) * 100, 1)

    def __str__(self):
        return f"{self.name} ({self.progress_percent()}%)"
