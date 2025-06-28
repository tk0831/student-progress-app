from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from progress.views import calculate_weekly_ranking


class Command(BaseCommand):
    help = '週次タスクを実行します（毎週日曜日の夜に実行）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際の処理は行わず、実行内容のみを表示します',
        )

    def handle(self, *args, **options):
        today = date.today()
        is_sunday = today.weekday() == 6  # 日曜日は6
        
        self.stdout.write(
            self.style.SUCCESS(f'週次タスク開始: {timezone.now()}')
        )
        self.stdout.write(f'今日は: {today} ({"日曜日" if is_sunday else "日曜日以外"})')
        
        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING('DRY RUN モード - 実際の処理は行いません')
            )
        
        # 日曜日でなくても強制実行可能（テスト用）
        if not is_sunday:
            self.stdout.write(
                self.style.WARNING(
                    '今日は日曜日ではありませんが、週間ランキング計算を実行します。'
                )
            )
        
        if not options['dry_run']:
            try:
                # 週間ランキング計算
                ranking_data = calculate_weekly_ranking()
                
                if ranking_data:
                    self.stdout.write(
                        self.style.SUCCESS('✅ 週間ランキング計算完了')
                    )
                    self.stdout.write('📊 今週の上位3位:')
                    for i, data in enumerate(ranking_data, 1):
                        self.stdout.write(
                            f"  {i}位: {data['user'].username} "
                            f"(完了項目標準日数: {data['total_standard_days']}日)"
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING('⚠️  今週は項目完了者がいませんでした')
                    )
                
                # 学習時間ランキング計算
                from django.core.management import call_command
                self.stdout.write('📊 学習時間ランキング計算中...')
                call_command('calculate_study_hours_ranking')
                self.stdout.write(
                    self.style.SUCCESS('✅ 学習時間ランキング計算完了')
                )
                
                # 将来的な週次タスクをここに追加
                # - 週間レポート生成
                # - 遅れている研修生への通知
                # - 統計データのクリーンアップ など
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 全週次タスク完了: {timezone.now()}')
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ 週次タスク実行中にエラーが発生: {str(e)}')
                )
                raise e
        else:
            self.stdout.write('📋 実行予定のタスク:')
            self.stdout.write('  1. 週間ランキング計算')
            self.stdout.write('  2. (将来) 週間レポート生成')
            self.stdout.write('  3. (将来) 遅れ通知')
            self.stdout.write('DRY RUN完了 - 実際の処理は実行されませんでした')