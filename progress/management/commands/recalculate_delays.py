from django.core.management.base import BaseCommand
from django.db import transaction
from progress.models import UserStats, DailyProgress

class Command(BaseCommand):
    help = '既存データの遅れ日数を新しいロジックで再計算します'

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
        
        self.stdout.write('\n=== 遅れ日数再計算結果 ===')
        
        with transaction.atomic():
            for user_stats in user_stats_list:
                # 古い値を保存
                old_delay = user_stats.delay_days
                old_days_elapsed = user_stats.days_elapsed
                
                # 新しい進捗状況を計算
                progress_status = user_stats.calculate_progress_status()
                
                if progress_status:
                    new_delay = progress_status['delay_days']
                    new_days_elapsed = progress_status['actual_days']
                    
                    # 変更があった場合のみ更新
                    if old_delay != new_delay or old_days_elapsed != new_days_elapsed:
                        if not dry_run:
                            user_stats.delay_days = new_delay
                            user_stats.days_elapsed = new_days_elapsed
                            user_stats.save(update_fields=['delay_days', 'days_elapsed'])
                            
                            # 該当ユーザーの最新の進捗記録も更新
                            latest_progress = DailyProgress.objects.filter(
                                user=user_stats.user
                            ).order_by('-date').first()
                            
                            if latest_progress:
                                latest_progress.days_elapsed = new_days_elapsed
                                latest_progress.save(update_fields=['days_elapsed'])
                        
                        updated_count += 1
                        
                        # 進捗状況の判定
                        if progress_status['is_ahead']:
                            status = f"先行中（+{new_delay}日）"
                        elif progress_status['is_on_track']:
                            status = "順調"
                        else:
                            status = f"{abs(new_delay)}日遅れ"
                        
                        self.stdout.write(
                            f'User: {user_stats.user.username} | '
                            f'経過日数: {old_days_elapsed} → {new_days_elapsed} | '
                            f'遅れ: {old_delay} → {new_delay}日 | '
                            f'期待: {progress_status["expected_days"]}日 | '
                            f'状況: {status}'
                        )
                else:
                    # 進捗状況が計算できない場合（開始日やPhase/Item未設定）
                    if user_stats.user.start_date is None:
                        reason = "開始日未設定"
                    elif user_stats.current_phase is None:
                        reason = "現在Phase未設定"
                    elif user_stats.current_item is None:
                        reason = "現在項目未設定"
                    else:
                        reason = "不明"
                    
                    self.stdout.write(
                        self.style.WARNING(
                            f'User: {user_stats.user.username} | 計算不可: {reason}'
                        )
                    )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nDRY RUN完了: {updated_count}名のユーザーで変更が検出されました'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n遅れ日数再計算完了: {updated_count}名のユーザーを更新しました'
                )
            )
            
        # 遅れ状況統計を表示
        delay_stats = {'先行': 0, '順調': 0, '軽度遅れ': 0, '重度遅れ': 0, '計算不可': 0}
        
        for user_stats in UserStats.objects.select_related('user').all():
            progress_status = user_stats.calculate_progress_status()
            if progress_status:
                if progress_status['is_ahead']:
                    delay_stats['先行'] += 1
                elif progress_status['is_on_track']:
                    delay_stats['順調'] += 1
                elif progress_status['delay_days'] >= -14:  # -14日以上（14日以内の遅れ）
                    delay_stats['軽度遅れ'] += 1
                else:  # -14日未満（15日以上の遅れ）
                    delay_stats['重度遅れ'] += 1
            else:
                delay_stats['計算不可'] += 1
        
        self.stdout.write('\n=== 遅れ状況分布 ===')
        for status, count in delay_stats.items():
            self.stdout.write(f'{status}: {count}名')