from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    # main
    path('', views.index, name='index'),

    # authentication
    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),

    # goals
    path('goals/', views.goals_list, name='goals_list'),
    path('goals/add_to/<int:goal_id>/', views.add_to_goal, name='add_to_goal'),
    path('goals/add/', views.goal_add, name='goal_add'),
    path('goals/<int:goal_id>/edit/', views.goal_edit, name='goal_edit'),
    path('goals/<int:goal_id>/delete/', views.goal_delete, name='goal_delete'),

    # reports
    path('reports/', views.reports, name='reports'),

    # categories
    path('categories/', views.categories_list, name='categories_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # transactions
    path('transactions/', views.transactions_list, name='transactions_list'),
    path('transactions/add/<str:type>/', views.transaction_add, name='transaction_add'),
    path('transactions/edit/<int:pk>/', views.transaction_edit, name='transaction_edit'),
    path('transactions/delete/<int:pk>/', views.transaction_delete, name='transaction_delete'),
]
