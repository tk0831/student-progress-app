from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Avg, Count, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from datetime import datetime, date, timedelta
import calendar
from ..models import CustomUser, Group, Phase, CurriculumItem, DailyProgress, UserStats, WeeklyRanking
from ..forms import DailyProgressForm
from ..decorators import permission_required, student_required


def progress_form(request):
    """進捗記録フォーム（progress_create関数のエイリアス）"""
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
    
    return render(request, 'progress/progress/progress_form.html', {'form': form})


@login_required
def progress_list_view(request):
    """進捗一覧表示"""
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
    
    return render(request, 'progress/progress/progress_list.html', context)


def progress_detail_view(request, progress_id):
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
        return render(request, 'progress/progress/progress_detail_modal.html', context)
    
    return render(request, 'progress/progress/progress_detail.html', context)


def progress_delete_view(request, progress_id):
    """進捗記録削除"""
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
    return render(request, 'progress/progress/progress_delete.html', context)


# progress_detail_modalは progress_detail_view のAjax処理で実装
def progress_detail_modal(request, progress_id):
    """モーダル用の進捗詳細"""
    return progress_detail_view(request, progress_id)


def progress_analytics_view(request):
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
    
    return render(request, 'progress/progress/progress_analytics.html', context)


@login_required
def progress_calendar(request):
    """進捗カレンダー表示"""
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
    
    return render(request, 'progress/progress/progress_calendar.html', context)