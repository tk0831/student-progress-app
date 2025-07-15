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
    
    # グループデータを準備
    group_data = []
    total_students = 0
    
    for group in groups:
        students = CustomUser.objects.filter(group=group, user_type='student')
        student_count = students.count()
        total_students += student_count
        
        group_data.append({
            'group': group,
            'student_count': student_count,
            'students': students[:5]  # 最初の5名のみ表示
        })
    
    total_groups = groups.count()
    avg_members = total_students / total_groups if total_groups > 0 else 0
    
    context = {
        'group_data': group_data,
        'total_groups': total_groups,
        'total_students': total_students,
        'avg_members': avg_members
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
    # ソートパラメータ取得
    sort_by = request.GET.get('sort', 'completion')
    period_days = 30  # 集計期間
    
    groups = Group.objects.all()
    ranking_data = []
    
    # 期間の計算
    end_date = date.today()
    start_date = end_date - timedelta(days=period_days)
    
    for group in groups:
        members = CustomUser.objects.filter(group=group, user_type='student').select_related('stats')
        student_count = members.count()
        
        if student_count > 0:
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
            
            avg_daily_hours = daily_avg_hours / student_count if student_count > 0 else 0
            
            # グループ平均完了率
            avg_completion = members.aggregate(
                avg=Avg('stats__completion_rate'))['avg'] or 0
            
            # 日報提出率計算（過去30日間）
            total_expected_reports = student_count * period_days
            actual_reports = DailyProgress.objects.filter(
                user__in=members,
                date__gte=start_date,
                date__lte=end_date
            ).count()
            report_submission_rate = int((actual_reports / total_expected_reports * 100) if total_expected_reports > 0 else 0)
            
            ranking_data.append({
                'group': group,
                'student_count': student_count,
                'total_hours': total_hours,
                'avg_daily_hours': round(avg_daily_hours, 1),
                'avg_completion': round(avg_completion, 1),
                'report_submission_rate': report_submission_rate
            })
    
    # ソート処理
    if sort_by == 'reports':
        ranking_data.sort(key=lambda x: x['report_submission_rate'], reverse=True)
    elif sort_by == 'hours':
        ranking_data.sort(key=lambda x: x['avg_daily_hours'], reverse=True)
    else:  # completion
        ranking_data.sort(key=lambda x: x['avg_completion'], reverse=True)
    
    context = {
        'ranking_data': ranking_data,
        'current_sort': sort_by,
        'period_days': period_days,
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


@permission_required('manage_groups')
def group_delete_view(request, group_id):
    """グループ削除"""
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.success(request, f'グループ「{group_name}」を削除しました。')
        return redirect('group_list')
    
    # メンバー数を確認
    member_count = CustomUser.objects.filter(group=group).count()
    
    context = {
        'group': group,
        'member_count': member_count
    }
    
    return render(request, 'progress/group/group_confirm_delete.html', context)


@permission_required('manage_groups')
def group_members_view(request, group_id):
    """グループメンバー管理"""
    group = get_object_or_404(Group, id=group_id)
    
    if request.method == 'POST':
        # メンバー割り当て処理
        user_ids = request.POST.getlist('user_ids')
        if user_ids:
            CustomUser.objects.filter(id__in=user_ids).update(group=group)
            messages.success(request, f'{len(user_ids)}名をグループ「{group.name}」に追加しました。')
        
        # メンバー削除処理
        remove_ids = request.POST.getlist('remove_ids')
        if remove_ids:
            CustomUser.objects.filter(id__in=remove_ids).update(group=None)
            messages.success(request, f'{len(remove_ids)}名をグループから削除しました。')
        
        return redirect('group_members', group_id=group.id)
    
    # 現在のメンバー
    members = CustomUser.objects.filter(group=group, user_type='student').select_related('stats')
    
    # グループ未所属の研修生
    unassigned_students = CustomUser.objects.filter(
        group__isnull=True, 
        user_type='student'
    ).select_related('stats')
    
    context = {
        'group': group,
        'members': members,
        'unassigned_students': unassigned_students
    }
    
    return render(request, 'progress/group/group_members.html', context)