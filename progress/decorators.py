from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def permission_required(permission_name):
    """
    権限チェックデコレータ
    
    Args:
        permission_name (str): チェックする権限名
            - 'manage_students': 研修生管理権限
            - 'manage_curriculum': カリキュラム管理権限
            - 'manage_groups': グループ管理権限
            - 'view_analytics': 分析画面閲覧権限
            - 'manage_system': システム管理権限
            - 'manage_users': ユーザー管理権限
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            # 権限チェック
            permission_attr = f'can_{permission_name}'
            
            if not hasattr(user, permission_attr):
                messages.error(request, '無効な権限が指定されました。')
                return redirect('login')
            
            if not getattr(user, permission_attr):
                messages.error(request, 'この機能にアクセスする権限がありません。')
                # ユーザータイプに応じてリダイレクト先を変更
                if user.user_type == 'student':
                    return redirect('student_dashboard')
                elif user.is_training_admin:
                    return redirect('training_admin_dashboard')
                elif user.is_system_admin:
                    return redirect('system_admin_dashboard')
                else:
                    return redirect('login')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def training_admin_required(view_func):
    """研修管理者以上の権限が必要"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_training_admin or request.user.is_system_admin):
            messages.error(request, '研修管理者権限が必要です。')
            if request.user.user_type == 'student':
                return redirect('student_dashboard')
            else:
                return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def system_admin_required(view_func):
    """システム管理者権限が必要"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_system_admin:
            messages.error(request, 'システム管理者権限が必要です。')
            if request.user.user_type == 'student':
                return redirect('student_dashboard')
            elif request.user.is_training_admin:
                return redirect('training_admin_dashboard')
            else:
                return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def student_required(view_func):
    """研修生権限が必要"""
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.user_type != 'student':
            messages.error(request, 'この機能は研修生専用です。')
            if request.user.is_training_admin:
                return redirect('training_admin_dashboard')
            elif request.user.is_system_admin:
                return redirect('system_admin_dashboard')
            else:
                return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper