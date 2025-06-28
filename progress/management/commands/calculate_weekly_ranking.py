from django.core.management.base import BaseCommand
from django.utils import timezone
from progress.views import calculate_weekly_ranking


class Command(BaseCommand):
    help = '週間ランキングを計算して保存します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='既存のランキングデータを強制的に再計算します',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f'週間ランキング計算開始: {timezone.now()}')
        )
        
        try:
            ranking_data = calculate_weekly_ranking()
            
            if ranking_data:
                self.stdout.write(
                    self.style.SUCCESS(f'今週のランキング上位3位:')
                )
                for i, data in enumerate(ranking_data, 1):
                    self.stdout.write(
                        f"{i}位: {data['user'].username} "
                        f"(標準日数: {data['total_standard_days']}日, "
                        f"効率: {data['avg_efficiency']:.2f}, "
                        f"学習時間: {data['total_study_hours']}時間)"
                    )
            else:
                self.stdout.write(
                    self.style.WARNING('今週は完了項目がある研修生がいませんでした。')
                )
            
            self.stdout.write(
                self.style.SUCCESS(f'週間ランキング計算完了: {timezone.now()}')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'週間ランキング計算中にエラーが発生しました: {str(e)}')
            )
            raise e