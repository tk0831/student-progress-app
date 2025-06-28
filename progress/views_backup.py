from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from django.http import JsonResponse, HttpResponse
import calendar
from datetime import datetime, date, timedelta
import json
import csv
from .models import CustomUser, Group, Phase, CurriculumItem, DailyProgress, UserStats, WeeklyRanking
from .forms import DailyProgressForm, LoginForm, GroupForm, UserGroupAssignForm, UserCreateForm, UserRegistrationForm
from .decorators import (
    permission_required, training_admin_required, 
    system_admin_required, student_required
)


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # ユーザータイプ別にリダイレクト
                if user.user_type == 'student':
                    return redirect('student_dashboard')
                elif user.user_type == 'training_admin':
                    return redirect('training_admin_dashboard')
                elif user.user_type == 'system_admin':
                    return redirect('system_admin_dashboard')
                else:
                    # 旧データ対応
                    return redirect('training_admin_dashboard')
            else:
                messages.error(request, 'ユーザー名またはパスワードが正しくありません。')
    else:
        form = LoginForm()
    
    return render(request, 'progress/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'ログアウトしました。')
    return redirect('login')


def register_view(request):
    """新規ユーザー登録（誰でも登録可能）"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 自動的にログイン
            login(request, user)
            messages.success(request, f'ようこそ、{user.username}さん！アカウントを作成しました。')
            return redirect('student_dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'progress/register.html', {'form': form})


@student_required
def student_dashboard(request):
    user_stats, created = UserStats.objects.get_or_create(user=request.user)
    recent_progress = DailyProgress.objects.filter(user=request.user).order_by('-date')[:7]
    
    # 週間ランキングを取得（受賞した場合のみ表示）
    current_rankings = get_user_weekly_rankings(request.user)
    
    context = {
        'user_stats': user_stats,
        'recent_progress': recent_progress,
        'phases': Phase.objects.all(),
        'current_rankings': current_rankings,
    }
    return render(request, 'progress/student_dashboard.html', context)


@permission_required('view_analytics')
def training_admin_dashboard(request):
    """研修管理者専用ダッシュボード"""
    total_students = CustomUser.objects.filter(user_type='student').count()
    recent_progress = DailyProgress.objects.order_by('-date')[:10]
    
    grade_stats = {}
    for grade, label in DailyProgress.GRADE_CHOICES:
        count = UserStats.objects.filter(current_grade=grade).count()
        grade_stats[label] = count
    
    # 研修管理者はグループと学生進捗のみ確認可能
    context = {
        'total_students': total_students,
        'recent_progress': recent_progress,
        'grade_stats': grade_stats,
        'groups': Group.objects.all(),
        'user_type': 'training_admin'
    }
    return render(request, 'progress/training_admin_dashboard.html', context)





@login_required
def progress_create(request):
    if request.user.user_type != 'student':
        return redirect('training_admin_dashboard')
    
    today = timezone.now().date()
    existing_progress = DailyProgress.objects.filter(user=request.user, date=today).first()
    
    if request.method == 'POST':
        form = DailyProgressForm(request.POST, instance=existing_progress, user=request.user)
        if form.is_valid():
            progress = form.save(commit=False)
            progress.user = request.user
            progress.date = today
            
            # 経過日数を計算
            if request.user.start_date:
                progress.days_elapsed = (today - request.user.start_date).days + 1
            
            # 次の項目に進んだ場合、前の項目を自動完了とする
            if existing_progress:
                previous_item = existing_progress.current_item
                previous_phase = existing_progress.current_phase
                
                # 項目またはPhaseが変わった場合、前の項目を完了扱いにする
                if (progress.current_item != previous_item or 
                    progress.current_phase != previous_phase):
                    
                    # 前日までの最新記録で、前の項目の最後の記録を完了扱いにする
                    last_previous_record = DailyProgress.objects.filter(
                        user=request.user,
                        current_item=previous_item,
                        current_phase=previous_phase,
                        date__lt=today
                    ).order_by('-date').first()
                    
                    if last_previous_record and not last_previous_record.item_completed:
                        last_previous_record.item_completed = True
                        last_previous_record.save()
            
            progress.save()
            
            # ユーザー統計を更新
            user_stats, created = UserStats.objects.get_or_create(user=request.user)
            user_stats.total_study_hours = DailyProgress.objects.filter(
                user=request.user
            ).aggregate(Sum('study_hours'))['study_hours__sum'] or 0
            user_stats.current_phase = progress.current_phase
            user_stats.current_item = progress.current_item
            user_stats.days_elapsed = progress.days_elapsed
            
            # すべての統計情報を一括更新（完了率・効率スコア・階級・遅れ状態）
            user_stats.update_all_stats()
            progress.current_grade = user_stats.current_grade
            progress.save()
            
            messages.success(request, '進捗記録を保存しました。')
            return redirect('student_dashboard')
    else:
        form = DailyProgressForm(instance=existing_progress, user=request.user)
    
    return render(request, 'progress/progress_form.html', {'form': form})


@login_required
def progress_list(request):
    # 権限チェック: 研修生は自分の記録のみ、管理者は全ての記録
    if request.user.user_type == 'student':
        queryset = DailyProgress.objects.filter(user=request.user)
    elif request.user.can_manage_students or request.user.is_system_admin:
        queryset = DailyProgress.objects.all()
    else:
        messages.error(request, '進捗一覧を閲覧する権限がありません。')
        return redirect('training_admin_dashboard')
    
    # フィルター処理
    user_filter = request.GET.get('user')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    phase_filter = request.GET.get('phase')
    grade_filter = request.GET.get('grade')
    
    if user_filter and request.user.user_type != 'student':
        queryset = queryset.filter(user__username__icontains=user_filter)
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    if phase_filter:
        queryset = queryset.filter(current_phase__phase_number=phase_filter)
    
    if grade_filter:
        queryset = queryset.filter(current_grade=grade_filter)
    
    # ページネーション（軽量化のため）
    from django.core.paginator import Paginator
    paginator = Paginator(queryset.select_related('user', 'current_phase', 'current_item').order_by('-date'), 20)
    page_number = request.GET.get('page')
    progress_list = paginator.get_page(page_number)
    
    # Ajax リクエストの場合は JSON で返す
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        data = []
        for progress in progress_list:
            data.append({
                'id': progress.id,
                'date': progress.date.strftime('%Y/%m/%d'),
                'user': progress.user.username if request.user.user_type != 'student' else None,
                'phase': f"Phase {progress.current_phase.phase_number}",
                'item': progress.current_item.item_code,
                'study_hours': str(progress.study_hours),
                'grade': progress.current_grade,
                'days_elapsed': progress.days_elapsed,
                'delay_days': progress.delay_days,
                'feedback_requested': progress.feedback_requested,
                'can_edit': request.user.user_type == 'student' and progress.user == request.user or request.user.user_type != 'student'
            })
        
        return JsonResponse({
            'progress_list': data,
            'has_next': progress_list.has_next(),
            'has_previous': progress_list.has_previous(),
            'page_number': progress_list.number,
            'total_pages': progress_list.paginator.num_pages,
            'total_count': progress_list.paginator.count
        })
    
    # 管理者用：ユーザー選択肢とフィルター情報
    context = {
        'progress_list': progress_list,
        'current_filters': {
            'user': user_filter,
            'date_from': date_from,
            'date_to': date_to,
            'phase': phase_filter,
            'grade': grade_filter,
        }
    }
    
    if request.user.user_type != 'student':
        context['users'] = CustomUser.objects.filter(user_type='student').order_by('username')
        context['phases'] = Phase.objects.all().order_by('phase_number')
        context['grades'] = DailyProgress.GRADE_CHOICES
    
    return render(request, 'progress/progress_list.html', context)


@login_required
def progress_edit(request, progress_id):
    progress = get_object_or_404(DailyProgress, id=progress_id)
    
    # 権限チェック: 研修生は自分の記録のみ、管理者は全ての記録
    if request.user.user_type == 'student' and progress.user != request.user:
        messages.error(request, '他の研修生の進捗記録は編集できません。')
        return redirect('progress_list')
    
    # 研修管理者以上の権限チェック（研修生以外のアクセス時）
    if request.user.user_type != 'student' and not (request.user.can_manage_students or request.user.is_system_admin):
        messages.error(request, '進捗記録を編集する権限がありません。')
        return redirect('training_admin_dashboard')
    
    if request.method == 'POST':
        form = DailyProgressForm(request.POST, instance=progress, user=progress.user)
        if form.is_valid():
            progress = form.save(commit=False)
            
            # 経過日数を再計算
            if progress.user.start_date:
                progress.days_elapsed = (progress.date - progress.user.start_date).days + 1
            
            progress.save()
            
            # ユーザー統計を更新
            user_stats, created = UserStats.objects.get_or_create(user=progress.user)
            user_stats.total_study_hours = DailyProgress.objects.filter(
                user=progress.user
            ).aggregate(Sum('study_hours'))['study_hours__sum'] or 0
            user_stats.current_phase = progress.current_phase
            user_stats.current_item = progress.current_item
            user_stats.days_elapsed = progress.days_elapsed
            
            # すべての統計情報を一括更新（完了率・効率スコア・階級・遅れ状態）
            user_stats.update_all_stats()
            progress.current_grade = user_stats.current_grade
            progress.save()
            
            messages.success(request, '進捗記録を更新しました。')
            return redirect('progress_list')
    else:
        form = DailyProgressForm(instance=progress, user=progress.user)
    
    context = {
        'form': form,
        'progress': progress,
        'is_edit': True
    }
    return render(request, 'progress/progress_form.html', context)


@login_required
def progress_delete(request, progress_id):
    progress = get_object_or_404(DailyProgress, id=progress_id)
    
    # 権限チェック: 研修生は自分の記録のみ、管理者は全ての記録
    if request.user.user_type == 'student' and progress.user != request.user:
        messages.error(request, '他の研修生の進捗記録は削除できません。')
        return redirect('progress_list')
    
    # 研修管理者以上の権限チェック（研修生以外のアクセス時）
    if request.user.user_type != 'student' and not (request.user.can_manage_students or request.user.is_system_admin):
        messages.error(request, '進捗記録を削除する権限がありません。')
        return redirect('training_admin_dashboard')
    
    if request.method == 'POST':
        user = progress.user
        progress.delete()
        
        # ユーザー統計を再計算
        user_stats, created = UserStats.objects.get_or_create(user=user)
        latest_progress = DailyProgress.objects.filter(user=user).order_by('-date').first()
        
        if latest_progress:
            user_stats.total_study_hours = DailyProgress.objects.filter(
                user=user
            ).aggregate(Sum('study_hours'))['study_hours__sum'] or 0
            user_stats.current_phase = latest_progress.current_phase
            user_stats.current_item = latest_progress.current_item
            user_stats.current_grade = latest_progress.current_grade
            user_stats.days_elapsed = latest_progress.days_elapsed
        else:
            user_stats.total_study_hours = 0
            user_stats.current_phase = None
            user_stats.current_item = None
            user_stats.current_grade = 'A'
            user_stats.days_elapsed = 0
        
        user_stats.save()
        
        # 完了率を新しいロジックで更新
        if user_stats:
            user_stats.update_completion_rate()
        
        messages.success(request, '進捗記録を削除しました。')
        return redirect('progress_list')
    
    context = {
        'progress': progress
    }
    return render(request, 'progress/progress_delete.html', context)


@permission_required('view_analytics')
def group_ranking(request):
    from datetime import date, timedelta
    
    groups = Group.objects.all()
    ranking_data = []
    
    # 日報提出度計算用の期間設定（過去30日）
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    expected_days = (end_date - start_date).days + 1
    
    for group in groups:
        students = CustomUser.objects.filter(group=group, user_type='student').select_related('stats')
        if students.exists():
            group_completion_rates = []
            daily_hours_list = []  # 各メンバーの一日平均学習時間のリスト
            total_students = 0
            total_report_submissions = 0
            total_possible_submissions = 0
            
            for student in students:
                try:
                    if hasattr(student, 'stats') and student.stats:
                        stats = student.stats
                        group_completion_rates.append(float(stats.completion_rate))
                        
                        # 一日平均学習時間を計算（経過日数で割る）
                        if student.start_date:
                            # 研修開始からの経過日数を計算
                            days_elapsed = (date.today() - student.start_date).days + 1
                            if days_elapsed > 0:
                                daily_avg = float(stats.total_study_hours) / days_elapsed
                                daily_hours_list.append(daily_avg)
                            else:
                                daily_hours_list.append(0)
                        else:
                            daily_hours_list.append(0)
                            
                        total_students += 1
                        
                        # 日報提出度計算（過去30日）
                        submitted_days = DailyProgress.objects.filter(
                            user=student,
                            date__gte=start_date,
                            date__lte=end_date
                        ).count()
                        
                        # 学習開始日を考慮した期待提出日数
                        if student.start_date:
                            student_start = max(student.start_date, start_date)
                            if student_start <= end_date:
                                expected_student_days = (end_date - student_start).days + 1
                                total_possible_submissions += expected_student_days
                                total_report_submissions += submitted_days
                        else:
                            total_possible_submissions += expected_days
                            total_report_submissions += submitted_days
                    else:
                        group_completion_rates.append(0.0)
                        daily_hours_list.append(0)
                        total_students += 1
                        total_possible_submissions += expected_days
                except Exception as e:
                    group_completion_rates.append(0.0)
                    daily_hours_list.append(0)
                    total_students += 1
                    total_possible_submissions += expected_days
            
            avg_completion = sum(group_completion_rates) / len(group_completion_rates) if group_completion_rates else 0
            # グループ内メンバーの一日平均学習時間の平均を計算
            avg_daily_hours = sum(daily_hours_list) / len(daily_hours_list) if daily_hours_list else 0
            report_submission_rate = (total_report_submissions / total_possible_submissions * 100) if total_possible_submissions > 0 else 0
            
            ranking_data.append({
                'group': group,
                'student_count': total_students,
                'avg_completion': avg_completion,
                'avg_daily_hours': round(avg_daily_hours, 1),
                'report_submission_rate': round(report_submission_rate, 1),
                'total_reports': total_report_submissions,
                'expected_reports': total_possible_submissions,
                'performance_level': 'excellent' if avg_completion >= 80 else 
                                   'good' if avg_completion >= 60 else
                                   'average' if avg_completion >= 40 else 'below'
            })
    
    # ソート基準を選択可能にする
    sort_by = request.GET.get('sort', 'completion')  # completion, reports, hours
    
    if sort_by == 'reports':
        ranking_data.sort(key=lambda x: x['report_submission_rate'], reverse=True)
    elif sort_by == 'hours':
        ranking_data.sort(key=lambda x: x['avg_daily_hours'], reverse=True)
    else:  # default: completion
        ranking_data.sort(key=lambda x: x['avg_completion'], reverse=True)
    
    context = {
        'ranking_data': ranking_data,
        'current_sort': sort_by,
        'period_days': expected_days,
    }
    
    return render(request, 'progress/group_ranking.html', context)


@permission_required('view_analytics')
def progress_calendar(request):
    # 現在の年月、またはGETパラメータから取得
    today = timezone.now().date()
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))
    
    # 表示対象ユーザーの決定
    if request.user.user_type == 'student':
        target_user = request.user
    else:
        user_id = request.GET.get('user_id')
        if user_id:
            target_user = get_object_or_404(CustomUser, id=user_id, user_type='student')
        else:
            target_user = request.user
    
    # カレンダー生成
    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり
    month_days = cal.monthdayscalendar(year, month)
    
    # 該当月の進捗記録を取得
    progress_records = DailyProgress.objects.filter(
        user=target_user,
        date__year=year,
        date__month=month
    ).select_related('current_phase', 'current_item')
    
    # 日付ごとの進捗データを辞書化
    progress_dict = {p.date.day: p for p in progress_records}
    
    # カレンダーデータ構築
    calendar_weeks = []
    for week in month_days:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                day_date = date(year, month, day)
                progress = progress_dict.get(day)
                week_data.append({
                    'day': day,
                    'date': day_date,
                    'progress': progress,
                    'is_today': day_date == today,
                    'is_future': day_date > today,
                })
        calendar_weeks.append(week_data)
    
    # 前月・次月の計算
    if month == 1:
        prev_month, prev_year = 12, year - 1
    else:
        prev_month, prev_year = month - 1, year
        
    if month == 12:
        next_month, next_year = 1, year + 1
    else:
        next_month, next_year = month + 1, year
    
    # 統計情報
    month_stats = {
        'total_days': len([d for d in progress_dict.keys()]),
        'total_hours': sum(p.study_hours for p in progress_records),
        'avg_hours': sum(p.study_hours for p in progress_records) / len(progress_records) if progress_records else 0,
    }
    
    # 管理者用：ユーザー選択肢
    students = None
    if request.user.user_type != 'student' and (request.user.can_view_analytics or request.user.is_system_admin):
        students = CustomUser.objects.filter(user_type='student').order_by('username')
    
    context = {
        'calendar_weeks': calendar_weeks,
        'year': year,
        'month': month,
        'month_name': calendar.month_name[month],
        'target_user': target_user,
        'month_stats': month_stats,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'students': students,
    }
    
    return render(request, 'progress/progress_calendar.html', context)


@permission_required('manage_groups')
def group_list(request):
    """グループ一覧表示"""
    groups = Group.objects.all().prefetch_related('customuser_set')
    
    group_data = []
    total_students = 0
    
    for group in groups:
        students = group.customuser_set.filter(user_type='student')
        student_count = students.count()
        total_students += student_count
        
        group_data.append({
            'group': group,
            'student_count': student_count,
            'students': students,
        })
    
    # 統計計算
    avg_members = total_students / len(groups) if groups else 0
    
    context = {
        'group_data': group_data,
        'total_groups': len(groups),
        'total_students': total_students,
        'avg_members': avg_members,
    }
    
    return render(request, 'progress/group_list.html', context)


@permission_required('manage_groups')
def group_create(request):
    """グループ作成"""
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'グループ「{group.name}」を作成しました。')
            return redirect('group_list')
    else:
        form = GroupForm()
    
    return render(request, 'progress/group_form.html', {
        'form': form,
        'title': 'グループ作成',
        'action': 'create'
    })


@permission_required('manage_groups')
def group_edit(request, group_id):
    """グループ編集"""
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'グループ「{group.name}」を更新しました。')
            return redirect('group_list')
    else:
        form = GroupForm(instance=group)
    
    return render(request, 'progress/group_form.html', {
        'form': form,
        'group': group,
        'title': 'グループ編集',
        'action': 'edit'
    })


@permission_required('manage_groups')
def group_delete(request, group_id):
    """グループ削除"""
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        # グループに所属する研修生のグループを解除
        students = group.customuser_set.filter(user_type='student')
        for student in students:
            student.group = None
            student.save()
        
        group_name = group.name
        group.delete()
        messages.success(request, f'グループ「{group_name}」を削除しました。')
        return redirect('group_list')
    
    students = group.customuser_set.filter(user_type='student')
    return render(request, 'progress/group_delete.html', {
        'group': group,
        'students': students
    })


@permission_required('manage_groups')
def group_members(request, group_id):
    """グループメンバー管理"""
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        form = UserGroupAssignForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, f'グループ「{group.name}」のメンバーを更新しました。')
            return redirect('group_list')
    else:
        form = UserGroupAssignForm(instance=group)
    
    return render(request, 'progress/group_members.html', {
        'form': form,
        'group': group
    })


@permission_required('manage_students')
def user_list(request):
    """ユーザー一覧表示"""
    students = CustomUser.objects.filter(user_type='student').select_related('group', 'stats', 'stats__current_phase', 'stats__current_item', 'assigned_admin')
    
    # 担当者フィルター
    assigned_admin_id = request.GET.get('assigned_admin')
    if assigned_admin_id:
        if assigned_admin_id == 'none':
            students = students.filter(assigned_admin__isnull=True)
        else:
            students = students.filter(assigned_admin_id=assigned_admin_id)
    
    # ソート処理
    sort_by = request.GET.get('sort', 'username')
    order = request.GET.get('order', 'asc')
    
    # ソートフィールドのマッピング
    sort_mapping = {
        'username': ('first_name', 'last_name'),  # 氏名（五十音順）
        'group': 'group__name',
        'admin': 'assigned_admin__username',
        'grade': 'stats__current_grade',
        'graduation': 'graduation_month',  # 研修終了見込み月
        'completion': 'stats__completion_rate',
        'hours': 'stats__total_study_hours',
        'days': 'stats__days_elapsed',
        'phase': 'stats__current_phase__phase_number',
        'progress': 'stats__delay_days',
    }
    
    # デフォルトのソートフィールド
    sort_field = sort_mapping.get(sort_by, ('first_name', 'last_name'))
    
    # 特別なソート処理が必要でない場合の事前ソート
    if sort_by not in ['grade', 'graduation']:
        # 通常のソート処理
        if isinstance(sort_field, tuple):
            # 複数フィールドの場合（氏名の五十音順）
            if order == 'desc':
                sort_fields = ['-' + field for field in sort_field]
            else:
                sort_fields = list(sort_field)
            students = students.order_by(*sort_fields)
        else:
            # 単一フィールドの場合
            if order == 'desc':
                sort_field = '-' + sort_field
            students = students.order_by(sort_field)
    elif sort_by == 'grade':
        # S->A->B->C->Dの順番でソート
        from django.db.models import Case, When, IntegerField
        grade_order = Case(
            When(stats__current_grade='S', then=1),
            When(stats__current_grade='A', then=2),
            When(stats__current_grade='B', then=3),
            When(stats__current_grade='C', then=4),
            When(stats__current_grade='D', then=5),
            default=6,
            output_field=IntegerField()
        )
        if order == 'desc':
            students = students.annotate(grade_order=grade_order).order_by('-grade_order')
        else:
            students = students.annotate(grade_order=grade_order).order_by('grade_order')
    
    # 各ユーザーの進捗状況と研修終了見込みを計算
    for student in students:
        if hasattr(student, 'stats') and student.stats:
            student.progress_status = student.stats.calculate_progress_status()
            student.graduation_estimate = student.stats.calculate_graduation_estimate()
            # ソート用の年月番号を追加
            if student.graduation_estimate:
                try:
                    # month_nameは「2025年3月」の形式
                    month_name = student.graduation_estimate['month_name']
                    # 正規表現で年と月を抽出
                    import re
                    match = re.match(r'(\d{4})年(\d{1,2})月', month_name)
                    if match:
                        year = int(match.group(1))
                        month = int(match.group(2))
                        # ソート用の値：年*100 + 月で計算（例：202503 = 2025年3月）
                        student.graduation_sort_key = year * 100 + month
                    else:
                        student.graduation_sort_key = 999999
                except (KeyError, ValueError, TypeError):
                    student.graduation_sort_key = 999999  # 不明な場合は最後にソート
            else:
                student.graduation_sort_key = 999999
        else:
            student.progress_status = None
            student.graduation_estimate = None
            student.graduation_sort_key = 999999
    
    # 研修終了見込み月でのソート処理
    if sort_by == 'graduation':
        if order == 'desc':
            students = sorted(students, key=lambda x: x.graduation_sort_key, reverse=True)
        else:
            students = sorted(students, key=lambda x: x.graduation_sort_key)
    
    # 研修管理者リストを取得（フィルター用）
    training_admins = CustomUser.objects.filter(user_type='training_admin').order_by('username')
    
    context = {
        'students': students,
        'training_admins': training_admins,
        'selected_admin': assigned_admin_id,
    }
    
    return render(request, 'progress/user_list.html', context)




@permission_required('manage_students')
def user_edit(request, user_id):
    """ユーザー編集"""
    user = get_object_or_404(CustomUser, id=user_id, user_type='student')
    
    if request.method == 'POST':
        # パスワード変更なしの場合の処理
        data = request.POST.copy()
        if not data.get('password'):
            data['password'] = 'dummy'  # ダミーパスワード
            data['password_confirm'] = 'dummy'
        
        form = UserCreateForm(data, instance=user, current_user=request.user)
        if form.is_valid():
            user = form.save(commit=False)
            # パスワードが入力されていない場合は更新しない
            if not request.POST.get('password'):
                user.save()
            else:
                user.set_password(form.cleaned_data['password'])
                user.save()
            
            messages.success(request, f'ユーザー「{user.username}」を更新しました。')
            return redirect('user_list')
    else:
        form = UserCreateForm(instance=user, current_user=request.user)
        # 編集時はパスワードフィールドを非必須に
        form.fields['password'].required = False
        form.fields['password_confirm'].required = False
        form.fields['password'].help_text = '変更する場合のみ入力してください'
        form.fields['password_confirm'].help_text = '変更する場合のみ入力してください'
    
    return render(request, 'progress/user_form.html', {
        'form': form,
        'user': user,
        'title': 'ユーザー編集',
        'action': 'edit'
    })


@permission_required('view_analytics')
def progress_analytics(request):
    """進捗分析ページ"""
    # 表示対象ユーザーの決定
    if request.user.user_type == 'student':
        target_user = request.user
        students = [request.user]
    else:
        user_id = request.GET.get('user_id')
        if user_id:
            target_user = get_object_or_404(CustomUser, id=user_id, user_type='student')
            students = [target_user]
        else:
            # 管理者の場合は全体分析
            target_user = None
            students = CustomUser.objects.filter(user_type='student')
    
    # 基本統計
    if target_user:
        total_progress = DailyProgress.objects.filter(user=target_user).count()
        total_hours = DailyProgress.objects.filter(user=target_user).aggregate(
            total=Sum('study_hours'))['total'] or 0
        avg_hours = total_hours / total_progress if total_progress > 0 else 0
        
        # 最新の進捗
        latest_progress = DailyProgress.objects.filter(user=target_user).order_by('-date').first()
        current_grade = latest_progress.current_grade if latest_progress else 'A'
    else:
        total_progress = DailyProgress.objects.count()
        total_hours = DailyProgress.objects.aggregate(total=Sum('study_hours'))['total'] or 0
        avg_hours = total_hours / total_progress if total_progress > 0 else 0
        current_grade = None
    
    # 管理者用：ユーザー選択肢
    all_students = None
    if request.user.user_type != 'student' and (request.user.can_view_analytics or request.user.is_system_admin):
        all_students = CustomUser.objects.filter(user_type='student').order_by('username')
    
    context = {
        'target_user': target_user,
        'all_students': all_students,
        'total_progress': total_progress,
        'total_hours': total_hours,
        'avg_hours': avg_hours,
        'current_grade': current_grade,
    }
    
    return render(request, 'progress/progress_analytics.html', context)


@permission_required('view_analytics')
def analytics_data(request):
    """チャート用データAPI"""
    chart_type = request.GET.get('type', 'daily_hours')
    
    # 表示対象ユーザーの決定
    if request.user.user_type == 'student':
        target_users = [request.user]
    else:
        user_id = request.GET.get('user_id')
        if user_id:
            target_users = [get_object_or_404(CustomUser, id=user_id, user_type='student')]
        else:
            target_users = CustomUser.objects.filter(user_type='student')
    
    if chart_type == 'daily_hours':
        # 日別学習時間推移
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        data = []
        labels = []
        
        for i in range(31):
            current_date = start_date + timedelta(days=i)
            labels.append(current_date.strftime('%m/%d'))
            
            day_hours = DailyProgress.objects.filter(
                user__in=target_users,
                date=current_date
            ).aggregate(total=Sum('study_hours'))['total'] or 0
            
            data.append(float(day_hours))
        
        return JsonResponse({
            'labels': labels,
            'datasets': [{
                'label': '学習時間',
                'data': data,
                'borderColor': 'rgb(59, 130, 246)',
                'backgroundColor': 'rgba(59, 130, 246, 0.1)',
                'tension': 0.1
            }]
        })
    
    elif chart_type == 'phase_progress':
        # Phase別進捗状況
        phases = Phase.objects.all().order_by('phase_number')
        labels = [f"Phase {p.phase_number}" for p in phases]
        data = []
        
        for phase in phases:
            count = UserStats.objects.filter(
                user__in=target_users,
                current_phase=phase
            ).count()
            data.append(count)
        
        return JsonResponse({
            'labels': labels,
            'datasets': [{
                'label': '人数',
                'data': data,
                'backgroundColor': [
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(54, 162, 235, 0.8)',
                    'rgba(255, 205, 86, 0.8)',
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(153, 102, 255, 0.8)',
                    'rgba(255, 159, 64, 0.8)',
                    'rgba(199, 199, 199, 0.8)',
                ]
            }]
        })
    
    elif chart_type == 'grade_distribution':
        # 階級分布
        grades = ['S', 'A', 'B', 'C', 'D']
        labels = [f'{g}級' for g in grades]
        data = []
        
        for grade in grades:
            count = UserStats.objects.filter(
                user__in=target_users,
                current_grade=grade
            ).count()
            data.append(count)
        
        return JsonResponse({
            'labels': labels,
            'datasets': [{
                'label': '人数',
                'data': data,
                'backgroundColor': [
                    'rgba(147, 51, 234, 0.8)',  # S級: purple
                    'rgba(245, 158, 11, 0.8)',  # A級: yellow
                    'rgba(107, 114, 128, 0.8)', # B級: gray
                    'rgba(251, 146, 60, 0.8)',  # C級: orange
                    'rgba(239, 68, 68, 0.8)',   # D級: red
                ]
            }]
        })
    
    elif chart_type == 'weekly_hours':
        # 週別学習時間
        end_date = timezone.now().date()
        start_date = end_date - timedelta(weeks=12)
        
        labels = []
        data = []
        
        current_date = start_date
        while current_date <= end_date:
            week_end = min(current_date + timedelta(days=6), end_date)
            labels.append(f"{current_date.strftime('%m/%d')}〜")
            
            week_hours = DailyProgress.objects.filter(
                user__in=target_users,
                date__range=[current_date, week_end]
            ).aggregate(total=Sum('study_hours'))['total'] or 0
            
            data.append(float(week_hours))
            current_date += timedelta(days=7)
        
        return JsonResponse({
            'labels': labels,
            'datasets': [{
                'label': '週間学習時間',
                'data': data,
                'borderColor': 'rgb(34, 197, 94)',
                'backgroundColor': 'rgba(34, 197, 94, 0.1)',
                'tension': 0.1
            }]
        })
    
    elif chart_type == 'group_comparison':
        # グループ比較
        if request.user.user_type == 'student':
            return JsonResponse({'error': '権限がありません'}, status=403)
        
        groups = Group.objects.all()
        labels = [group.name for group in groups]
        avg_hours_data = []
        avg_completion_data = []
        
        for group in groups:
            students = group.customuser_set.filter(user_type='student')
            if students.exists():
                avg_hours = UserStats.objects.filter(
                    user__in=students
                ).aggregate(avg=Avg('total_study_hours'))['avg'] or 0
                
                avg_completion = UserStats.objects.filter(
                    user__in=students
                ).aggregate(avg=Avg('completion_rate'))['avg'] or 0
                
                avg_hours_data.append(float(avg_hours))
                avg_completion_data.append(float(avg_completion))
            else:
                avg_hours_data.append(0)
                avg_completion_data.append(0)
        
        return JsonResponse({
            'labels': labels,
            'datasets': [{
                'label': '平均学習時間',
                'data': avg_hours_data,
                'backgroundColor': 'rgba(59, 130, 246, 0.8)',
                'yAxisID': 'y'
            }, {
                'label': '平均完了率',
                'data': avg_completion_data,
                'backgroundColor': 'rgba(16, 185, 129, 0.8)',
                'yAxisID': 'y1'
            }]
        })
    
    return JsonResponse({'error': 'Invalid chart type'}, status=400)


@permission_required('view_analytics')
def export_progress_csv(request):
    """進捗データをCSVでエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="progress_export_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    # BOM付きUTF-8でExcel対応
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # ヘッダー行
    writer.writerow([
        '記録日', 'ユーザー名', 'グループ', '現在Phase', '現在項目', 
        '学習時間', '階級', '経過日数', '遅れ日数', '振り返り', 
        '明日の目標', 'フィードバック希望', '詰まった内容'
    ])
    
    # データ行
    progress_records = DailyProgress.objects.select_related(
        'user', 'user__group', 'current_phase', 'current_item'
    ).order_by('-date', 'user__username')
    
    for progress in progress_records:
        writer.writerow([
            progress.date.strftime('%Y-%m-%d'),
            progress.user.username,
            progress.user.group.name if progress.user.group else '未所属',
            f"Phase {progress.current_phase.phase_number}",
            progress.current_item.item_code,
            progress.study_hours,
            progress.current_grade,
            progress.days_elapsed,
            progress.delay_days,
            progress.reflection,
            progress.next_goal,
            'はい' if progress.feedback_requested else 'いいえ',
            progress.stuck_content,
        ])
    
    return response


@permission_required('view_analytics')
def export_users_csv(request):
    """ユーザー一覧をCSVでエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="users_export_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    # BOM付きUTF-8でExcel対応
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # ヘッダー行
    writer.writerow([
        'ユーザー名', '姓', '名', 'メールアドレス', 'ユーザータイプ', 
        'グループ', '研修開始日', '累計学習時間', '現在Phase', '現在項目',
        '現在階級', '経過日数', '遅れ日数', '完了率', '最終更新日'
    ])
    
    # データ行
    users = CustomUser.objects.filter(user_type='student').select_related(
        'group', 'stats', 'stats__current_phase', 'stats__current_item'
    ).order_by('username')
    
    for user in users:
        stats = getattr(user, 'stats', None)
        writer.writerow([
            user.username,
            user.first_name,
            user.last_name,
            user.email,
            user.get_user_type_display(),
            user.group.name if user.group else '未所属',
            user.start_date.strftime('%Y-%m-%d') if user.start_date else '',
            stats.total_study_hours if stats else 0,
            f"Phase {stats.current_phase.phase_number}" if stats and stats.current_phase else '',
            stats.current_item.item_code if stats and stats.current_item else '',
            stats.current_grade if stats else '',
            stats.days_elapsed if stats else 0,
            stats.delay_days if stats else 0,
            stats.completion_rate if stats else 0,
            stats.last_updated.strftime('%Y-%m-%d %H:%M') if stats else '',
        ])
    
    return response


@permission_required('view_analytics')
def export_groups_csv(request):
    """グループ統計をCSVでエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="groups_export_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    # BOM付きUTF-8でExcel対応
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # ヘッダー行
    writer.writerow([
        'グループ名', 'グループ説明', '作成日', 'メンバー数', 
        '平均学習時間', '平均完了率', 'S級人数', 'A級人数', 
        'B級人数', 'C級人数', 'D級人数'
    ])
    
    # データ行
    groups = Group.objects.all().order_by('name')
    
    for group in groups:
        students = group.customuser_set.filter(user_type='student')
        student_stats = UserStats.objects.filter(user__in=students)
        
        if students.exists():
            avg_hours = student_stats.aggregate(avg=Avg('total_study_hours'))['avg'] or 0
            avg_completion = student_stats.aggregate(avg=Avg('completion_rate'))['avg'] or 0
            
            grade_counts = {
                'S': student_stats.filter(current_grade='S').count(),
                'A': student_stats.filter(current_grade='A').count(),
                'B': student_stats.filter(current_grade='B').count(),
                'C': student_stats.filter(current_grade='C').count(),
                'D': student_stats.filter(current_grade='D').count(),
            }
        else:
            avg_hours = avg_completion = 0
            grade_counts = {'S': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0}
        
        writer.writerow([
            group.name,
            group.description,
            group.created_at.strftime('%Y-%m-%d'),
            students.count(),
            round(avg_hours, 1),
            round(avg_completion, 1),
            grade_counts['S'],
            grade_counts['A'],
            grade_counts['B'],
            grade_counts['C'],
            grade_counts['D'],
        ])
    
    return response


@permission_required('view_analytics')
def export_analytics_csv(request):
    """分析データをCSVでエクスポート"""
    chart_type = request.GET.get('type', 'daily_hours')
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="analytics_{chart_type}_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    # BOM付きUTF-8でExcel対応
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    if chart_type == 'daily_hours':
        writer.writerow(['日付', '学習時間'])
        
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        for i in range(31):
            current_date = start_date + timedelta(days=i)
            day_hours = DailyProgress.objects.filter(
                date=current_date
            ).aggregate(total=Sum('study_hours'))['total'] or 0
            
            writer.writerow([
                current_date.strftime('%Y-%m-%d'),
                day_hours
            ])
    
    elif chart_type == 'phase_progress':
        writer.writerow(['Phase', '人数'])
        
        phases = Phase.objects.all().order_by('phase_number')
        for phase in phases:
            count = UserStats.objects.filter(current_phase=phase).count()
            writer.writerow([f"Phase {phase.phase_number}", count])
    
    elif chart_type == 'grade_distribution':
        writer.writerow(['階級', '人数'])
        
        grades = ['S', 'A', 'B', 'C', 'D']
        for grade in grades:
            count = UserStats.objects.filter(current_grade=grade).count()
            writer.writerow([f"{grade}級", count])
    
    return response


@permission_required('view_analytics')
def export_menu(request):
    """エクスポートメニュー"""
    return render(request, 'progress/export_menu.html')


@permission_required('manage_students')
def user_detail(request, user_id):
    """ユーザー詳細・傾向画面"""
    target_user = get_object_or_404(CustomUser, id=user_id, user_type='student')
    
    # 基本統計
    try:
        user_stats = target_user.stats
    except:
        user_stats = None
    
    # 進捗履歴（最新30件）
    recent_progress = DailyProgress.objects.filter(user=target_user).order_by('-date')[:30]
    
    # 学習時間の推移（過去30日）
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=29)
    
    daily_hours = []
    dates = []
    for i in range(30):
        current_date = start_date + timedelta(days=i)
        dates.append(current_date.strftime('%m/%d'))
        
        day_progress = DailyProgress.objects.filter(user=target_user, date=current_date).first()
        daily_hours.append(float(day_progress.study_hours) if day_progress else 0)
    
    # Phase別進捗状況
    phase_progress = []
    phases = Phase.objects.all().order_by('phase_number')
    for phase in phases:
        progress_count = DailyProgress.objects.filter(user=target_user, current_phase=phase).count()
        phase_progress.append({
            'phase': phase,
            'count': progress_count,
            'is_current': user_stats and user_stats.current_phase == phase
        })
    
    # 週間統計（過去12週）
    weekly_stats = []
    for week in range(12):
        week_start = end_date - timedelta(weeks=week+1)
        week_end = week_start + timedelta(days=6)
        
        week_progress = DailyProgress.objects.filter(
            user=target_user,
            date__range=[week_start, week_end]
        )
        
        week_hours = week_progress.aggregate(total=Sum('study_hours'))['total'] or 0
        week_days = week_progress.count()
        avg_hours = week_hours / week_days if week_days > 0 else 0
        
        weekly_stats.append({
            'week_start': week_start,
            'week_end': week_end,
            'total_hours': week_hours,
            'study_days': week_days,
            'avg_hours': avg_hours
        })
    
    weekly_stats.reverse()  # 古い順に並び替え
    
    # フィードバック履歴
    feedback_requests = DailyProgress.objects.filter(
        user=target_user, 
        feedback_requested=True
    ).order_by('-date')[:10]
    
    # 学習傾向分析
    total_days = DailyProgress.objects.filter(user=target_user).count()
    if total_days > 0:
        avg_daily_hours = DailyProgress.objects.filter(user=target_user).aggregate(
            avg=Avg('study_hours'))['avg'] or 0
        
        # 曜日別学習傾向
        weekday_stats = {}
        for i in range(7):  # 0=月曜, 6=日曜
            weekday_progress = DailyProgress.objects.filter(
                user=target_user,
                date__week_day=(i+2) % 7 + 1  # Djangoの週始まり調整
            )
            weekday_hours = weekday_progress.aggregate(avg=Avg('study_hours'))['avg'] or 0
            weekday_stats[i] = {
                'name': ['月', '火', '水', '木', '金', '土', '日'][i],
                'avg_hours': weekday_hours,
                'study_days': weekday_progress.count()
            }
    else:
        avg_daily_hours = 0
        weekday_stats = {}
    
    # 進捗遅れ状況の計算
    progress_status = None
    if user_stats:
        progress_status = user_stats.calculate_progress_status()
    
    # 項目別学習期間分析
    item_duration_analysis = []
    
    # ユーザーの全進捗記録を項目別に分析
    user_records = DailyProgress.objects.filter(
        user=target_user
    ).select_related('current_phase', 'current_item').order_by('date')
    
    if user_records.exists():
        # 項目別の開始日・終了日を記録
        item_periods = {}
        
        for record in user_records:
            item_key = (record.current_phase.id, record.current_item.id)
            item_info = {
                'phase': record.current_phase,
                'item': record.current_item,
                'phase_name': record.current_phase.name,
                'item_code': record.current_item.item_code,
                'item_name': record.current_item.name,
                'estimated_days': record.current_item.estimated_days or 1
            }
            
            if item_key not in item_periods:
                item_periods[item_key] = {
                    **item_info,
                    'start_date': record.date,
                    'end_date': record.date,
                    'total_hours': record.study_hours,
                    'study_days': 1,
                    'feedback_requests': 1 if record.feedback_requested else 0
                }
            else:
                item_periods[item_key]['end_date'] = record.date
                item_periods[item_key]['total_hours'] += record.study_hours
                item_periods[item_key]['study_days'] += 1
                if record.feedback_requested:
                    item_periods[item_key]['feedback_requests'] += 1
        
        # 分析結果を整理
        for item_key, period_data in item_periods.items():
            duration_days = (period_data['end_date'] - period_data['start_date']).days + 1
            estimated_days = period_data['estimated_days']
            
            # 効率指標の計算
            efficiency_ratio = round(estimated_days / duration_days, 2) if duration_days > 0 else 0
            avg_hours_per_day = round(period_data['total_hours'] / period_data['study_days'], 1) if period_data['study_days'] > 0 else 0
            
            # 進捗状況の判定
            if duration_days <= estimated_days * 0.8:
                status = 'excellent'  # 予定より早い
                status_label = '優秀'
                status_class = 'bg-green-100 text-green-800'
            elif duration_days <= estimated_days:
                status = 'good'  # 予定通り
                status_label = '良好'
                status_class = 'bg-blue-100 text-blue-800'
            elif duration_days <= estimated_days * 1.5:
                status = 'average'  # やや遅れ
                status_label = '標準'
                status_class = 'bg-yellow-100 text-yellow-800'
            else:
                status = 'slow'  # 大幅遅れ
                status_label = '要改善'
                status_class = 'bg-red-100 text-red-800'
            
            delay_days = duration_days - estimated_days
            abs_delay_days = abs(delay_days)
            
            item_duration_analysis.append({
                'phase': period_data['phase'],
                'item': period_data['item'],
                'phase_name': period_data['phase_name'],
                'item_code': period_data['item_code'],
                'item_name': period_data['item_name'],
                'start_date': period_data['start_date'],
                'end_date': period_data['end_date'],
                'duration_days': duration_days,
                'estimated_days': estimated_days,
                'total_hours': period_data['total_hours'],
                'study_days': period_data['study_days'],
                'avg_hours_per_day': avg_hours_per_day,
                'feedback_requests': period_data['feedback_requests'],
                'efficiency_ratio': efficiency_ratio,
                'status': status,
                'status_label': status_label,
                'status_class': status_class,
                'delay_days': delay_days,
                'abs_delay_days': abs_delay_days
            })
    
    # Phase順、項目順でソート
    item_duration_analysis.sort(key=lambda x: (x['phase'].phase_number, x['item'].order))
    
    # 統計サマリーを計算
    analysis_summary = {}
    if item_duration_analysis:
        excellent_good_count = len([a for a in item_duration_analysis if a['status'] in ['excellent', 'good']])
        fb_request_count = len([a for a in item_duration_analysis if a['feedback_requests'] > 0])
        total_hours = sum(a['total_hours'] for a in item_duration_analysis)
        avg_efficiency = sum(a['efficiency_ratio'] for a in item_duration_analysis) / len(item_duration_analysis)
        
        analysis_summary = {
            'total_items': len(item_duration_analysis),
            'excellent_good_count': excellent_good_count,
            'fb_request_count': fb_request_count,
            'total_hours': round(total_hours, 1),
            'avg_efficiency': round(avg_efficiency, 2)
        }

    context = {
        'target_user': target_user,
        'user_stats': user_stats,
        'progress_status': progress_status,
        'recent_progress': recent_progress,
        'daily_hours': daily_hours,
        'dates': dates,
        'phase_progress': phase_progress,
        'weekly_stats': weekly_stats,
        'feedback_requests': feedback_requests,
        'total_study_days': total_days,
        'avg_daily_hours': avg_daily_hours,
        'weekday_stats': weekday_stats,
        'item_duration_analysis': item_duration_analysis,
        'analysis_summary': analysis_summary,
    }
    
    return render(request, 'progress/user_detail.html', context)


