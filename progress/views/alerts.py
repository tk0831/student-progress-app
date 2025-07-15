from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from ..models import Alert
from ..decorators import permission_required


@login_required
def alert_list_view(request):
    """アラート一覧表示"""
    # 権限チェック
    if request.user.user_type == 'student':
        # 研修生は自分のアラートのみ表示
        alerts = Alert.objects.filter(
            user=request.user,
            is_active=True
        ).order_by('-created_at')
    else:
        # 管理者は全アラートを表示
        if not (request.user.can_view_analytics or request.user.is_system_admin):
            messages.error(request, 'アラートを表示する権限がありません。')
            return redirect('dashboard')
        
        # フィルター処理
        alerts = Alert.objects.filter(is_active=True).select_related('user')
        
        # アラートタイプフィルター
        alert_type = request.GET.get('alert_type')
        if alert_type:
            alerts = alerts.filter(alert_type=alert_type)
        
        # 重要度フィルター
        severity = request.GET.get('severity')
        if severity:
            alerts = alerts.filter(severity=severity)
        
        # 解決状況フィルター
        resolved = request.GET.get('resolved')
        if resolved == 'true':
            alerts = alerts.filter(is_resolved=True)
        elif resolved == 'false':
            alerts = alerts.filter(is_resolved=False)
        
        # 検索
        search = request.GET.get('search')
        if search:
            alerts = alerts.filter(
                Q(user__username__icontains=search) |
                Q(title__icontains=search) |
                Q(message__icontains=search)
            )
        
        alerts = alerts.order_by('-created_at')
    
    # 統計情報（管理者のみ）
    stats = {}
    if request.user.user_type != 'student':
        stats = {
            'total_alerts': Alert.objects.filter(is_active=True).count(),
            'critical_alerts': Alert.objects.filter(is_active=True, severity='critical').count(),
            'high_alerts': Alert.objects.filter(is_active=True, severity='high').count(),
            'unresolved_alerts': Alert.objects.filter(is_active=True, is_resolved=False).count(),
            'grade_risk_alerts': Alert.objects.filter(is_active=True, alert_type='grade_risk').count(),
            'no_report_alerts': Alert.objects.filter(is_active=True, alert_type='no_report').count(),
        }
    
    context = {
        'alerts': alerts,
        'stats': stats,
        'alert_types': Alert.ALERT_TYPES,
        'severity_levels': Alert.SEVERITY_LEVELS,
        'current_filters': {
            'alert_type': alert_type,
            'severity': severity,
            'resolved': resolved,
            'search': search,
        }
    }
    
    return render(request, 'progress/alerts/alert_list.html', context)


@login_required
def alert_detail_view(request, alert_id):
    """アラート詳細表示"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    # 権限チェック
    if request.user.user_type == 'student' and alert.user != request.user:
        messages.error(request, '他のユーザーのアラートは表示できません。')
        return redirect('alert_list')
    
    if request.user.user_type != 'student' and not (request.user.can_view_analytics or request.user.is_system_admin):
        messages.error(request, 'アラートを表示する権限がありません。')
        return redirect('dashboard')
    
    context = {
        'alert': alert
    }
    
    return render(request, 'progress/alerts/alert_detail.html', context)


@permission_required('manage_students')
def alert_resolve_view(request, alert_id):
    """アラート解決"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    if request.method == 'POST':
        if not alert.is_resolved:
            alert.resolve(resolved_by=request.user)
            messages.success(request, f'アラート「{alert.title}」を解決済みにしました。')
        else:
            messages.warning(request, 'このアラートは既に解決済みです。')
        
        return redirect('alert_list')
    
    context = {
        'alert': alert
    }
    
    return render(request, 'progress/alerts/alert_resolve.html', context)


@permission_required('manage_students')
def alert_dismiss_view(request, alert_id):
    """アラート無効化"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    if request.method == 'POST':
        alert.is_active = False
        alert.save()
        messages.success(request, f'アラート「{alert.title}」を無効化しました。')
        return redirect('alert_list')
    
    context = {
        'alert': alert
    }
    
    return render(request, 'progress/alerts/alert_dismiss.html', context)


@login_required
def alert_widget_view(request):
    """アラートウィジェット（ダッシュボード用）"""
    if request.user.user_type == 'student':
        # 研修生は自分のアラートのみ
        alerts = Alert.objects.filter(
            user=request.user,
            is_active=True,
            is_resolved=False
        ).order_by('-created_at')[:5]
    else:
        # 管理者は緊急・重要アラートのみ
        alerts = Alert.objects.filter(
            is_active=True,
            is_resolved=False,
            severity__in=['critical', 'high']
        ).select_related('user').order_by('-created_at')[:10]
    
    context = {
        'alerts': alerts
    }
    
    return render(request, 'progress/alerts/alert_widget.html', context)