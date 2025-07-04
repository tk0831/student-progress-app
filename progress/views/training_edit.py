from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Min, Max, Count
from ..models import CustomUser, DailyProgress, UserStats, Phase, CurriculumItem
from ..forms import UserTrainingEditForm, ItemProgressEditForm
from ..decorators import system_admin_required


@login_required
@system_admin_required
def edit_user_training(request, user_id):
    """システム管理者用ユーザー研修詳細編集ビュー"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        form = UserTrainingEditForm(request.POST, user=user)
        if form.is_valid():
            # 研修開始日を更新
            if form.cleaned_data.get('start_date'):
                user.start_date = form.cleaned_data['start_date']
                user.save()
            
            # 新しい進捗記録を作成
            today = timezone.now().date()
            current_phase = form.cleaned_data.get('current_phase')
            current_item = form.cleaned_data.get('current_item')
            days_elapsed = form.cleaned_data.get('days_elapsed')
            
            if current_phase:
                # 今日の進捗記録を作成または更新
                progress, created = DailyProgress.objects.get_or_create(
                    user=user,
                    date=today,
                    defaults={
                        'current_phase': current_phase,
                        'current_item': current_item,
                        'days_elapsed': days_elapsed or 0,
                        'study_hours': 0,
                        'current_grade': user.user_stats.current_grade if hasattr(user, 'user_stats') else 'A'
                    }
                )
                
                if not created:
                    progress.current_phase = current_phase
                    progress.current_item = current_item
                    if days_elapsed is not None:
                        progress.days_elapsed = days_elapsed
                    progress.save()
                
                # UserStatsを更新
                user_stats, _ = UserStats.objects.get_or_create(user=user)
                user_stats.update_stats()
                
                messages.success(request, f'{user.username}の研修情報を更新しました。')
                return redirect('user_detail', user_id=user.id)
        else:
            messages.error(request, 'フォームにエラーがあります。')
    else:
        form = UserTrainingEditForm(user=user)
    
    context = {
        'form': form,
        'target_user': user,
    }
    return render(request, 'progress/admin/edit_user_training.html', context)


@login_required
@system_admin_required
def edit_progress_history(request, user_id):
    """ユーザーの進捗履歴編集ビュー"""
    user = get_object_or_404(CustomUser, id=user_id)
    progress_list = DailyProgress.objects.filter(user=user).order_by('-date')
    
    context = {
        'target_user': user,
        'progress_list': progress_list,
    }
    return render(request, 'progress/admin/edit_progress_history.html', context)


@login_required
@system_admin_required
def edit_progress_record(request, progress_id):
    """個別進捗記録編集ビュー"""
    progress = get_object_or_404(DailyProgress, id=progress_id)
    
    if request.method == 'POST':
        form = ItemProgressEditForm(request.POST, instance=progress)
        if form.is_valid():
            form.save()
            
            # UserStatsを更新
            user_stats, _ = UserStats.objects.get_or_create(user=progress.user)
            user_stats.update_stats()
            
            messages.success(request, '進捗記録を更新しました。')
            return redirect('edit_progress_history', user_id=progress.user.id)
    else:
        form = ItemProgressEditForm(instance=progress)
    
    context = {
        'form': form,
        'progress': progress,
        'target_user': progress.user,
    }
    return render(request, 'progress/admin/edit_progress_record.html', context)


@login_required
@system_admin_required
@require_POST
def delete_progress_record(request, progress_id):
    """進捗記録削除（システム管理者のみ）"""
    progress = get_object_or_404(DailyProgress, id=progress_id)
    user = progress.user
    progress.delete()
    
    # UserStatsを更新
    user_stats, _ = UserStats.objects.get_or_create(user=user)
    user_stats.update_stats()
    
    messages.success(request, '進捗記録を削除しました。')
    return redirect('edit_progress_history', user_id=user.id)


@login_required
@system_admin_required
def ajax_get_phase_items(request):
    """Phase選択時に対応する項目リストを返すAjaxビュー"""
    phase_id = request.GET.get('phase_id')
    if not phase_id:
        return JsonResponse({'items': []})
    
    try:
        phase = Phase.objects.get(id=phase_id)
        items = phase.curriculumitem_set.all().order_by('order')
        items_data = [
            {
                'id': item.id,
                'code': item.item_code,
                'name': item.name,
                'display': f'{item.item_code}: {item.name}'
            }
            for item in items
        ]
        return JsonResponse({'items': items_data})
    except Phase.DoesNotExist:
        return JsonResponse({'items': []})


@login_required
@system_admin_required
@require_POST
def batch_update_progress(request, user_id):
    """進捗記録の一括更新"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # 新しい開始日を設定
    new_start_date = request.POST.get('new_start_date')
    if new_start_date:
        user.start_date = new_start_date
        user.save()
        
        # 全進捗記録の経過日数を再計算
        progress_records = DailyProgress.objects.filter(user=user)
        for progress in progress_records:
            if user.start_date:
                progress.days_elapsed = (progress.date - user.start_date).days + 1
                progress.save()
        
        messages.success(request, f'研修開始日を変更し、{progress_records.count()}件の進捗記録を更新しました。')
    
    return redirect('edit_progress_history', user_id=user.id)


