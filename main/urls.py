from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.index, name='index'),

    path('login/', views.user_login, name='login'),
    path('register/', views.user_register, name='register'),
    path('logout/', views.user_logout, name='logout'),

    path('goals/', views.goals_list, name='goals'),
    path('goals/add/', views.goal_add, name='goal_add'),

    path('reports/', views.reports, name='reports'),

    path('categories/', views.categories_list, name='categories_list'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    path('transactions/add/<str:type>/', views.transaction_add, name='transaction_add'),
]