@permission_required('view_analytics')
def users_by_grade(request, grade):
    """階級別ユーザー一覧"""
    if grade not in ['S', 'A', 'B', 'C', 'D']:
        messages.error(request, '無効な階級です。')
        return redirect('training_admin_dashboard')
    
    # 該当階級のユーザーを取得
    users_stats = UserStats.objects.filter(
        current_grade=grade,
        user__user_type='student'
    ).select_related('user', 'user__group', 'current_phase', 'current_item').order_by('-completion_rate')
    
    # 各ユーザーの進捗状況を計算
    for user_stat in users_stats:
        user_stat.progress_status = user_stat.calculate_progress_status()
    
    # 階級名の取得
    grade_display = dict(DailyProgress.GRADE_CHOICES).get(grade, grade)
    
    # 階級統計
    total_users = users_stats.count()
    if total_users > 0:
        avg_completion = users_stats.aggregate(avg=Avg('completion_rate'))['avg'] or 0
        avg_hours = users_stats.aggregate(avg=Avg('total_study_hours'))['avg'] or 0
        avg_days = users_stats.aggregate(avg=Avg('days_elapsed'))['avg'] or 0
    else:
        avg_completion = avg_hours = avg_days = 0
    
    # グループ別分布
    group_distribution = {}
    for stats in users_stats:
        group_name = stats.user.group.name if stats.user.group else '未所属'
        if group_name not in group_distribution:
            group_distribution[group_name] = 0
        group_distribution[group_name] += 1
    
    context = {
        'grade': grade,
        'grade_display': grade_display,
        'users_stats': users_stats,
        'total_users': total_users,
        'avg_completion': avg_completion,
        'avg_hours': avg_hours,
        'avg_days': avg_days,
        'group_distribution': group_distribution,
    }
    
    return render(request, 'progress/users_by_grade.html', context)


@login_required
def get_phase_items(request):
    """Phase IDに基づいてカリキュラム項目を取得するAPI（進捗バリデーション付き）"""
    phase_id = request.GET.get('phase_id')
    if not phase_id:
        return JsonResponse({'error': 'Phase ID is required'}, status=400)
    
    try:
        # 基本的な項目リスト
        items = CurriculumItem.objects.filter(phase_id=phase_id).order_by('order')
        
        # 研修生の場合は進捗状況をチェック
        if request.user.user_type == 'student':
            progress_status = request.user.get_current_progress_status()
            if progress_status:
                available_phase_ids = list(progress_status['available_phases'].values_list('id', flat=True))
                
                # 選択されたフェーズが利用可能かチェック
                if int(phase_id) not in available_phase_ids:
                    return JsonResponse({'error': 'このフェーズは選択できません'}, status=403)
        
        items_data = [
            {
                'id': item.id,
                'code': item.item_code,
                'name': item.name,
                'display': f"{item.item_code}: {item.name}",
                'estimated_days': item.estimated_days,
                'order': item.order
            }
            for item in items
        ]
        return JsonResponse({'items': items_data})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def progress_detail(request, progress_id):
    """進捗記録詳細表示"""
    progress = get_object_or_404(DailyProgress, id=progress_id)
    
    # 権限チェック: 研修生は自分の記録のみ、管理者は全ての記録
    if request.user.user_type == 'student' and progress.user != request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': '権限がありません'}, status=403)
        messages.error(request, '他の研修生の進捗記録は閲覧できません。')
        return redirect('progress_list')
    
    # 研修管理者以上の権限チェック（研修生以外のアクセス時）
    if request.user.user_type != 'student' and not (request.user.can_view_analytics or request.user.is_system_admin):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': '権限がありません'}, status=403)
        messages.error(request, '進捗記録を閲覧する権限がありません。')
        return redirect('training_admin_dashboard')
    
    # 進捗遅れ計算
    if progress.user.start_date:
        expected_day = (progress.date - progress.user.start_date).days + 1
        
        # 現在の項目までの標準日数を計算
        items_before = CurriculumItem.objects.filter(
            phase__phase_number__lt=progress.current_phase.phase_number
        ).aggregate(total_days=Sum('estimated_days'))['total_days'] or 0
        
        items_in_phase = CurriculumItem.objects.filter(
            phase=progress.current_phase,
            order__lte=progress.current_item.order
        ).aggregate(total_days=Sum('estimated_days'))['total_days'] or 0
        
        expected_completion_day = items_before + items_in_phase
        progress_status = {
            'expected_day': expected_day,
            'expected_completion_day': expected_completion_day,
            'delay_days': max(0, expected_day - expected_completion_day),
            'is_ahead': expected_day < expected_completion_day,
            'is_on_track': abs(expected_day - expected_completion_day) <= 2,
            'is_behind': expected_day > expected_completion_day + 2
        }
    else:
        progress_status = None
    
    # 同じユーザーの前後の記録
    prev_progress = DailyProgress.objects.filter(
        user=progress.user, 
        date__lt=progress.date
    ).order_by('-date').first()
    
    next_progress = DailyProgress.objects.filter(
        user=progress.user, 
        date__gt=progress.date
    ).order_by('date').first()
    
    context = {
        'progress': progress,
        'progress_status': progress_status,
        'prev_progress': prev_progress,
        'next_progress': next_progress,
    }
    
    # Ajaxリクエストの場合は専用テンプレートを使用
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'progress/progress_detail_modal.html', context)
    
    return render(request, 'progress/progress_detail.html', context)


