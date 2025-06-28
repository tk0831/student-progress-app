from .auth import login_view, logout_view, register_view
from .dashboard import student_dashboard, training_admin_dashboard, system_admin_dashboard
from .progress import (
    progress_form, progress_list_view, progress_detail_view,
    progress_delete_view, progress_detail_modal, progress_analytics_view,
    progress_calendar
)
from .user import (
    user_list_view, user_detail_view, user_create_view, user_update_view,
    users_by_grade_view
)
from .group import (
    group_list_view, group_create_view, group_detail_view, 
    group_ranking_view, group_update_view
)
from .analytics import feedback_analytics_view, feedback_detail_view, feedback_requests_list_view
from .export import export_data_view, export_menu_view
from .api import get_user_weekly_rankings, get_weekly_summary, analytics_data_api, get_phase_items

__all__ = [
    # 認証関連
    'login_view', 'logout_view', 'register_view',
    # ダッシュボード関連  
    'student_dashboard', 'training_admin_dashboard', 'system_admin_dashboard',
    # 進捗関連
    'progress_form', 'progress_list_view', 'progress_detail_view',
    'progress_delete_view', 'progress_detail_modal', 'progress_analytics_view',
    'progress_calendar',
    # ユーザー関連
    'user_list_view', 'user_detail_view', 'user_create_view', 'user_update_view',
    'users_by_grade_view',
    # グループ関連
    'group_list_view', 'group_create_view', 'group_detail_view',
    'group_ranking_view', 'group_update_view',
    # 分析関連
    'feedback_analytics_view', 'feedback_detail_view', 'feedback_requests_list_view',
    # エクスポート関連
    'export_data_view', 'export_menu_view',
    # API関連
    'get_user_weekly_rankings', 'get_weekly_summary', 'analytics_data_api', 'get_phase_items'
]