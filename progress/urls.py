from django.urls import path
from . import views

urlpatterns = [
    # 認証関連
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # ダッシュボード
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('training-admin/', views.training_admin_dashboard, name='training_admin_dashboard'),
    path('system-admin/', views.system_admin_dashboard, name='system_admin_dashboard'),
    
    # 進捗関連
    path('progress/create/', views.progress_form, name='progress_create'),
    path('progress/list/', views.progress_list_view, name='progress_list'),
    path('progress/detail/<int:progress_id>/', views.progress_detail_view, name='progress_detail'),
    path('progress/delete/<int:progress_id>/', views.progress_delete_view, name='progress_delete'),
    path('progress/analytics/', views.progress_analytics_view, name='progress_analytics'),
    path('progress/calendar/', views.progress_calendar, name='progress_calendar'),
    
    # フィードバック要請関連
    path('feedback/list/', views.feedback_requests_list_view, name='feedback_requests_list'),
    path('feedback/detail/<int:progress_id>/', views.feedback_detail_view, name='feedback_detail'),
    path('feedback/analytics/', views.feedback_analytics_view, name='feedback_analytics'),
    
    # グループ関連
    path('groups/', views.group_list_view, name='group_list'),
    path('groups/create/', views.group_create_view, name='group_create'),
    path('groups/<int:group_id>/', views.group_detail_view, name='group_detail'),
    path('groups/<int:group_id>/edit/', views.group_update_view, name='group_edit'),
    path('ranking/', views.group_ranking_view, name='group_ranking'),
    
    # ユーザー管理
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_update_view, name='user_edit'),
    path('users/grade/<str:grade>/', views.users_by_grade_view, name='users_by_grade'),
    
    # API・データ
    path('api/analytics-data/', views.analytics_data_api, name='analytics_data'),
    path('api/weekly-summary/', views.get_weekly_summary, name='weekly_summary'),
    path('api/phase-items/', views.get_phase_items, name='get_phase_items'),
    
    # エクスポート
    path('export/', views.export_menu_view, name='export_menu'),
    path('export/data/', views.export_data_view, name='export_data'),
]