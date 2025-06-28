from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from ..forms import LoginForm, UserRegistrationForm


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
    
    return render(request, 'progress/auth/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'ログアウトしました。')
    return redirect('login')


def register_view(request):
    """新規ユーザー登録（誰でも登録可能）"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 自動的にログイン
            login(request, user)
            messages.success(request, f'ようこそ、{user.username}さん！アカウントを作成しました。')
            return redirect('student_dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'progress/auth/register.html', {'form': form})