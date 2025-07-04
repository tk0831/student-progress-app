from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg, Count, Q
from django.core.paginator import Paginator
from datetime import datetime, date, timedelta
from ..models import CustomUser, Group, Phase, CurriculumItem, DailyProgress, UserStats
from ..forms import UserCreateForm, UserGroupAssignForm
from ..decorators import permission_required, system_admin_required


@permission_required('manage_students')
def user_list_view(request):
    """ユーザー一覧表示"""
    users = CustomUser.objects.filter(user_type='student').select_related('group', 'assigned_admin', 'stats')
    
    # フィルター処理
    group_filter = request.GET.get('group')
    grade_filter = request.GET.get('grade')
    admin_filter = request.GET.get('assigned_admin')  # Fixed parameter name
    search = request.GET.get('search')
    sort_by = request.GET.get('sort', 'username')
    order = request.GET.get('order', 'asc')
    
    if group_filter:
        users = users.filter(group_id=group_filter)
    
    if grade_filter:
        users = users.filter(stats__current_grade=grade_filter)
    
    if admin_filter:
        if admin_filter == 'none':
            users = users.filter(assigned_admin__isnull=True)
        else:
            users = users.filter(assigned_admin_id=admin_filter)
    
    if search:
        users = users.filter(
            Q(username__icontains=search) | 
            Q(first_name__icontains=search) | 
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    # ソート処理
    sort_mapping = {
        'username': 'username',
        'group': 'group__name',
        'admin': 'assigned_admin__username',
        'start_date': 'start_date',
        'grade': 'stats__current_grade',
        'phase': 'stats__current_phase__phase_number',
        'completion': 'stats__completion_rate',
        'total_hours': 'stats__total_study_hours',
        'avg_hours': 'stats__average_daily_hours',
    }
    
    sort_field = sort_mapping.get(sort_by, 'username')
    if order == 'desc':
        sort_field = f'-{sort_field}'
    
    users = users.order_by(sort_field)
    
    # ページネーション前に各ユーザーの統計情報を計算
    users_list = list(users)
    
    # 各ユーザーに対して統計情報を計算
    for user in users_list:
        if hasattr(user, 'stats') and user.stats:
            # 進捗状況を計算
            user.progress_status = user.stats.calculate_progress_status()
            # 研修終了見込みを計算
            user.graduation_estimate = user.stats.calculate_graduation_estimate()
            # 経過日数を計算
            if user.start_date:
                user.days_elapsed = (date.today() - user.start_date).days + 1
            else:
                user.days_elapsed = 0
        else:
            user.progress_status = None
            user.graduation_estimate = None
            user.days_elapsed = 0
    
    # 特殊なソート処理が必要なフィールド
    if sort_by == 'graduation':
        # 卒業見込みでソート（年→月の順）
        def graduation_sort_key(user):
            if not user.graduation_estimate:
                return (9999, 12)  # 算出不可は最後に
            completion_date = user.graduation_estimate.get('estimated_completion_date')
            if not completion_date:
                return (9999, 12)
            return (completion_date.year, completion_date.month)
        
        reverse = (order == 'desc')
        users_list.sort(key=graduation_sort_key, reverse=reverse)
        
    elif sort_by == 'grade':
        # 階級でソート（S→A→B→C→Dの順）
        grade_order = {'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4}
        def grade_sort_key(user):
            if hasattr(user, 'stats') and user.stats:
                return grade_order.get(user.stats.current_grade, 5)
            return 5
        
        reverse = (order != 'asc')  # 昇順の時はS→D、降順の時はD→S
        users_list.sort(key=grade_sort_key, reverse=reverse)
        
    elif sort_by == 'total_hours':
        # 累計学習時間でソート
        def hours_sort_key(user):
            if hasattr(user, 'stats') and user.stats:
                return user.stats.total_study_hours or 0
            return 0
        
        reverse = (order == 'desc')
        users_list.sort(key=hours_sort_key, reverse=reverse)
        
    elif sort_by == 'avg_hours':
        # 平均学習時間でソート
        def avg_hours_sort_key(user):
            if hasattr(user, 'stats') and user.stats:
                return user.stats.average_daily_hours or 0
            return 0
        
        reverse = (order == 'desc')
        users_list.sort(key=avg_hours_sort_key, reverse=reverse)
        
    elif sort_by == 'elapsed_days':
        # 経過日数でソート
        def days_sort_key(user):
            return user.days_elapsed
        
        reverse = (order == 'desc')
        users_list.sort(key=days_sort_key, reverse=reverse)
        
    elif sort_by == 'progress_status':
        # 進捗状況でソート（先行→順調→遅れ→不明の順）
        def progress_sort_key(user):
            if not user.progress_status:
                return (3, 0)  # 不明は最後
            if user.progress_status.get('is_ahead'):
                # 先行（delay_daysが大きいほど上位）
                return (0, -user.progress_status.get('delay_days', 0))
            elif user.progress_status.get('is_on_track'):
                return (1, 0)  # 順調
            elif user.progress_status.get('is_behind'):
                # 遅れ（delay_daysの絶対値が大きいほど下位）
                return (2, -user.progress_status.get('delay_days', 0))
            else:
                return (1, 0)  # デフォルトは順調扱い
        
        reverse = (order == 'desc')
        users_list.sort(key=progress_sort_key, reverse=reverse)
    
    # ページネーション
    paginator = Paginator(users_list, 20)
    page_number = request.GET.get('page')
    users_page = paginator.get_page(page_number)
    
    context = {
        'users': users_page,
        'groups': Group.objects.all(),
        'grades': DailyProgress.GRADE_CHOICES,
        'training_admins': CustomUser.objects.filter(user_type='training_admin'),  # Renamed to match template
        'selected_admin': admin_filter,  # Added for filter selection
        'current_filters': {
            'group': group_filter,
            'grade': grade_filter,
            'admin': admin_filter,
            'search': search,
        },
        'current_sort': {
            'sort': sort_by,
            'order': order,
        }
    }
    
    return render(request, 'progress/user/user_list.html', context)


@permission_required('view_analytics')
def user_detail_view(request, user_id):
    """ユーザー詳細表示"""
    user = get_object_or_404(CustomUser, id=user_id, user_type='student')
    user_stats, created = UserStats.objects.get_or_create(user=user)
    
    # 進捗記録
    progress_records = DailyProgress.objects.filter(user=user).order_by('-date')[:30]
    
    # 統計情報
    total_records = DailyProgress.objects.filter(user=user).count()
    total_hours = DailyProgress.objects.filter(user=user).aggregate(
        total=Sum('study_hours'))['total'] or 0
    avg_hours = total_hours / total_records if total_records > 0 else 0
    
    # 曜日別学習時間（過去30日）
    weekday_stats = {}
    for i in range(7):  # 0=月曜日, 6=日曜日
        weekday_hours = DailyProgress.objects.filter(
            user=user,
            date__gte=date.today() - timedelta(days=30),
            date__week_day=(i + 2) % 7 + 1  # Djangoの週の始まりは日曜=1
        ).aggregate(avg=Avg('study_hours'))['avg'] or 0
        
        weekday_names = ['月', '火', '水', '木', '金', '土', '日']
        weekday_stats[weekday_names[i]] = round(weekday_hours, 1)
    
    # 項目別学習期間分析
    item_analysis = []
    completed_items = DailyProgress.objects.filter(
        user=user, item_completed=True
    ).values('current_item', 'current_item__name', 'current_item__item_code', 
             'current_item__estimated_days').distinct()
    
    for item_data in completed_items:
        item_id = item_data['current_item']
        
        # 項目の開始日と終了日を取得
        item_records = DailyProgress.objects.filter(
            user=user, current_item_id=item_id
        ).order_by('date')
        
        if item_records.exists():
            start_date = item_records.first().date
            end_date = item_records.last().date
            actual_days = (end_date - start_date).days + 1
            estimated_days = item_data['current_item__estimated_days'] or 1
            
            efficiency_ratio = estimated_days / actual_days if actual_days > 0 else 0
            
            # 効率判定
            if efficiency_ratio >= 1.25:
                status = '優秀'
                status_class = 'text-blue-600'
            elif efficiency_ratio >= 1.0:
                status = '良好'
                status_class = 'text-green-600'
            elif efficiency_ratio >= 0.67:
                status = '標準'
                status_class = 'text-yellow-600'
            else:
                status = '要改善'
                status_class = 'text-red-600'
            
            item_analysis.append({
                'item_code': item_data['current_item__item_code'],
                'item_name': item_data['current_item__name'],
                'estimated_days': estimated_days,
                'actual_days': actual_days,
                'efficiency_ratio': round(efficiency_ratio, 2),
                'status': status,
                'status_class': status_class
            })
    
    # 進捗状況判定
    if user_stats.delay_days > 5:
        progress_status = '大幅先行'
        progress_class = 'text-blue-600'
    elif user_stats.delay_days > 0:
        progress_status = '順調'
        progress_class = 'text-green-600'
    elif user_stats.delay_days > -5:
        progress_status = '注意'
        progress_class = 'text-yellow-600'
    else:
        progress_status = '要改善'
        progress_class = 'text-red-600'
    
    context = {
        'target_user': user,  # テンプレートで使用している変数名に合わせる
        'user_stats': user_stats,
        'progress_records': progress_records,
        'total_records': total_records,
        'total_hours': total_hours,
        'avg_hours': round(avg_hours, 1),
        'weekday_stats': weekday_stats,
        'item_analysis': item_analysis,
        'progress_status': progress_status,
        'progress_class': progress_class,
    }
    
    return render(request, 'progress/user/user_detail.html', context)


@system_admin_required
def user_create_view(request):
    """ユーザー作成"""
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'ユーザー「{user.username}」を作成しました。')
            return redirect('user_list')
    else:
        form = UserCreateForm()
    
    return render(request, 'progress/user/user_form.html', {'form': form, 'action': '新規作成'})


@system_admin_required
def user_update_view(request, user_id):
    """ユーザー更新"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'ユーザー「{user.username}」を更新しました。')
            return redirect('user_list')
    else:
        form = UserCreateForm(instance=user)
    
    return render(request, 'progress/user/user_form.html', {'form': form, 'action': '更新', 'user': user})


@permission_required('view_analytics')
def users_by_grade_view(request):
    """階級別ユーザー表示"""
    grade = request.GET.get('grade', 'A')
    
    users = CustomUser.objects.filter(
        user_type='student',
        stats__current_grade=grade
    ).select_related('group', 'assigned_admin', 'stats').order_by('-stats__completion_rate')
    
    context = {
        'users': users,
        'current_grade': grade,
        'grades': DailyProgress.GRADE_CHOICES,
    }
    
    return render(request, 'progress/user/users_by_grade.html', context)