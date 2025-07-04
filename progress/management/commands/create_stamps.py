from django.core.management.base import BaseCommand
from progress.models import StampType


class Command(BaseCommand):
    help = 'スタンプの初期データを作成する'
    
    def handle(self, *args, **options):
        stamps = [
            {
                'name': 'いいね！',
                'emoji': '👍',
                'color': 'blue',
                'description': '良い進捗です',
                'order': 1
            },
            {
                'name': '素晴らしい！',
                'emoji': '🌟',
                'color': 'yellow',
                'description': '特に優れた成果です',
                'order': 2
            },
            {
                'name': '頑張った！',
                'emoji': '💪',
                'color': 'red',
                'description': '努力が認められます',
                'order': 3
            },
            {
                'name': 'ナイス！',
                'emoji': '✨',
                'color': 'purple',
                'description': '良い取り組みです',
                'order': 4
            },
            {
                'name': 'すごい！',
                'emoji': '🎉',
                'color': 'green',
                'description': '目覚ましい成果です',
                'order': 5
            },
            {
                'name': '完璧！',
                'emoji': '💯',
                'color': 'orange',
                'description': '完璧な仕上がりです',
                'order': 6
            },
            {
                'name': 'グッドジョブ！',
                'emoji': '👏',
                'color': 'indigo',
                'description': '素晴らしい仕事です',
                'order': 7
            },
            {
                'name': 'ファイト！',
                'emoji': '🔥',
                'color': 'pink',
                'description': '応援しています',
                'order': 8
            }
        ]
        
        created_count = 0
        for stamp_data in stamps:
            stamp_type, created = StampType.objects.get_or_create(
                name=stamp_data['name'],
                defaults=stamp_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'スタンプ "{stamp_type.emoji} {stamp_type.name}" を作成しました'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'スタンプ "{stamp_type.emoji} {stamp_type.name}" は既に存在します'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'合計 {created_count} 個のスタンプを作成しました'
            )
        )