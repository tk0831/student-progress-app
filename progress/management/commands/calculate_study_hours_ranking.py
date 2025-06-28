from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Sum, Count
from datetime import date, timedelta
from progress.models import CustomUser, DailyProgress, WeeklyStudyHoursRanking


class Command(BaseCommand):
    help = '週間学習時間ランキングを計算して保存します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存のランキングデータを強制的に再計算します',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'週間学習時間ランキング計算開始: {timezone.now()}')
        )
        
        try:
            # 今週の月曜日と日曜日を計算
            today = date.today()
            days_since_monday = today.weekday()
            week_start = today - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            
            # 全研修生を取得
            students = CustomUser.objects.filter(user_type='student')
            
            ranking_data = []
            
            for student in students:
                # 今週の学習記録を取得
                week_progress = DailyProgress.objects.filter(
                    user=student,
                    date__gte=week_start,
                    date__lte=week_end
                )
                
                # 総学習時間と学習日数を計算
                stats = week_progress.aggregate(
                    total_hours=Sum('study_hours'),
                    study_days=Count('date')
                )
                
                total_hours = stats['total_hours'] or 0
                study_days = stats['study_days'] or 0
                
                if total_hours > 0:  # 学習時間がある学生のみランキング対象
                    avg_daily_hours = total_hours / 7  # 週7日で割って日平均を計算
                    
                    ranking_data.append({
                        'user': student,
                        'total_study_hours': total_hours,
                        'study_days': study_days,
                        'average_daily_hours': round(avg_daily_hours, 1),
                    })
            
            # 学習時間でソート（多い順）
            ranking_data.sort(key=lambda x: -x['total_study_hours'])
            
            # 上位5位まで保存（学習時間は5位まで表示）
            for rank, data in enumerate(ranking_data[:5], 1):
                WeeklyStudyHoursRanking.objects.update_or_create(
                    user=data['user'],
                    week_start=week_start,
                    defaults={
                        'week_end': week_end,
                        'rank': rank,
                        'total_study_hours': data['total_study_hours'],
                        'study_days': data['study_days'],
                        'average_daily_hours': data['average_daily_hours'],
                    }
                )
                
                self.stdout.write(
                    f"{rank}位: {data['user'].username} "
                    f"(学習時間: {data['total_study_hours']}時間, "
                    f"学習日数: {data['study_days']}日, "
                    f"日平均: {data['average_daily_hours']}時間)"
                )
            
            if not ranking_data:
                self.stdout.write(
                    self.style.WARNING('今週は学習記録がある研修生がいませんでした。')
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'週間学習時間ランキング計算完了: {timezone.now()}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'週間学習時間ランキング計算中にエラーが発生しました: {str(e)}')
            )
            raise e