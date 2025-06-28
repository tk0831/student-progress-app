from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg, Count
from datetime import datetime, date, timedelta
from ..models import CustomUser, Group, DailyProgress, UserStats
from ..forms import GroupForm, UserGroupAssignForm
from ..decorators import permission_required


@permission_required('manage_groups')
def group_list_view(request):
    """グループ一覧表示"""
    groups = Group.objects.all().annotate(
        member_count=Count('customuser')
    ).order_by('name')
    
    context = {
        'groups': groups
    }
    
    return render(request, 'progress/group/group_list.html', context)


@permission_required('manage_groups')
def group_create_view(request):
    """グループ作成"""
    if request.method == 'POST':
        form = GroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'グループ「{group.name}」を作成しました。')
            return redirect('group_list')
    else:
        form = GroupForm()
    
    return render(request, 'progress/group/group_form.html', {'form': form, 'action': '新規作成'})


@permission_required('view_analytics')
def group_detail_view(request, group_id):
    """グループ詳細表示"""
    group = get_object_or_404(Group, id=group_id)
    
    # グループメンバー
    members = CustomUser.objects.filter(group=group, user_type='student').select_related('stats')
    
    # グループ統計
    total_members = members.count()
    if total_members > 0:
        # 総学習時間
        total_hours = DailyProgress.objects.filter(
            user__in=members
        ).aggregate(total=Sum('study_hours'))['total'] or 0
        
        # 平均学習時間
        avg_hours = total_hours / total_members if total_members > 0 else 0
        
        # 一日平均学習時間（研修開始からの累計）
        daily_avg_hours = 0
        for member in members:
            if member.start_date:
                days_elapsed = (date.today() - member.start_date).days + 1
                member_total = DailyProgress.objects.filter(user=member).aggregate(
                    total=Sum('study_hours'))['total'] or 0
                if days_elapsed > 0:
                    daily_avg_hours += member_total / days_elapsed
        
        daily_avg_hours = daily_avg_hours / total_members if total_members > 0 else 0
        
        # 階級分布
        grade_distribution = {}
        for grade, label in DailyProgress.GRADE_CHOICES:
            count = members.filter(stats__current_grade=grade).count()
            grade_distribution[label] = count
    else:
        total_hours = 0
        avg_hours = 0
        daily_avg_hours = 0
        grade_distribution = {}
    
    context = {
        'group': group,
        'members': members,
        'total_members': total_members,
        'total_hours': total_hours,
        'avg_hours': round(avg_hours, 1),
        'daily_avg_hours': round(daily_avg_hours, 1),
        'grade_distribution': grade_distribution,
    }
    
    return render(request, 'progress/group/group_detail.html', context)


@permission_required('view_analytics')
def group_ranking_view(request):
    """グループランキング表示"""
    groups = Group.objects.all()
    
    group_stats = []
    for group in groups:
        members = CustomUser.objects.filter(group=group, user_type='student')
        member_count = members.count()
        
        if member_count > 0:
            # グループ総学習時間
            total_hours = DailyProgress.objects.filter(
                user__in=members
            ).aggregate(total=Sum('study_hours'))['total'] or 0
            
            # グループ一日平均学習時間
            daily_avg_hours = 0
            for member in members:
                if member.start_date:
                    days_elapsed = (date.today() - member.start_date).days + 1
                    member_total = DailyProgress.objects.filter(user=member).aggregate(
                        total=Sum('study_hours'))['total'] or 0
                    if days_elapsed > 0:
                        daily_avg_hours += member_total / days_elapsed
            
            daily_avg_hours = daily_avg_hours / member_count if member_count > 0 else 0
            
            # グループ平均完了率
            avg_completion = members.aggregate(
                avg=Avg('stats__completion_rate'))['avg'] or 0
            
            # 各階級の人数
            grade_counts = {}
            for grade, label in DailyProgress.GRADE_CHOICES:
                count = members.filter(stats__current_grade=grade).count()
                grade_counts[grade] = count
            
            group_stats.append({
                'group': group,
                'member_count': member_count,
                'total_hours': total_hours,
                'daily_avg_hours': round(daily_avg_hours, 1),
                'avg_completion': round(avg_completion, 1),
                'grade_counts': grade_counts
            })
    
    # 一日平均学習時間でソート
    group_stats.sort(key=lambda x: x['daily_avg_hours'], reverse=True)
    
    # ランキング順位を付与
    for i, stat in enumerate(group_stats, 1):
        stat['rank'] = i
    
    context = {
        'group_stats': group_stats,
        'grades': DailyProgress.GRADE_CHOICES,
    }
    
    return render(request, 'progress/group/group_ranking.html', context)


@permission_required('manage_groups')
def group_update_view(request, group_id):
    """グループ更新"""
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        form = GroupForm(request.POST, instance=group)
        if form.is_valid():
            group = form.save()
            messages.success(request, f'グループ「{group.name}」を更新しました。')
            return redirect('group_list')
    else:
        form = GroupForm(instance=group)
    
    return render(request, 'progress/group/group_form.html', {'form': form, 'action': '更新', 'group': group})