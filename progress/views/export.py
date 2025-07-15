from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.db.models import Sum, Avg, Count
from datetime import datetime, date, timedelta
import csv
from ..models import CustomUser, Group, Phase, CurriculumItem, DailyProgress, UserStats
from ..decorators import permission_required


@permission_required('view_analytics')
def export_menu_view(request):
    """エクスポートメニュー表示"""
    return render(request, 'progress/partials/export_menu.html')


@permission_required('view_analytics')
def export_data_view(request, export_type=None):
    """データエクスポート"""
    if export_type is None:
        export_type = request.GET.get('type', 'progress')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # CSVファイル名生成
    today = date.today().strftime('%Y%m%d')
    
    if export_type == 'progress':
        filename = f'progress_data_{today}.csv'
        return export_progress_csv(request, filename, date_from, date_to)
    elif export_type == 'users':
        filename = f'user_data_{today}.csv'
        return export_users_csv(request, filename)
    elif export_type == 'groups':
        filename = f'group_data_{today}.csv'
        return export_groups_csv(request, filename)
    elif export_type == 'feedback':
        filename = f'feedback_data_{today}.csv'
        return export_feedback_csv(request, filename, date_from, date_to)
    elif export_type == 'analytics':
        analytics_type = request.GET.get('type', 'daily_hours')
        filename = f'analytics_{analytics_type}_{today}.csv'
        return export_analytics_csv(request, filename, analytics_type)
    else:
        return HttpResponse('無効なエクスポートタイプです', status=400)


def export_progress_csv(request, filename, date_from=None, date_to=None):
    """進捗データのCSVエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # BOMを追加（Excel対応）
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # ヘッダー行
    writer.writerow([
        '記録日', 'ユーザー名', '氏名', 'グループ', 'Phase', '項目コード', '項目名',
        '学習時間', '階級', '経過日数', '遅れ日数', '項目完了', 'フィードバック要請',
        '詰まった内容', '振り返り', '明日の目標'
    ])
    
    # データ取得
    queryset = DailyProgress.objects.select_related(
        'user', 'user__group', 'current_phase', 'current_item'
    ).order_by('-date')
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    # データ行
    for progress in queryset:
        writer.writerow([
            progress.date.strftime('%Y/%m/%d'),
            progress.user.username,
            f'{progress.user.last_name} {progress.user.first_name}',
            progress.user.group.name if progress.user.group else '',
            f'Phase {progress.current_phase.phase_number}',
            progress.current_item.item_code,
            progress.current_item.name,
            progress.study_hours,
            progress.current_grade,
            progress.days_elapsed,
            progress.delay_days,
            '完了' if progress.item_completed else '未完了',
            '要請' if progress.feedback_requested else '',
            progress.stuck_content,
            progress.reflection,
            progress.next_goal
        ])
    
    return response


def export_users_csv(request, filename):
    """ユーザーデータのCSVエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # BOMを追加（Excel対応）
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # ヘッダー行
    writer.writerow([
        'ユーザー名', '氏名', 'メールアドレス', 'グループ', '担当管理者',
        '研修開始日', '現在のPhase', '現在の項目', '現在の階級',
        '累計学習時間', '経過日数', '遅れ日数', '完了率', '効率スコア'
    ])
    
    # データ取得
    users = CustomUser.objects.filter(user_type='student').select_related(
        'group', 'assigned_admin', 'stats'
    ).order_by('username')
    
    # データ行
    for user in users:
        stats = getattr(user, 'stats', None)
        writer.writerow([
            user.username,
            f'{user.last_name} {user.first_name}',
            user.email,
            user.group.name if user.group else '',
            user.assigned_admin.username if user.assigned_admin else '',
            user.start_date.strftime('%Y/%m/%d') if user.start_date else '',
            f'Phase {stats.current_phase.phase_number}' if stats and stats.current_phase else '',
            stats.current_item.item_code if stats and stats.current_item else '',
            stats.current_grade if stats else '',
            stats.total_study_hours if stats else 0,
            stats.days_elapsed if stats else 0,
            stats.delay_days if stats else 0,
            f'{stats.completion_rate}%' if stats else '0%',
            stats.efficiency_score if stats else 0
        ])
    
    return response


