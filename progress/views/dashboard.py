from django.shortcuts import render
from django.db.models import Sum, Count
from datetime import date, timedelta
from ..models import CustomUser, Group, Phase, DailyProgress, UserStats, WeeklyRanking
from ..decorators import student_required, permission_required


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


def get_user_study_hours_rankings(user):
    """指定ユーザーの週間学習時間ランキングを取得する関数"""
    from ..models import WeeklyStudyHoursRanking
    
    study_rankings = []
    for week_offset in range(4):  # 過去4週間
        target_monday = date.today() - timedelta(days=date.today().weekday() + (week_offset * 7))
        
        study_ranking = WeeklyStudyHoursRanking.objects.filter(
            user=user,
            week_start=target_monday
        ).first()
        
        if study_ranking:
            study_rankings.append(study_ranking)
    
    return study_rankings


@student_required
def student_dashboard(request):
    user_stats, created = UserStats.objects.get_or_create(user=request.user)
    recent_progress = DailyProgress.objects.filter(user=request.user).order_by('-date')[:7]
    
    # 週間ランキングを取得（受賞した場合のみ表示）
    current_rankings = get_user_weekly_rankings(request.user)
    
    # 学習時間ランキングを取得
    study_rankings = get_user_study_hours_rankings(request.user)
    
    context = {
        'user_stats': user_stats,
        'recent_progress': recent_progress,
        'phases': Phase.objects.all(),
        'current_rankings': current_rankings,
        'study_rankings': study_rankings,
    }
    return render(request, 'progress/dashboard/student_dashboard.html', context)


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
    return render(request, 'progress/dashboard/training_admin_dashboard.html', context)


# system_admin_dashboardは同じ関数を使用（URLでのみ区別）
system_admin_dashboard = training_admin_dashboard