@permission_required('view_analytics')
def feedback_requests_list(request):
    """フィードバック要請一覧"""
    feedback_requests = DailyProgress.objects.filter(
        feedback_requested=True
    ).select_related(
        'user', 'user__group', 'current_phase', 'current_item'
    ).order_by('-date')
    
    # フィルター処理
    user_filter = request.GET.get('user')
    phase_filter = request.GET.get('phase')
    status_filter = request.GET.get('status', 'all')
    
    if user_filter:
        feedback_requests = feedback_requests.filter(user__username__icontains=user_filter)
    
    if phase_filter:
        feedback_requests = feedback_requests.filter(current_phase__phase_number=phase_filter)
    
    # ステータスフィルター
    if status_filter == 'pending':
        feedback_requests = feedback_requests.filter(feedback_provided=False)
    elif status_filter == 'completed':
        feedback_requests = feedback_requests.filter(feedback_provided=True)
    
    # 統計情報
    total_requests = feedback_requests.count()
    pending_requests = DailyProgress.objects.filter(feedback_requested=True, feedback_provided=False).count()
    completed_requests = DailyProgress.objects.filter(feedback_requested=True, feedback_provided=True).count()
    recent_requests = feedback_requests.filter(
        date__gte=timezone.now().date() - timedelta(days=7)
    ).count()
    
    # Phase別集計
    phase_stats = feedback_requests.values(
        'current_phase__phase_number', 'current_phase__name'
    ).annotate(count=Count('id')).order_by('current_phase__phase_number')
    
    # ユーザー別集計（上位10名）
    user_stats = feedback_requests.values(
        'user__username', 'user__last_name', 'user__first_name'
    ).annotate(count=Count('id')).order_by('-count')[:10]
    
    context = {
        'feedback_requests': feedback_requests,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'completed_requests': completed_requests,
        'recent_requests': recent_requests,
        'phase_stats': phase_stats,
        'user_stats': user_stats,
        'phases': Phase.objects.all(),
        'current_filters': {
            'user': user_filter,
            'phase': phase_filter,
            'status': status_filter,
        }
    }
    
    return render(request, 'progress/feedback_requests_list.html', context)


