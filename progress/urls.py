from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('progress/create/', views.progress_create, name='progress_create'),
    path('progress/list/', views.progress_list, name='progress_list'),
    path('ranking/', views.group_ranking, name='group_ranking'),
]