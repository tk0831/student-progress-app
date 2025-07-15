from django.core.management.base import BaseCommand
from django.db.models import Count
from progress.models import Stamp


class Command(BaseCommand):
    help = '重複スタンプをクリーンアップします（一人一投稿一スタンプに）'

    def handle(self, *args, **options):
        self.stdout.write('重複スタンプをチェックしています...')
        
        # 同じ管理者が同じ日報に複数のスタンプを押しているケースを検出
        duplicates = Stamp.objects.values('daily_progress', 'admin_user').annotate(
            stamp_count=Count('id')
        ).filter(stamp_count__gt=1)
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('✅ 重複スタンプはありません'))
            return
        
        self.stdout.write(f'⚠️  {len(duplicates)}件の重複が見つかりました')
        
        # 各重複ケースについて処理
        for dup in duplicates:
            stamps = Stamp.objects.filter(
                daily_progress_id=dup['daily_progress'],
                admin_user_id=dup['admin_user']
            ).order_by('-created_at')
            
            # 最新のスタンプを残して、他は削除
            keep_stamp = stamps.first()
            delete_stamps = stamps[1:]
            
            self.stdout.write(
                f'  日報ID: {dup["daily_progress"]}, 管理者ID: {dup["admin_user"]} - '
                f'{keep_stamp.stamp_type.emoji} を残して、{len(delete_stamps)}個削除'
            )
            
            for stamp in delete_stamps:
                stamp.delete()
        
        self.stdout.write(self.style.SUCCESS('✅ クリーンアップが完了しました'))