@login_required  
def feedback_detail(request, progress_id):
    """フィードバック要請詳細表示・フィードバック提供"""
    progress = get_object_or_404(DailyProgress, id=progress_id, feedback_requested=True)
    
    # 権限チェック: 研修生は自分の記録のみ、管理者は全ての記録
    if request.user.user_type == 'student' and progress.user != request.user:
        messages.error(request, '他の研修生のフィードバック要請は閲覧できません。')
        return redirect('progress_list')
    
    # 研修管理者以上の権限チェック（研修生以外のアクセス時）
    if request.user.user_type != 'student' and not (request.user.can_view_analytics or request.user.is_system_admin):
        messages.error(request, 'フィードバック要請を閲覧する権限がありません。')
        return redirect('training_admin_dashboard')
    
    # フィードバック提供処理（管理者のみ）
    if request.method == 'POST' and request.user.user_type in ['training_admin', 'system_admin']:
        feedback_response = request.POST.get('feedback_response', '').strip()
        
        if feedback_response:
            from django.utils import timezone
            
            progress.feedback_provided = True
            progress.feedback_admin = request.user
            progress.feedback_response = feedback_response
            progress.feedback_provided_at = timezone.now()
            progress.save()
            
            messages.success(request, f'{progress.user.username}さんにフィードバックを提供しました。')
            return redirect('feedback_requests_list')
        else:
            messages.error(request, 'フィードバック内容を入力してください。')
    
    # 同じユーザーの他のフィードバック要請（前後5件）
    other_requests = DailyProgress.objects.filter(
        user=progress.user,
        feedback_requested=True
    ).exclude(id=progress.id).order_by('-date')[:5]
    
    # 進捗遅れ計算
    if progress.user.start_date:
        expected_day = (progress.date - progress.user.start_date).days + 1
        
        # 現在の項目までの標準日数を計算
        items_before = CurriculumItem.objects.filter(
            phase__phase_number__lt=progress.current_phase.phase_number
        ).aggregate(total_days=Sum('estimated_days'))['total_days'] or 0
        
        items_in_phase = CurriculumItem.objects.filter(
            phase=progress.current_phase,
            order__lte=progress.current_item.order
        ).aggregate(total_days=Sum('estimated_days'))['total_days'] or 0
        
        expected_completion_day = items_before + items_in_phase
        progress_status = {
            'expected_day': expected_day,
            'expected_completion_day': expected_completion_day,
            'delay_days': max(0, expected_day - expected_completion_day),
            'is_ahead': expected_day < expected_completion_day,
            'is_on_track': abs(expected_day - expected_completion_day) <= 2,
            'is_behind': expected_day > expected_completion_day + 2
        }
    else:
        progress_status = None
    
    context = {
        'progress': progress,
        'progress_status': progress_status,
        'other_requests': other_requests,
        'can_provide_feedback': request.user.user_type in ['training_admin', 'system_admin'] and not progress.feedback_provided,
    }
    
    return render(request, 'progress/feedback_detail.html', context)


