from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Sum, Avg
from .models import CustomUser, Group, Phase, CurriculumItem, DailyProgress, UserStats
from .forms import DailyProgressForm, LoginForm
from .decorators import (
    permission_required, training_admin_required, 
    system_admin_required, student_required
)


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # ユーザータイプ別にリダイレクト
                if user.user_type == 'student':
                    return redirect('student_dashboard')
                elif user.user_type == 'training_admin':
                    return redirect('training_admin_dashboard')
                elif user.user_type == 'system_admin':
                    return redirect('system_admin_dashboard')
                else:
                    # 旧データ対応
                    return redirect('training_admin_dashboard')
            else:
                messages.error(request, 'ユーザー名またはパスワードが正しくありません。')
    else:
        form = LoginForm()
    
    return render(request, 'progress/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'ログアウトしました。')
    return redirect('login')


@student_required
def student_dashboard(request):
    user_stats, created = UserStats.objects.get_or_create(user=request.user)
    recent_progress = DailyProgress.objects.filter(user=request.user).order_by('-date')[:7]
    
    context = {
        'user_stats': user_stats,
        'recent_progress': recent_progress,
        'phases': Phase.objects.all(),
    }
    return render(request, 'progress/student_dashboard.html', context)


@training_admin_required
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
    return render(request, 'progress/training_admin_dashboard.html', context)


@system_admin_required  
def system_admin_dashboard(request):
    """システム管理者専用ダッシュボード"""
    total_students = CustomUser.objects.filter(user_type='student').count()
    total_training_admins = CustomUser.objects.filter(user_type='training_admin').count()
    total_system_admins = CustomUser.objects.filter(user_type='system_admin').count()
    recent_progress = DailyProgress.objects.order_by('-date')[:10]
    
    grade_stats = {}
    for grade, label in DailyProgress.GRADE_CHOICES:
        count = UserStats.objects.filter(current_grade=grade).count()
        grade_stats[label] = count
    
    # システム管理者は全機能にアクセス可能
    context = {
        'total_students': total_students,
        'total_training_admins': total_training_admins,
        'total_system_admins': total_system_admins,
        'recent_progress': recent_progress,
        'grade_stats': grade_stats,
        'groups': Group.objects.all(),
        'user_type': 'system_admin'
    }
    return render(request, 'progress/system_admin_dashboard.html', context)


@login_required
def admin_dashboard(request):
    """旧admin_dashboardを適切にリダイレクト"""
    if request.user.is_training_admin:
        return redirect('training_admin_dashboard')
    elif request.user.is_system_admin:
        return redirect('system_admin_dashboard')
    else:
        return redirect('student_dashboard')


@login_required
def progress_create(request):
    if request.user.user_type != 'student':
        return redirect('admin_dashboard')
    
    today = timezone.now().date()
    existing_progress = DailyProgress.objects.filter(user=request.user, date=today).first()
    
    if request.method == 'POST':
        form = DailyProgressForm(request.POST, instance=existing_progress)
        if form.is_valid():
            progress = form.save(commit=False)
            progress.user = request.user
            progress.date = today
            
            # 経過日数と階級を計算
            if request.user.start_date:
                progress.days_elapsed = (today - request.user.start_date).days + 1
                if progress.days_elapsed <= 120:
                    progress.current_grade = 'S'
                elif progress.days_elapsed <= 150:
                    progress.current_grade = 'A'
                elif progress.days_elapsed <= 180:
                    progress.current_grade = 'B'
                elif progress.days_elapsed <= 210:
                    progress.current_grade = 'C'
                else:
                    progress.current_grade = 'D'
            
            progress.save()
            
            # ユーザー統計を更新
            user_stats, created = UserStats.objects.get_or_create(user=request.user)
            user_stats.total_study_hours = DailyProgress.objects.filter(
                user=request.user
            ).aggregate(Sum('study_hours'))['study_hours__sum'] or 0
            user_stats.current_phase = progress.current_phase
            user_stats.current_item = progress.current_item
            user_stats.current_grade = progress.current_grade
            user_stats.days_elapsed = progress.days_elapsed
            user_stats.save()
            
            messages.success(request, '進捗記録を保存しました。')
            return redirect('student_dashboard')
    else:
        form = DailyProgressForm(instance=existing_progress)
    
    return render(request, 'progress/progress_form.html', {'form': form})


@login_required
def progress_list(request):
    if request.user.user_type == 'admin':
        progress_list = DailyProgress.objects.all().order_by('-date')
    else:
        progress_list = DailyProgress.objects.filter(user=request.user).order_by('-date')
    
    return render(request, 'progress/progress_list.html', {'progress_list': progress_list})


@login_required
def group_ranking(request):
    groups = Group.objects.all()
    ranking_data = []
    
    for group in groups:
        students = CustomUser.objects.filter(group=group, user_type='student')
        if students.exists():
            avg_progress = UserStats.objects.filter(
                user__in=students
            ).aggregate(
                avg_completion=Avg('completion_rate'),
                avg_hours=Avg('total_study_hours')
            )
            
            ranking_data.append({
                'group': group,
                'student_count': students.count(),
                'avg_completion': avg_progress['avg_completion'] or 0,
                'avg_hours': avg_progress['avg_hours'] or 0,
            })
    
    ranking_data.sort(key=lambda x: x['avg_completion'], reverse=True)
    
    return render(request, 'progress/group_ranking.html', {'ranking_data': ranking_data})
