from django.core.management.base import BaseCommand
from progress.models import StampType


class Command(BaseCommand):
    help = '新しいスタンプタイプに更新します'

    def handle(self, *args, **options):
        self.stdout.write('スタンプタイプを更新します...')
        
        # 既存のスタンプタイプを無効化
        StampType.objects.all().update(is_active=False)
        
        # 新しいスタンプタイプを定義
        new_stamp_types = [
            # 非常に良いスタンプ
            {
                'name': '素晴らしい！',
                'emoji': '🌟',
                'color': 'yellow',
                'description': '特に優れた成果や努力に対して',
                'order': 1
            },
            {
                'name': '完璧！',
                'emoji': '💎',
                'color': 'purple',
                'description': '完璧な仕上がりや理解度に対して',
                'order': 2
            },
            {
                'name': '天才！',
                'emoji': '🧠',
                'color': 'indigo',
                'description': '優れた発想や問題解決に対して',
                'order': 3
            },
            
            # 良いスタンプ
            {
                'name': 'よくできました',
                'emoji': '👍',
                'color': 'blue',
                'description': '良い成果や進捗に対して',
                'order': 10
            },
            {
                'name': 'Good!',
                'emoji': '✨',
                'color': 'green',
                'description': '良い取り組みに対して',
                'order': 11
            },
            {
                'name': 'ナイス！',
                'emoji': '👏',
                'color': 'teal',
                'description': '良い努力や成果に対して',
                'order': 12
            },
            
            # 普通のスタンプ
            {
                'name': 'OK',
                'emoji': '👌',
                'color': 'gray',
                'description': '標準的な進捗に対して',
                'order': 20
            },
            {
                'name': '了解',
                'emoji': '✅',
                'color': 'gray',
                'description': '確認・承認の意味で',
                'order': 21
            },
            
            # 励ましのスタンプ
            {
                'name': 'がんばって！',
                'emoji': '💪',
                'color': 'orange',
                'description': '応援・励ましの意味で',
                'order': 30
            },
            {
                'name': 'ファイト！',
                'emoji': '🔥',
                'color': 'red',
                'description': '困難に立ち向かう時の応援',
                'order': 31
            },
            {
                'name': '次回に期待',
                'emoji': '🌱',
                'color': 'green',
                'description': '成長を期待する意味で',
                'order': 32
            },
            
            # 注意・改善のスタンプ
            {
                'name': 'もう少し',
                'emoji': '😅',
                'color': 'yellow',
                'description': 'もう少し努力が必要な時',
                'order': 40
            },
            {
                'name': '要改善',
                'emoji': '⚠️',
                'color': 'orange',
                'description': '改善が必要な点がある時',
                'order': 41
            },
            {
                'name': '頑張ろう',
                'emoji': '😤',
                'color': 'red',
                'description': 'より一層の努力が必要な時',
                'order': 42
            },
            
            # 特殊なスタンプ
            {
                'name': '質問あり',
                'emoji': '❓',
                'color': 'purple',
                'description': '質問や疑問点がある時',
                'order': 50
            },
            {
                'name': 'ヒント',
                'emoji': '💡',
                'color': 'yellow',
                'description': 'ヒントや助言を与える時',
                'order': 51
            },
            {
                'name': '確認済み',
                'emoji': '📝',
                'color': 'blue',
                'description': '内容を確認した時',
                'order': 52
            }
        ]
        
        # スタンプタイプを作成または更新
        for stamp_data in new_stamp_types:
            stamp_type, created = StampType.objects.update_or_create(
                emoji=stamp_data['emoji'],
                defaults={
                    'name': stamp_data['name'],
                    'color': stamp_data['color'],
                    'description': stamp_data['description'],
                    'order': stamp_data['order'],
                    'is_active': True
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'✅ 作成: {stamp_data["emoji"]} {stamp_data["name"]}')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'🔄 更新: {stamp_data["emoji"]} {stamp_data["name"]}')
                )
        
        # 古いスタンプタイプで無効化されたものを表示
        inactive_stamps = StampType.objects.filter(is_active=False)
        if inactive_stamps.exists():
            self.stdout.write('\n無効化されたスタンプ:')
            for stamp in inactive_stamps:
                self.stdout.write(f'  ❌ {stamp.emoji} {stamp.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ スタンプタイプの更新が完了しました！')
        )