@permission_required('view_analytics')
def feedback_analytics(request):
    """フィードバック要請分析ページ"""
    from django.db.models import Count, Avg
    from collections import defaultdict
    
    # フィードバック要請があった記録を取得
    feedback_records = DailyProgress.objects.filter(
        feedback_requested=True
    ).select_related('current_phase', 'current_item', 'user')
    
    # 1. 項目別フィードバック要請数とその内容
    item_feedback_stats = {}
    problem_by_item = defaultdict(list)
    
    for record in feedback_records:
        item_key = f"{record.current_phase.name} - {record.current_item.item_code}: {record.current_item.name}"
        
        if item_key not in item_feedback_stats:
            item_feedback_stats[item_key] = {
                'item': record.current_item,
                'phase': record.current_phase,
                'count': 0,
                'users': set(),
                'problems': []
            }
        
        item_feedback_stats[item_key]['count'] += 1
        item_feedback_stats[item_key]['users'].add(record.user.username)
        
        if record.problem_detail:
            item_feedback_stats[item_key]['problems'].append({
                'user': record.user.username,
                'date': record.date,
                'problem': record.problem_detail,
                'tried_solutions': record.tried_solutions,
                'study_hours': record.study_hours
            })
    
    # カウント順でソート
    sorted_items = sorted(
        item_feedback_stats.items(), 
        key=lambda x: x[1]['count'], 
        reverse=True
    )
    
    # 2. 各項目の平均所要時間を計算
    item_duration_stats = {}
    
    # 全項目を取得
    all_items = CurriculumItem.objects.select_related('phase').order_by('phase__phase_number', 'order')
    
    for item in all_items:
        # この項目に取り組んだ全ユーザーの進捗記録を取得
        item_records = DailyProgress.objects.filter(
            current_item=item
        ).select_related('user').order_by('user', 'date')
        
        user_durations = {}
        current_user_start = {}
        
        for record in item_records:
            user = record.user
            
            # ユーザーがこの項目を初めて学習した日
            if user not in current_user_start:
                current_user_start[user] = record.date
            
            # ユーザーがこの項目を最後に学習した日
            user_durations[user] = (record.date - current_user_start[user]).days + 1
        
        # 平均所要日数を計算
        if user_durations:
            avg_duration = sum(user_durations.values()) / len(user_durations)
            total_users = len(user_durations)
            
            # フィードバック要請数
            feedback_count = DailyProgress.objects.filter(
                current_item=item,
                feedback_requested=True
            ).count()
            
            estimated_days = item.estimated_days or 1  # None の場合は1日として扱う
            item_duration_stats[item] = {
                'avg_duration': round(avg_duration, 1),
                'total_users': total_users,
                'feedback_count': feedback_count,
                'feedback_rate': round((feedback_count / total_users * 100), 1) if total_users > 0 else 0,
                'estimated_days': estimated_days,
                'efficiency_ratio': round((estimated_days / avg_duration), 2) if avg_duration > 0 else 0
            }
    
    # 3. Phase別統計
    phase_stats = {}
    for phase in Phase.objects.all():
        phase_feedback_count = DailyProgress.objects.filter(
            current_phase=phase,
            feedback_requested=True
        ).count()
        
        phase_total_records = DailyProgress.objects.filter(
            current_phase=phase
        ).count()
        
        phase_stats[phase] = {
            'feedback_count': phase_feedback_count,
            'total_records': phase_total_records,
            'feedback_rate': round((phase_feedback_count / phase_total_records * 100), 1) if phase_total_records > 0 else 0
        }
    
    # 4. 最近のトレンド分析（過去30日）
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    recent_feedback = DailyProgress.objects.filter(
        feedback_requested=True,
        date__gte=start_date,
        date__lte=end_date
    ).select_related('current_item', 'current_phase')
    
    daily_feedback_count = {}
    for i in range(31):
        current_date = start_date + timedelta(days=i)
        count = recent_feedback.filter(date=current_date).count()
        daily_feedback_count[current_date.strftime('%m/%d')] = count
    
    context = {
        'sorted_items': sorted_items[:20],  # トップ20項目
        'item_duration_stats': item_duration_stats,
        'phase_stats': phase_stats,
        'daily_feedback_count': daily_feedback_count,
        'total_feedback_requests': feedback_records.count(),
        'unique_users_requesting': len(set(r.user for r in feedback_records)),
        'avg_requests_per_user': round(feedback_records.count() / len(set(r.user for r in feedback_records)), 1) if feedback_records else 0,
    }
    
    return render(request, 'progress/feedback_analytics.html', context)


