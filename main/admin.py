from django.contrib import admin
from .models import Category, Transaction, Goal


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type', 'user')
    list_filter = ('type', 'user')
    search_fields = ('name', 'user__username')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'category', 'amount', 'type', 'date')
    list_filter = ('type', 'category', 'user')
    search_fields = ('description', 'user__username')
    list_editable = ('amount', 'category')  # можно редактировать прямо в списке
    date_hierarchy = 'date'


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'target_amount', 'current_amount',
                    'deadline', 'progress_percent', 'months_left')
    search_fields = ('name', 'user__username')
    list_filter = ('deadline', 'user')
    readonly_fields = ('created_at', 'progress_percent', 'months_left', 'monthly_needed')
