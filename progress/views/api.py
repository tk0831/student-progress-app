from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Avg, Count
from datetime import datetime, date, timedelta
from ..models import CustomUser, Group, Phase, CurriculumItem, DailyProgress, UserStats, WeeklyRanking
from ..decorators import permission_required


def get_user_weekly_rankings(user):
    """指定ユーザーの週間ランキングを取得する関数"""
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


@permission_required('view_analytics')
def get_weekly_summary(request):
    """週間サマリーデータを取得するAPI"""
    # 今週の月曜日を計算
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    # 今週の進捗記録を取得
    this_week_progress = DailyProgress.objects.filter(
        date__gte=week_start,
        date__lte=week_end
    )
    
    # 基本統計
    total_records = this_week_progress.count()
    total_hours = this_week_progress.aggregate(
        total=Sum('study_hours'))['total'] or 0
    avg_hours = total_hours / total_records if total_records > 0 else 0
    
    # 日別統計
    daily_stats = []
    for i in range(7):
        current_date = week_start + timedelta(days=i)
        day_records = this_week_progress.filter(date=current_date).count()
        day_hours = this_week_progress.filter(date=current_date).aggregate(
            total=Sum('study_hours'))['total'] or 0
        
        daily_stats.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day_name': ['月', '火', '水', '木', '金', '土', '日'][i],
            'records': day_records,
            'hours': float(day_hours)
        })
    
    # フィードバック要請数
    feedback_requests = this_week_progress.filter(feedback_requested=True).count()
    pending_feedback = this_week_progress.filter(
        feedback_requested=True, feedback_provided=False
    ).count()
    
    return JsonResponse({
        'week_start': week_start.strftime('%Y-%m-%d'),
        'week_end': week_end.strftime('%Y-%m-%d'),
        'total_records': total_records,
        'total_hours': float(total_hours),
        'avg_hours': round(avg_hours, 1),
        'daily_stats': daily_stats,
        'feedback_requests': feedback_requests,
        'pending_feedback': pending_feedback
    })


@permission_required('view_analytics')
def analytics_data_api(request):
    """チャート用データAPI"""
    chart_type = request.GET.get('type', 'daily_hours')
    
    # 表示対象ユーザーの決定
    if request.user.user_type == 'student':
        target_users = [request.user]
    else:
        user_id = request.GET.get('user_id')
        if user_id:
            try:
                target_user = CustomUser.objects.get(id=user_id, user_type='student')
                target_users = [target_user]
            except CustomUser.DoesNotExist:
                target_users = CustomUser.objects.filter(user_type='student')
        else:
            target_users = CustomUser.objects.filter(user_type='student')
    
    if chart_type == 'daily_hours':
        # 日別学習時間推移（過去30日）
        end_date = date.today()
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
    
    elif chart_type == 'grade_distribution':
        # 階級分布
        grade_data = {}
        for grade, label in DailyProgress.GRADE_CHOICES:
            count = target_users.filter(stats__current_grade=grade).count()
            grade_data[grade] = count
        
        return JsonResponse({
            'labels': [label for grade, label in DailyProgress.GRADE_CHOICES],
            'datasets': [{
                'data': [grade_data.get(grade, 0) for grade, label in DailyProgress.GRADE_CHOICES],
                'backgroundColor': [
                    '#EF4444',  # S級 - Red
                    '#F97316',  # A級 - Orange  
                    '#EAB308',  # B級 - Yellow
                    '#22C55E',  # C級 - Green
                    '#3B82F6'   # D級 - Blue
                ]
            }]
        })
    
    elif chart_type == 'phase_progress':
        # Phase別進捗状況
        phase_data = []
        for phase in Phase.objects.all().order_by('phase_number'):
            current_count = target_users.filter(stats__current_phase=phase).count()
            completed_count = 0  # 完了者数の計算は複雑なので簡略化
            
            phase_data.append({
                'phase': f'Phase {phase.phase_number}',
                'current': current_count,
                'completed': completed_count
            })
        
        return JsonResponse({
            'labels': [item['phase'] for item in phase_data],
            'datasets': [
                {
                    'label': '現在取組中',
                    'data': [item['current'] for item in phase_data],
                    'backgroundColor': 'rgba(59, 130, 246, 0.5)'
                },
                {
                    'label': '完了',
                    'data': [item['completed'] for item in phase_data],
                    'backgroundColor': 'rgba(34, 197, 94, 0.5)'
                }
            ]
        })
    
    else:
        return JsonResponse({'error': '無効なチャートタイプです'}, status=400)