@permission_required('view_analytics')
def group_detail(request, group_id):
    """グループ詳細画面"""
    from datetime import date, timedelta
    
    try:
        group = Group.objects.get(pk=group_id)
    except Group.DoesNotExist:
        return redirect('group_ranking')
    
    # グループの学生を取得
    students = CustomUser.objects.filter(
        group=group, 
        user_type='student'
    ).select_related('stats').prefetch_related('daily_progress')
    
    # 統計計算
    student_stats = []
    group_completion_rates = []
    total_hours = 0
    total_reports = 0
    expected_reports = 0
    
    # 日報提出度計算用の期間設定（過去30日）
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    expected_days = (end_date - start_date).days + 1
    
    for student in students:
        if hasattr(student, 'stats') and student.stats:
            stats = student.stats
            completion_rate = float(stats.completion_rate)
            study_hours = float(stats.total_study_hours)
            efficiency_score = float(stats.efficiency_score)
            
            # 日報提出度計算
            submitted_days = DailyProgress.objects.filter(
                user=student,
                date__gte=start_date,
                date__lte=end_date
            ).count()
            
            if student.start_date:
                student_start = max(student.start_date, start_date)
                if student_start <= end_date:
                    expected_student_days = (end_date - student_start).days + 1
                    expected_reports += expected_student_days
                    total_reports += submitted_days
                    submission_rate = (submitted_days / expected_student_days * 100) if expected_student_days > 0 else 0
                else:
                    submission_rate = 0
            else:
                expected_reports += expected_days
                total_reports += submitted_days
                submission_rate = (submitted_days / expected_days * 100) if expected_days > 0 else 0
            
            # 一日平均学習時間を計算（経過日数で割る）
            if student.start_date:
                days_elapsed = (date.today() - student.start_date).days + 1
                daily_avg_hours = float(stats.total_study_hours) / days_elapsed if days_elapsed > 0 else 0
            else:
                daily_avg_hours = 0
            
            student_stats.append({
                'user': student,
                'completion_rate': completion_rate,
                'study_hours': study_hours,
                'daily_avg_hours': round(daily_avg_hours, 1),
                'efficiency_score': efficiency_score,
                'grade': stats.current_grade,
                'submission_rate': round(submission_rate, 1),
                'submitted_days': submitted_days,
                'days_elapsed': stats.days_elapsed,
            })
            
            group_completion_rates.append(completion_rate)
            total_hours += study_hours
        else:
            student_stats.append({
                'user': student,
                'completion_rate': 0,
                'study_hours': 0,
                'daily_avg_hours': 0,
                'efficiency_score': 0,
                'grade': 'D',
                'submission_rate': 0,
                'submitted_days': 0,
                'days_elapsed': 0,
            })
            group_completion_rates.append(0)
    
    # グループ統計
    avg_completion = sum(group_completion_rates) / len(group_completion_rates) if group_completion_rates else 0
    
    # グループ内メンバーの一日平均学習時間を計算
    daily_hours_list = []
    for student in students:
        if hasattr(student, 'stats') and student.stats:
            stats = student.stats
            # 経過日数で計算
            if student.start_date:
                days_elapsed = (date.today() - student.start_date).days + 1
                if days_elapsed > 0:
                    daily_avg = float(stats.total_study_hours) / days_elapsed
                    daily_hours_list.append(daily_avg)
                else:
                    daily_hours_list.append(0)
            else:
                daily_hours_list.append(0)
        else:
            daily_hours_list.append(0)
    
    # グループ内メンバーの一日平均学習時間の平均を計算
    avg_daily_hours = sum(daily_hours_list) / len(daily_hours_list) if daily_hours_list else 0
    group_submission_rate = (total_reports / expected_reports * 100) if expected_reports > 0 else 0
    
    # 階級分布
    grade_distribution = {'S': 0, 'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for stat in student_stats:
        grade_distribution[stat['grade']] += 1
    
    # ソート
    sort_by = request.GET.get('sort', 'completion')
    if sort_by == 'reports':
        student_stats.sort(key=lambda x: x['submission_rate'], reverse=True)
    elif sort_by == 'hours':
        student_stats.sort(key=lambda x: x['study_hours'], reverse=True)
    elif sort_by == 'efficiency':
        student_stats.sort(key=lambda x: x['efficiency_score'], reverse=True)
    else:  # completion
        student_stats.sort(key=lambda x: x['completion_rate'], reverse=True)
    
    context = {
        'group': group,
        'student_stats': student_stats,
        'student_count': len(students),
        'avg_completion': round(avg_completion, 1),
        'avg_hours': round(avg_daily_hours, 1),  # Keep for compatibility but now daily hours
        'avg_daily_hours': round(avg_daily_hours, 1),
        'group_submission_rate': round(group_submission_rate, 1),
        'grade_distribution': grade_distribution,
        'current_sort': sort_by,
        'period_days': expected_days,
    }
    
    return render(request, 'progress/group_detail.html', context)


def calculate_weekly_ranking():
    """週間ランキングを計算して保存する関数"""
    from datetime import date, timedelta
    
    # 今週の月曜日と日曜日を計算
    today = date.today()
    # 今週の月曜日を計算（weekday()は月曜日=0）
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)
    
    # 全研修生を取得
    students = CustomUser.objects.filter(user_type='student')
    
    ranking_data = []
    
    for student in students:
        # 今週完了した項目を取得
        completed_items = DailyProgress.objects.filter(
            user=student,
            date__gte=week_start,
            date__lte=week_end,
            item_completed=True
        ).select_related('current_item')
        
        # 完了項目の標準日数合計を計算
        total_standard_days = 0
        efficiency_scores = []
        
        for progress in completed_items:
            item = progress.current_item
            if item.estimated_days:
                total_standard_days += item.estimated_days
                
                # 効率計算：その項目にかかった実際の日数を計算
                item_start_date = DailyProgress.objects.filter(
                    user=student,
                    current_item=item,
                    date__lte=progress.date
                ).order_by('date').first()
                
                if item_start_date:
                    actual_days = (progress.date - item_start_date.date).days + 1
                    efficiency = item.estimated_days / actual_days if actual_days > 0 else 0
                    efficiency_scores.append(efficiency)
        
        # 平均効率を計算
        avg_efficiency = sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0
        
        # 今週の総学習時間を計算
        week_hours = DailyProgress.objects.filter(
            user=student,
            date__gte=week_start,
            date__lte=week_end
        ).aggregate(total=Sum('study_hours'))['total'] or 0
        
        ranking_data.append({
            'user': student,
            'total_standard_days': total_standard_days,
            'avg_efficiency': avg_efficiency,
            'total_study_hours': week_hours,
        })
    
    # ランキング計算（標準日数→効率→学習時間の順で並び替え）
    ranking_data.sort(key=lambda x: (
        -x['total_standard_days'],  # 標準日数：多い順
        -x['avg_efficiency'],       # 効率：高い順
        -x['total_study_hours']     # 学習時間：多い順
    ))
    
    # 上位3位のみ保存
    for rank, data in enumerate(ranking_data[:3], 1):
        WeeklyRanking.objects.update_or_create(
            user=data['user'],
            week_start=week_start,
            defaults={
                'week_end': week_end,
                'rank': rank,
                'completed_standard_days': data['total_standard_days'],
                'efficiency_score': round(data['avg_efficiency'], 2),
                'total_study_hours': data['total_study_hours'],
            }
        )
    
    return ranking_data[:3]


def get_user_weekly_rankings(user):
    """指定ユーザーの週間ランキングを取得する関数"""
    from datetime import date, timedelta
    
    current_rankings = []
    for week_offset in range(4):  # 過去4週間
        target_monday = date.today() - timedelta(days=date.today().weekday() + (week_offset * 7))
        
        user_ranking = WeeklyRanking.objects.filter(
            user=user,
            week_start=target_monday
        ).first()
        
        if user_ranking:
            current_rankings.append(user_ranking)
    
    return current_rankings
