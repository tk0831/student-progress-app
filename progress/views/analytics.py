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
    
    # 項目別フィードバック要請数
    item_feedback_stats = []
    items_with_feedback = DailyProgress.objects.filter(
        feedback_requested=True
    ).values(
        'current_item__item_code',
        'current_item__name',
        'current_item__estimated_days'
    ).annotate(
        request_count=Count('id'),
        avg_days=Avg('days_elapsed')
    ).order_by('-request_count')
    
    for item_stat in items_with_feedback:
        # 項目の標準日数
        estimated_days = item_stat['current_item__estimated_days'] or 1
        avg_days = item_stat['avg_days'] or 0
        
        # 効率比計算
        if avg_days > 0:
            efficiency_ratio = estimated_days / avg_days
        else:
            efficiency_ratio = 0
        
        # 主な問題内容を取得
        common_problems = DailyProgress.objects.filter(
            feedback_requested=True,
            current_item__item_code=item_stat['current_item__item_code'],
            problem_detail__isnull=False
        ).exclude(problem_detail='').values_list('problem_detail', flat=True)[:5]
        
        item_feedback_stats.append({
            'item_code': item_stat['current_item__item_code'],
            'item_name': item_stat['current_item__name'],
            'request_count': item_stat['request_count'],
            'estimated_days': estimated_days,
            'avg_actual_days': round(avg_days, 1),
            'efficiency_ratio': round(efficiency_ratio, 2),
            'common_problems': list(common_problems)
        })
    
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
        'item_feedback_stats': item_feedback_stats,
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
    
    context = {
        'feedback_requests': feedback_requests,
        'total_requests': total_requests,
        'pending_count': pending_count,
        'completed_count': completed_count,
        'unique_items': sorted(unique_items),
        'current_filters': {
            'status': status_filter,
            'item': item_filter,
            'user': user_filter,
        }
    }
    
    return render(request, 'progress/analytics/feedback_requests_list.html', context)