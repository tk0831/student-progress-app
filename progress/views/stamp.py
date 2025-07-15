from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils import timezone
from ..models import DailyProgress, StampType, Stamp, CustomUser
from ..decorators import training_admin_required


@login_required
@require_POST
@training_admin_required
def add_stamp(request):
    """日報にスタンプを追加"""
    progress_id = request.POST.get('progress_id')
    stamp_type_id = request.POST.get('stamp_type_id')
    
    if not progress_id or not stamp_type_id:
        return JsonResponse({'success': False, 'error': '必須パラメータが不足しています'}, status=400)
    
    try:
        progress = get_object_or_404(DailyProgress, id=progress_id)
        stamp_type = get_object_or_404(StampType, id=stamp_type_id, is_active=True)
        
        # 既に同じ進捗に対してスタンプを押しているかチェック
        existing_stamp = Stamp.objects.filter(
            daily_progress=progress,
            admin_user=request.user
        ).first()
        
        if existing_stamp:
            if existing_stamp.stamp_type == stamp_type:
                # 同じスタンプの場合は削除（トグル動作）
                existing_stamp.delete()
                return JsonResponse({
                    'success': True,
                    'action': 'removed',
                    'message': f'{stamp_type.emoji} を取り消しました'
                })
            else:
                # 異なるスタンプの場合は置き換え
                old_emoji = existing_stamp.stamp_type.emoji
                existing_stamp.stamp_type = stamp_type
                existing_stamp.created_at = timezone.now()
                existing_stamp.save()
                return JsonResponse({
                    'success': True,
                    'action': 'replaced',
                    'message': f'{old_emoji} を {stamp_type.emoji} に変更しました',
                    'stamp': {
                        'id': existing_stamp.id,
                        'emoji': stamp_type.emoji,
                        'name': stamp_type.name,
                        'color': stamp_type.color,
                        'admin': existing_stamp.admin_user.username,
                        'created_at': existing_stamp.created_at.strftime('%Y-%m-%d %H:%M')
                    }
                })
        
        # 新規作成
        stamp = Stamp.objects.create(
            daily_progress=progress,
            stamp_type=stamp_type,
            admin_user=request.user,
            created_at=timezone.now()
        )
        
        return JsonResponse({
            'success': True,
            'action': 'added',
            'message': f'{stamp_type.emoji} を追加しました',
            'stamp': {
                'id': stamp.id,
                'emoji': stamp_type.emoji,
                'name': stamp_type.name,
                'color': stamp_type.color,
                'admin': stamp.admin_user.username,
                'created_at': stamp.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def get_progress_stamps(request, progress_id):
    """特定の日報のスタンプ一覧を取得"""
    progress = get_object_or_404(DailyProgress, id=progress_id)
    
    # 権限チェック: 研修生は自分の記録のみ、管理者は全ての記録
    if request.user.user_type == 'student' and progress.user != request.user:
        return JsonResponse({'error': '権限がありません'}, status=403)
    
    stamps = Stamp.objects.filter(daily_progress=progress).select_related('stamp_type', 'admin_user')
    
    stamp_data = []
    for stamp in stamps:
        stamp_data.append({
            'id': stamp.id,
            'emoji': stamp.stamp_type.emoji,
            'name': stamp.stamp_type.name,
            'color': stamp.stamp_type.color,
            'admin': stamp.admin_user.username,
            'created_at': stamp.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    # 現在のユーザーが押したスタンプを取得
    user_stamp = stamps.filter(admin_user=request.user).first() if request.user.user_type != 'student' else None
    
    # 利用可能なスタンプタイプも返す
    available_stamps = []
    if request.user.user_type != 'student':
        for stamp_type in StampType.objects.filter(is_active=True).order_by('order'):
            available_stamps.append({
                'id': stamp_type.id,
                'emoji': stamp_type.emoji,
                'name': stamp_type.name,
                'color': stamp_type.color,
                'is_stamped': user_stamp and user_stamp.stamp_type.id == stamp_type.id
            })
    
    return JsonResponse({
        'stamps': stamp_data,
        'available_stamps': available_stamps,
        'can_stamp': request.user.user_type != 'student',
        'user_stamp': {
            'emoji': user_stamp.stamp_type.emoji,
            'name': user_stamp.stamp_type.name,
            'id': user_stamp.stamp_type.id
        } if user_stamp else None
    })


@login_required
def get_stamp_summary(request):
    """ユーザーのスタンプサマリーを取得"""
    user_id = request.GET.get('user_id')
    
    if user_id:
        # 管理者が特定ユーザーのサマリーを見る場合
        if request.user.user_type == 'student':
            return JsonResponse({'error': '権限がありません'}, status=403)
        user = get_object_or_404(CustomUser, id=user_id)
    else:
        # 自分のサマリーを見る場合
        user = request.user
    
    # スタンプの集計
    stamp_counts = {}
    stamps = Stamp.objects.filter(
        daily_progress__user=user
    ).select_related('stamp_type')
    
    for stamp in stamps:
        emoji = stamp.stamp_type.emoji
        if emoji not in stamp_counts:
            stamp_counts[emoji] = {
                'count': 0,
                'name': stamp.stamp_type.name,
                'color': stamp.stamp_type.color
            }
        stamp_counts[emoji]['count'] += 1
    
    # 最新のスタンプを取得
    recent_stamps = Stamp.objects.filter(
        daily_progress__user=user
    ).select_related('stamp_type', 'admin_user').order_by('-created_at')[:10]
    
    recent_data = []
    for stamp in recent_stamps:
        recent_data.append({
            'emoji': stamp.stamp_type.emoji,
            'name': stamp.stamp_type.name,
            'date': stamp.daily_progress.date.strftime('%Y-%m-%d'),
            'admin': stamp.admin_user.username,
            'created_at': stamp.created_at.strftime('%Y-%m-%d %H:%M')
        })
    
    return JsonResponse({
        'stamp_counts': stamp_counts,
        'recent_stamps': recent_data,
        'total_stamps': stamps.count()
    })