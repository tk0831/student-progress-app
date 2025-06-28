from django.core.management.base import BaseCommand
from django.db import transaction
from progress.models import UserStats, DailyProgress

class Command(BaseCommand):
    help = '既存データの階級を新しい進捗効率ベースの基準で再計算します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際の更新を行わず、結果のみを表示'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN モード: 実際の更新は行いません'))
        
        # 全ユーザーのUserStatsを取得
        user_stats_list = UserStats.objects.select_related('user').all()
        
        updated_count = 0
        
        with transaction.atomic():
            for user_stats in user_stats_list:
                # 古い値を保存
                old_grade = user_stats.current_grade
                old_efficiency = user_stats.efficiency_score
                
                # 新しい効率スコアと階級を計算
                new_efficiency = user_stats.calculate_efficiency_score()
                new_grade = user_stats.calculate_grade_from_efficiency()
                
                # 変更があった場合のみ更新
                if old_grade != new_grade or old_efficiency != new_efficiency:
                    if not dry_run:
                        user_stats.efficiency_score = new_efficiency
                        user_stats.current_grade = new_grade
                        user_stats.save()
                        
                        # 該当ユーザーの最新の進捗記録も更新
                        latest_progress = DailyProgress.objects.filter(
                            user=user_stats.user
                        ).order_by('-date').first()
                        
                        if latest_progress:
                            latest_progress.current_grade = new_grade
                            latest_progress.save()
                    
                    updated_count += 1
                    
                    self.stdout.write(
                        f'User: {user_stats.user.username} | '
                        f'Grade: {old_grade} → {new_grade} | '
                        f'Efficiency: {old_efficiency:.2f} → {new_efficiency:.2f}'
                    )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'DRY RUN完了: {updated_count}名のユーザーで変更が検出されました'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'階級再計算完了: {updated_count}名のユーザーを更新しました'
                )
            )
            
        # 統計情報を表示
        grade_stats = {}
        for user_stats in UserStats.objects.all():
            if not dry_run:
                # 実際に更新された値を使用
                grade = user_stats.current_grade
            else:
                # 計算された新しい値を使用
                grade = user_stats.calculate_grade_from_efficiency()
            
            grade_stats[grade] = grade_stats.get(grade, 0) + 1
        
        self.stdout.write('\n=== 階級分布 ===')
        for grade in ['S', 'A', 'B', 'C', 'D']:
            count = grade_stats.get(grade, 0)
            self.stdout.write(f'{grade}級: {count}名')