from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count, Q
from django.http import JsonResponse
from datetime import datetime, date, timedelta
from ..models import CustomUser, Phase, CurriculumItem, DailyProgress, UserStats
from ..decorators import permission_required


@permission_required('view_analytics')
def feedback_analytics_view(request):
    """フィードバック分析ページ"""
    # 基本統計
    total_feedback_requests = DailyProgress.objects.filter(feedback_requested=True).count()
    pending_feedback = DailyProgress.objects.filter(
        feedback_requested=True, feedback_provided=False
    ).count()
    completed_feedback = DailyProgress.objects.filter(
        feedback_requested=True, feedback_provided=True
    ).count()
    
    # 要請した研修生数
    unique_users_requesting = DailyProgress.objects.filter(
        feedback_requested=True
    ).values('user').distinct().count()
    
    # 一人当たり平均要請数
    avg_requests_per_user = round(total_feedback_requests / max(unique_users_requesting, 1), 1)
    
    # 項目別フィードバック要請統計（詳細版）
    from collections import defaultdict
    item_stats = defaultdict(lambda: {
        'count': 0,
        'users': set(),
        'problems': [],
        'phase': None
    })
    
    feedback_requests = DailyProgress.objects.filter(feedback_requested=True).select_related(
        'user', 'current_item', 'current_phase'
    ).order_by('-date')
    
    for req in feedback_requests:
        if req.current_item:
            item_key = f"{req.current_item.item_code}: {req.current_item.name}"
            item_stats[item_key]['count'] += 1
            item_stats[item_key]['users'].add(req.user.username)
            item_stats[item_key]['phase'] = req.current_phase
            
            # 問題詳細があれば追加
            if req.problem_detail and req.problem_detail.strip():
                item_stats[item_key]['problems'].append({
                    'user': req.user.username,
                    'date': req.date,
                    'problem': req.problem_detail,
                    'tried_solutions': req.tried_solutions or '',
                    'study_hours': req.study_hours
                })
            else:
                # 問題詳細がない場合はstuck_contentを使用
                problem_text = req.stuck_content or 'フィードバック要請（詳細記載なし）'
                item_stats[item_key]['problems'].append({
                    'user': req.user.username,
                    'date': req.date,
                    'problem': problem_text,
                    'tried_solutions': req.tried_solutions or '',
                    'study_hours': req.study_hours
                })
    
    # ソート済みアイテム（要請数順）
    sorted_items = sorted(item_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:20]
    
    # 項目別平均所要時間分析
    from ..models import CurriculumItem
    item_duration_stats = {}
    
    for item in CurriculumItem.objects.all():
        # この項目で進捗記録があるユーザーの開始・終了日を計算
        user_durations = []
        feedback_count = 0
        
        # 各ユーザーについて、この項目での最初と最後の記録を取得
        users_with_progress = DailyProgress.objects.filter(
            current_item=item
        ).values('user').distinct()
        
        for user_data in users_with_progress:
            user_records = DailyProgress.objects.filter(
                user_id=user_data['user'],
                current_item=item
            ).order_by('date')
            
            if user_records.exists():
                start_date = user_records.first().date
                end_date = user_records.last().date
                duration = (end_date - start_date).days + 1
                user_durations.append(duration)
                
                # このユーザーのこの項目でのフィードバック要請数
                feedback_count += user_records.filter(feedback_requested=True).count()
        
        if user_durations:
            avg_duration = round(sum(user_durations) / len(user_durations), 1)
            estimated_days = item.estimated_days or 1
            efficiency_ratio = round(estimated_days / avg_duration, 2) if avg_duration > 0 else 0
            feedback_rate = round((feedback_count / len(user_durations)) * 100, 1)
            
            item_duration_stats[item] = {
                'avg_duration': avg_duration,
                'estimated_days': estimated_days,
                'efficiency_ratio': efficiency_ratio,
                'total_users': len(user_durations),
                'feedback_count': feedback_count,
                'feedback_rate': feedback_rate
            }
    
    # Phase別統計
    from ..models import Phase
    phase_stats = {}
    
    for phase in Phase.objects.all():
        total_records = DailyProgress.objects.filter(current_phase=phase).count()
        feedback_count = DailyProgress.objects.filter(
            current_phase=phase, feedback_requested=True
        ).count()
        feedback_rate = round((feedback_count / max(total_records, 1)) * 100, 1)
        
        phase_stats[phase] = {
            'total_records': total_records,
            'feedback_count': feedback_count,
            'feedback_rate': feedback_rate
        }
    
    # 月別フィードバック要請推移
    monthly_stats = []
    for i in range(6):  # 過去6ヶ月
        target_month = date.today().replace(day=1) - timedelta(days=i*30)
        month_start = target_month.replace(day=1)
        next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
        
        month_requests = DailyProgress.objects.filter(
            feedback_requested=True,
            date__gte=month_start,
            date__lt=next_month
        ).count()
        
        monthly_stats.append({
            'month': month_start.strftime('%Y年%m月'),
            'requests': month_requests
        })
    
    monthly_stats.reverse()  # 古い順に並び替え
    
    context = {
        'total_feedback_requests': total_feedback_requests,
        'pending_feedback': pending_feedback,
        'completed_feedback': completed_feedback,
        'unique_users_requesting': unique_users_requesting,
        'avg_requests_per_user': avg_requests_per_user,
        'sorted_items': sorted_items,
        'item_duration_stats': item_duration_stats,
        'phase_stats': phase_stats,
        'monthly_stats': monthly_stats,
    }
    
    return render(request, 'progress/analytics/feedback_analytics.html', context)


