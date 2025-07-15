from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 認証関連
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # パスワードリセット
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='progress/auth/password_reset.html',
        email_template_name='progress/auth/password_reset_email.html',
        success_url='/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='progress/auth/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='progress/auth/password_reset_confirm.html',
        success_url='/password-reset-complete/'
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='progress/auth/password_reset_complete.html'
    ), name='password_reset_complete'),
    
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
    path('groups/<int:group_id>/delete/', views.group_delete_view, name='group_delete'),
    path('groups/<int:group_id>/members/', views.group_members_view, name='group_members'),
    path('ranking/', views.group_ranking_view, name='group_ranking'),
    
    # ユーザー管理
    path('users/', views.user_list_view, name='user_list'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:user_id>/', views.user_detail_view, name='user_detail'),
    path('users/<int:user_id>/edit/', views.user_update_view, name='user_edit'),
    path('users/grade/<str:grade>/', views.users_by_grade_view, name='users_by_grade'),
    
    # システム管理者用研修編集
    path('users/<int:user_id>/training-edit/', views.edit_user_training, name='edit_user_training'),
    path('users/<int:user_id>/progress-history/', views.edit_progress_history, name='edit_progress_history'),
    path('users/<int:user_id>/item-progress/', views.edit_item_progress, name='edit_item_progress'),
    path('progress/edit/<int:progress_id>/', views.edit_progress_record, name='edit_progress_record'),
    path('progress/system-delete/<int:progress_id>/', views.delete_progress_record, name='delete_progress_record'),
    path('users/<int:user_id>/batch-update/', views.batch_update_progress, name='batch_update_progress'),
    
    # API・データ
    path('api/analytics-data/', views.analytics_data_api, name='analytics_data'),
    path('api/weekly-summary/', views.get_weekly_summary, name='weekly_summary'),
    path('api/phase-items/', views.get_phase_items, name='get_phase_items'),
    path('api/last-week-mvp/', views.get_last_week_mvp, name='last_week_mvp'),
    path('api/ajax-phase-items/', views.ajax_get_phase_items, name='ajax_get_phase_items'),
    
    # スタンプAPI
    path('api/stamp/add/', views.add_stamp, name='add_stamp'),
    path('api/stamp/progress/<int:progress_id>/', views.get_progress_stamps, name='get_progress_stamps'),
    path('api/stamp/summary/', views.get_stamp_summary, name='get_stamp_summary'),
    
    # エクスポート
    path('export/', views.export_menu_view, name='export_menu'),
    path('export/data/', views.export_data_view, name='export_data'),
    path('export/progress/', views.export_data_view, {'export_type': 'progress'}, name='export_progress_csv'),
    path('export/users/', views.export_data_view, {'export_type': 'users'}, name='export_users_csv'),
    path('export/groups/', views.export_data_view, {'export_type': 'groups'}, name='export_groups_csv'),
    path('export/analytics/', views.export_data_view, {'export_type': 'analytics'}, name='export_analytics_csv'),
    
    # アラート関連
    path('alerts/', views.alert_list_view, name='alert_list'),
    path('alerts/<int:alert_id>/', views.alert_detail_view, name='alert_detail'),
    path('alerts/<int:alert_id>/resolve/', views.alert_resolve_view, name='alert_resolve'),
    path('alerts/<int:alert_id>/dismiss/', views.alert_dismiss_view, name='alert_dismiss'),
]