def export_groups_csv(request, filename):
    """グループデータのCSVエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # BOMを追加（Excel対応）
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # ヘッダー行
    writer.writerow([
        'グループ名', '説明', 'メンバー数', '総学習時間', '平均学習時間',
        '一日平均学習時間', '平均完了率', 'S級', 'A級', 'B級', 'C級', 'D級'
    ])
    
    # データ取得
    groups = Group.objects.all()
    
    # データ行
    for group in groups:
        members = CustomUser.objects.filter(group=group, user_type='student')
        member_count = members.count()
        
        if member_count > 0:
            # 総学習時間
            total_hours = DailyProgress.objects.filter(
                user__in=members
            ).aggregate(total=Sum('study_hours'))['total'] or 0
            
            # 平均学習時間
            avg_hours = total_hours / member_count
            
            # 一日平均学習時間
            daily_avg_hours = 0
            for member in members:
                if member.start_date:
                    days_elapsed = (date.today() - member.start_date).days + 1
                    member_total = DailyProgress.objects.filter(user=member).aggregate(
                        total=Sum('study_hours'))['total'] or 0
                    if days_elapsed > 0:
                        daily_avg_hours += member_total / days_elapsed
            daily_avg_hours = daily_avg_hours / member_count if member_count > 0 else 0
            
            # 平均完了率
            avg_completion = members.aggregate(
                avg=Avg('stats__completion_rate'))['avg'] or 0
            
            # 各階級の人数
            grade_counts = {}
            for grade, label in DailyProgress.GRADE_CHOICES:
                count = members.filter(stats__current_grade=grade).count()
                grade_counts[grade] = count
        else:
            total_hours = 0
            avg_hours = 0
            daily_avg_hours = 0
            avg_completion = 0
            grade_counts = {grade: 0 for grade, label in DailyProgress.GRADE_CHOICES}
        
        writer.writerow([
            group.name,
            group.description,
            member_count,
            total_hours,
            round(avg_hours, 1),
            round(daily_avg_hours, 1),
            f'{avg_completion:.1f}%',
            grade_counts.get('S', 0),
            grade_counts.get('A', 0),
            grade_counts.get('B', 0),
            grade_counts.get('C', 0),
            grade_counts.get('D', 0)
        ])
    
    return response


def export_feedback_csv(request, filename, date_from=None, date_to=None):
    """フィードバックデータのCSVエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # BOMを追加（Excel対応）
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    # ヘッダー行
    writer.writerow([
        '記録日', 'ユーザー名', '氏名', 'Phase', '項目コード', '項目名',
        '具体的な問題内容', '試したこと', '詰まった内容',
        'フィードバック提供済み', 'フィードバック提供者', 'フィードバック内容',
        'フィードバック提供日時'
    ])
    
    # データ取得
    queryset = DailyProgress.objects.filter(feedback_requested=True).select_related(
        'user', 'current_phase', 'current_item', 'feedback_admin'
    ).order_by('-date')
    
    if date_from:
        queryset = queryset.filter(date__gte=date_from)
    if date_to:
        queryset = queryset.filter(date__lte=date_to)
    
    # データ行
    for progress in queryset:
        writer.writerow([
            progress.date.strftime('%Y/%m/%d'),
            progress.user.username,
            f'{progress.user.last_name} {progress.user.first_name}',
            f'Phase {progress.current_phase.phase_number}',
            progress.current_item.item_code,
            progress.current_item.name,
            progress.problem_detail,
            progress.tried_solutions,
            progress.stuck_content,
            '提供済み' if progress.feedback_provided else '未対応',
            progress.feedback_admin.username if progress.feedback_admin else '',
            progress.feedback_response,
            progress.feedback_provided_at.strftime('%Y/%m/%d %H:%M') if progress.feedback_provided_at else ''
        ])
    
    return response


def export_analytics_csv(request, filename, analytics_type):
    """分析データのCSVエクスポート"""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # BOMを追加（Excel対応）
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    if analytics_type == 'daily_hours':
        # 日別学習時間
        writer.writerow(['日付', '総学習時間', '平均学習時間', '記録数'])
        
        daily_data = DailyProgress.objects.values('date').annotate(
            total_hours=Sum('study_hours'),
            avg_hours=Avg('study_hours'),
            count=Count('id')
        ).order_by('-date')[:30]  # 最新30日
        
        for data in daily_data:
            writer.writerow([
                data['date'].strftime('%Y/%m/%d'),
                data['total_hours'],
                round(data['avg_hours'], 1),
                data['count']
            ])
    
    elif analytics_type == 'phase_progress':
        # Phase別進捗
        writer.writerow(['Phase', '人数', '平均完了率', '平均学習時間'])
        
        phases = Phase.objects.all().order_by('phase_number')
        for phase in phases:
            users_in_phase = CustomUser.objects.filter(
                stats__current_phase=phase, user_type='student'
            )
            count = users_in_phase.count()
            
            if count > 0:
                avg_completion = users_in_phase.aggregate(
                    avg=Avg('stats__completion_rate'))['avg'] or 0
                avg_hours = DailyProgress.objects.filter(
                    user__in=users_in_phase, current_phase=phase
                ).aggregate(avg=Avg('study_hours'))['avg'] or 0
            else:
                avg_completion = 0
                avg_hours = 0
            
            writer.writerow([
                f'Phase {phase.phase_number}',
                count,
                f'{avg_completion:.1f}%',
                round(avg_hours, 1)
            ])
    
    elif analytics_type == 'grade_distribution':
        # 階級分布
        writer.writerow(['階級', '人数', '割合'])
        
        total_students = CustomUser.objects.filter(user_type='student').count()
        
        for grade, label in DailyProgress.GRADE_CHOICES:
            count = CustomUser.objects.filter(
                stats__current_grade=grade, user_type='student'
            ).count()
            percentage = (count / total_students * 100) if total_students > 0 else 0
            
            writer.writerow([
                f'{grade}級 ({label})',
                count,
                f'{percentage:.1f}%'
            ])
    
    return response