@login_required
def get_last_week_mvp(request):
    """先週の週間MVPデータを取得するAPI"""
    # 先週の月曜日を計算
    today = date.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    
    # 先週のランキングデータを取得
    mvp_rankings = WeeklyRanking.objects.filter(
        week_start=last_monday
    ).select_related('user').order_by('rank')[:3]
    
    mvp_list = []
    for ranking in mvp_rankings:
        mvp_list.append({
            'username': ranking.user.username,
            'rank': ranking.rank,
            'completed_days': ranking.completed_standard_days,
            'efficiency': round(ranking.efficiency_score, 1),
            'study_hours': float(ranking.total_study_hours)
        })
    
    return JsonResponse({
        'week_start': last_monday.strftime('%Y-%m-%d'),
        'week_end': (last_monday + timedelta(days=6)).strftime('%Y-%m-%d'),
        'mvp_list': mvp_list
    })


@login_required
def get_phase_items(request):
    """Phase IDに基づいてカリキュラム項目を取得するAPI（進捗バリデーション付き）"""
    phase_id = request.GET.get('phase_id')
    if not phase_id:
        return JsonResponse({'error': 'Phase ID is required'}, status=400)
    
    try:
        # Phaseを取得
        phase = Phase.objects.get(id=phase_id)
        
        # 基本的な項目リスト
        items = CurriculumItem.objects.filter(phase_id=phase_id).order_by('order')
        
        # 研修生の場合は進捗状況をチェック
        user = request.user
        if user.user_type == 'student':
            progress_status = user.get_current_progress_status()
            if progress_status:
                available_phase_ids = list(progress_status['available_phases'].values_list('id', flat=True))
                
                # 選択されたフェーズが利用可能かチェック
                if int(phase_id) not in available_phase_ids:
                    return JsonResponse({'error': 'このフェーズは選択できません'}, status=403)
        
        # 各項目の完了情報を取得
        items_data = []
        for item in items:
            item_data = {
                'id': item.id,
                'code': item.item_code,
                'name': item.name,
                'display': f"{item.item_code}: {item.name}",
                'estimated_days': item.estimated_days,
                'order': item.order
            }
            
            # 完了した項目の情報を取得
            progress_records = DailyProgress.objects.filter(
                user=user,
                current_item=item
            ).order_by('date')
            
            if progress_records.exists():
                # この項目で実際に学習した日数をカウント
                days_taken = progress_records.count()
                start_date = progress_records.first().date
                end_date = progress_records.last().date
                
                # 現在学習中の項目でない場合のみ完了とする
                # （次の項目に進んでいる or 同じPhaseの後の項目に進んでいる）
                user_stats = getattr(user, 'stats', None)
                is_completed = False
                
                if user_stats:
                    current_phase = user_stats.current_phase
                    current_item = user_stats.current_item
                    
                    # 現在のPhaseが進んでいる場合
                    if current_phase and phase.phase_number < current_phase.phase_number:
                        is_completed = True
                    # 同じPhaseで、現在の項目が進んでいる場合
                    elif current_phase and phase.phase_number == current_phase.phase_number:
                        if current_item and item.order < current_item.order:
                            is_completed = True
                        elif not current_item:  # Phase完了済み
                            is_completed = True
                
                item_data['completed'] = is_completed
                item_data['days_taken'] = days_taken
                item_data['start_date'] = start_date.strftime('%Y-%m-%d')
                item_data['end_date'] = end_date.strftime('%Y-%m-%d')
                
                # デバッグ情報
                item_data['debug_info'] = {
                    'record_count': progress_records.count(),
                    'estimated_days': item.estimated_days,
                    'actual_days': days_taken
                }
            else:
                item_data['completed'] = False
                
            items_data.append(item_data)
        
        # 現在のユーザーの統計情報も含める
        user_stats = getattr(user, 'stats', None)
        current_info = {
            'current_phase_id': user_stats.current_phase.id if user_stats and user_stats.current_phase else None,
            'current_phase_number': user_stats.current_phase.phase_number if user_stats and user_stats.current_phase else None,
            'current_item_id': user_stats.current_item.id if user_stats and user_stats.current_item else None,
            'current_item_order': user_stats.current_item.order if user_stats and user_stats.current_item else None
        }
        
        return JsonResponse({
            'items': items_data,
            'phase_number': phase.phase_number,
            'current_info': current_info
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)