@permission_required('view_analytics')
def feedback_detail_view(request, progress_id):
    """フィードバック詳細表示"""
    progress = get_object_or_404(DailyProgress, id=progress_id)
    
    context = {
        'progress': progress,
    }
    
    return render(request, 'progress/analytics/feedback_detail.html', context)


@permission_required('view_analytics')
def feedback_requests_list_view(request):
    """フィードバック要請一覧"""
    # フィルター
    status_filter = request.GET.get('status', 'all')
    item_filter = request.GET.get('item')
    user_filter = request.GET.get('user')
    
    queryset = DailyProgress.objects.filter(feedback_requested=True)
    
    if status_filter == 'pending':
        queryset = queryset.filter(feedback_provided=False)
    elif status_filter == 'completed':
        queryset = queryset.filter(feedback_provided=True)
    
    if item_filter:
        queryset = queryset.filter(current_item__item_code__icontains=item_filter)
    
    if user_filter:
        queryset = queryset.filter(user__username__icontains=user_filter)
    
    feedback_requests = queryset.select_related(
        'user', 'current_phase', 'current_item', 'feedback_admin'
    ).order_by('-date')
    
    # 統計情報
    total_requests = queryset.count()
    pending_count = queryset.filter(feedback_provided=False).count()
    completed_count = queryset.filter(feedback_provided=True).count()
    
    # ユニークな項目リスト（フィルター用）
    unique_items = DailyProgress.objects.filter(
        feedback_requested=True
    ).values_list('current_item__item_code', flat=True).distinct()
    
    # 今週のフィードバック要請数
    from datetime import datetime
    week_start = date.today() - timedelta(days=date.today().weekday())
    recent_requests = DailyProgress.objects.filter(
        feedback_requested=True,
        date__gte=week_start
    ).count()
    
    # Phase別統計
    phase_stats = DailyProgress.objects.filter(
        feedback_requested=True
    ).values('current_phase__phase_number').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # ユーザー別統計
    user_stats = DailyProgress.objects.filter(
        feedback_requested=True
    ).values('user__username').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # 全Phase取得
    from ..models import Phase
    phases = Phase.objects.all().order_by('phase_number')
    
    context = {
        'feedback_requests': feedback_requests,
        'total_requests': total_requests,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'unique_items': sorted(unique_items),
        'recent_requests': recent_requests,
        'phase_stats': phase_stats,
        'user_stats': user_stats,
        'phases': phases,
        'current_filters': {
            'status': status_filter,
            'item': item_filter,
            'user': user_filter,
        }
    }
    
    return render(request, 'progress/analytics/feedback_requests_list.html', context)