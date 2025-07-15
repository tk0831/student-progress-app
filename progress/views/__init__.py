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
    group_ranking_view, group_update_view, group_delete_view,
    group_members_view
)
from .analytics import feedback_analytics_view, feedback_detail_view, feedback_requests_list_view
from .export import export_data_view, export_menu_view
from .api import get_user_weekly_rankings, get_weekly_summary, analytics_data_api, get_phase_items, get_last_week_mvp
from .stamp import add_stamp, get_progress_stamps, get_stamp_summary
from .training_edit import (
    edit_user_training, edit_progress_history, edit_progress_record,
    delete_progress_record, ajax_get_phase_items, batch_update_progress,
    edit_item_progress
)
from .alerts import (
    alert_list_view, alert_detail_view, alert_resolve_view,
    alert_dismiss_view, alert_widget_view
)

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
    'group_ranking_view', 'group_update_view', 'group_delete_view',
    'group_members_view',
    # 分析関連
    'feedback_analytics_view', 'feedback_detail_view', 'feedback_requests_list_view',
    # エクスポート関連
    'export_data_view', 'export_menu_view',
    # API関連
    'get_user_weekly_rankings', 'get_weekly_summary', 'analytics_data_api', 'get_phase_items', 'get_last_week_mvp',
    # スタンプ関連
    'add_stamp', 'get_progress_stamps', 'get_stamp_summary',
    # 研修編集関連（システム管理者用）
    'edit_user_training', 'edit_progress_history', 'edit_progress_record',
    'delete_progress_record', 'ajax_get_phase_items', 'batch_update_progress',
    'edit_item_progress',
    # アラート関連
    'alert_list_view', 'alert_detail_view', 'alert_resolve_view',
    'alert_dismiss_view', 'alert_widget_view'
]