@login_required
@system_admin_required
def edit_item_progress(request, user_id):
    """項目別経過日数編集ビュー"""
    user = get_object_or_404(CustomUser, id=user_id)
    
    # 全フェーズと項目を取得
    phases = Phase.objects.all().order_by('phase_number')
    
    # 各項目の進捗状況を集計
    item_progress_data = []
    
    for phase in phases:
        phase_data = {
            'phase': phase,
            'items': []
        }
        
        for item in phase.items.all().order_by('order'):
            # この項目に関する進捗記録を取得
            item_records = DailyProgress.objects.filter(
                user=user,
                current_item=item
            ).aggregate(
                start_date=Min('date'),
                end_date=Max('date'),
                record_count=Count('id')
            )
            
            # 経過日数を計算
            if item_records['start_date'] and item_records['end_date']:
                days_spent = (item_records['end_date'] - item_records['start_date']).days + 1
                status = 'completed'
                
                # 最新の進捗記録から完了状態を確認
                latest_record = DailyProgress.objects.filter(
                    user=user,
                    current_item=item
                ).order_by('-date').first()
                
                if latest_record and not latest_record.item_completed:
                    status = 'in_progress'
            else:
                days_spent = 0
                status = 'not_started'
            
            item_data = {
                'item': item,
                'start_date': item_records['start_date'],
                'end_date': item_records['end_date'],
                'days_spent': days_spent,
                'record_count': item_records['record_count'],
                'status': status,
                'efficiency': round(item.estimated_days / days_spent * 100, 1) if days_spent > 0 and item.estimated_days else 0
            }
            
            phase_data['items'].append(item_data)
        
        item_progress_data.append(phase_data)
    
    # 現在の進捗情報
    user_stats = UserStats.objects.filter(user=user).first()
    
    if request.method == 'POST':
        # 項目別の進捗を更新
        updated_count = 0
        
        # POSTデータを項目IDごとにグループ化
        item_updates = {}
        for key, value in request.POST.items():
            if key.startswith('item_'):
                parts = key.split('_')
                if len(parts) >= 3:
                    field_type = parts[1]  # 'days', 'start', 'end'
                    item_id = parts[2]
                    
                    if item_id not in item_updates:
                        item_updates[item_id] = {}
                    
                    item_updates[item_id][field_type] = value
        
        # 各項目を更新
        for item_id, updates in item_updates.items():
            try:
                item = CurriculumItem.objects.get(id=item_id)
                
                # 更新データを取得
                new_days = int(updates.get('days', '0')) if updates.get('days') else 0
                start_date_str = updates.get('start', '')
                end_date_str = updates.get('end', '')
                
                # 日付が指定されている場合の処理
                if start_date_str and end_date_str:
                    try:
                        from datetime import datetime
                        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                        
                        if end_date >= start_date:
                            # 既存の記録を削除
                            DailyProgress.objects.filter(
                                user=user,
                                current_item=item
                            ).delete()
                            
                            # 指定期間で新しい記録を作成
                            current_date = start_date
                            days_count = 0
                            total_days = (end_date - start_date).days + 1
                            
                            while current_date <= end_date:
                                # 他の項目と重複しない日付のみ作成
                                if not DailyProgress.objects.filter(user=user, date=current_date).exists():
                                    DailyProgress.objects.create(
                                        user=user,
                                        date=current_date,
                                        current_phase=item.phase,
                                        current_item=item,
                                        study_hours=8,
                                        current_grade=user_stats.current_grade if user_stats else 'D',
                                        item_completed=(current_date == end_date),
                                        planned_hours=8,
                                        days_elapsed=(current_date - user.start_date).days + 1 if user.start_date else days_count + 1,
                                        reflection='管理者による一括編集',
                                        next_goal='次の項目へ進む',
                                        action_plan='計画通り進める'
                                    )
                                current_date += timezone.timedelta(days=1)
                                days_count += 1
                            
                            updated_count += 1
                            continue
                    except ValueError:
                        pass  # 日付の解析に失敗した場合は通常の処理を続行
                
                # 経過日数のみが指定されている場合
                elif new_days > 0:
                    # この項目に関する既存の進捗記録を取得
                    existing_records = DailyProgress.objects.filter(
                        user=user,
                        current_item=item
                    ).order_by('date')
                    
                    # 開始日を決定
                    if existing_records.exists():
                        # 既存の記録がある場合は、その開始日を使用
                        start_date = existing_records.first().date
                    else:
                        # 未開始の項目の場合、適切な開始日を計算
                        # すべての進捗記録から最後の日付を取得
                        last_progress = DailyProgress.objects.filter(
                            user=user
                        ).order_by('-date').first()
                        
                        if last_progress:
                            start_date = last_progress.date + timezone.timedelta(days=1)
                        else:
                            start_date = user.start_date if user.start_date else timezone.now().date()
                    
                    # 既存の記録を削除（この項目に関するもののみ）
                    existing_records.delete()
                    
                    # 日付の重複を避けるため、使用済みの日付を取得
                    used_dates = set(DailyProgress.objects.filter(
                        user=user
                    ).values_list('date', flat=True))
                    
                    # 新しい記録を作成
                    created_count = 0
                    current_date = start_date
                    
                    while created_count < new_days:
                        # 使用済みの日付はスキップ
                        if current_date not in used_dates:
                            DailyProgress.objects.create(
                                user=user,
                                date=current_date,
                                current_phase=item.phase,
                                current_item=item,
                                study_hours=8,  # デフォルト値
                                current_grade=user_stats.current_grade if user_stats else 'D',
                                item_completed=(created_count == new_days - 1),  # 最終日に完了
                                # 必須フィールドにデフォルト値を設定
                                planned_hours=8,
                                days_elapsed=(current_date - user.start_date).days + 1 if user.start_date else created_count + 1,
                                reflection='管理者による一括編集',
                                next_goal='次の項目へ進む',
                                action_plan='計画通り進める'
                            )
                            created_count += 1
                        
                        current_date += timezone.timedelta(days=1)
                
                updated_count += 1
                    
            except (CurriculumItem.DoesNotExist, ValueError):
                continue
        
        if updated_count > 0:
            # UserStatsを更新
            if user_stats:
                user_stats.update_stats()
            
            messages.success(request, f'{updated_count}項目の経過日数を更新しました。')
            return redirect('edit_item_progress', user_id=user.id)
    
    context = {
        'target_user': user,
        'user_stats': user_stats,
        'item_progress_data': item_progress_data,
    }
    
    return render(request, 'progress/admin/edit_item_progress.html', context)