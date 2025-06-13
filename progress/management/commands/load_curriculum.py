from django.core.management.base import BaseCommand
from progress.models import Phase, CurriculumItem


class Command(BaseCommand):
    help = 'カリキュラムの初期データを投入します'

    def handle(self, *args, **options):
        self.stdout.write('カリキュラムデータの投入を開始します...')
        
        # Phase データ
        phases_data = [
            {
                'phase_number': 1,
                'name': 'フロントエンド基礎1',
                'description': 'HTML、CSS、JavaScriptの基礎を学習',
                'total_days': 7,
                'start_day': 1,
                'end_day': 7
            },
            {
                'phase_number': 2,
                'name': 'フロントエンド基礎2',
                'description': 'JavaScript応用とjQueryを学習',
                'total_days': 7,
                'start_day': 8,
                'end_day': 14
            },
            {
                'phase_number': 3,
                'name': 'フロントエンド実践',
                'description': 'レイアウト作成とサンプルサイト制作',
                'total_days': 16,
                'start_day': 15,
                'end_day': 30
            },
            {
                'phase_number': 4,
                'name': 'サーバーサイド基礎1',
                'description': 'PHP基礎とプログラミング概念',
                'total_days': 30,
                'start_day': 31,
                'end_day': 60
            },
            {
                'phase_number': 5,
                'name': 'サーバーサイド基礎2',
                'description': 'データベース基礎とSQL',
                'total_days': 18,
                'start_day': 61,
                'end_day': 78
            },
            {
                'phase_number': 6,
                'name': 'サーバーサイド実践',
                'description': 'Laravelフレームワークとアプリ開発',
                'total_days': 32,
                'start_day': 79,
                'end_day': 110
            },
            {
                'phase_number': 7,
                'name': 'WEBシステム自作',
                'description': 'オリジナルWebシステムの設計・開発',
                'total_days': 40,
                'start_day': 111,
                'end_day': 150
            }
        ]
        
        # Phaseを作成
        for phase_data in phases_data:
            phase, created = Phase.objects.get_or_create(
                phase_number=phase_data['phase_number'],
                defaults=phase_data
            )
            if created:
                self.stdout.write(f'Phase {phase.phase_number}: {phase.name} を作成しました')
            else:
                self.stdout.write(f'Phase {phase.phase_number}: {phase.name} は既に存在します')
        
        # カリキュラム項目データ
        curriculum_items = [
            # Phase 1: フロントエンド基礎1
            {'phase_number': 1, 'item_code': '1-A', 'name': 'HTMLとCSS', 'estimated_hours': 4.0, 'estimated_days': 3, 'order': 1},
            {'phase_number': 1, 'item_code': '1-B', 'name': 'リスト・テーブル', 'estimated_hours': 1.0, 'estimated_days': None, 'order': 2},
            {'phase_number': 1, 'item_code': '1-C', 'name': 'idとclass', 'estimated_hours': 2.0, 'estimated_days': None, 'order': 3},
            {'phase_number': 1, 'item_code': '1-2', 'name': '要素と表示', 'estimated_hours': 2.0, 'estimated_days': 2, 'order': 4},
            {'phase_number': 1, 'item_code': '1-3', 'name': 'flexbox', 'estimated_hours': 2.0, 'estimated_days': None, 'order': 5},
            {'phase_number': 1, 'item_code': '1-4', 'name': '画面とリンク', 'estimated_hours': 1.0, 'estimated_days': None, 'order': 6},
            {'phase_number': 1, 'item_code': '1-5', 'name': 'ヘッダー作成', 'estimated_hours': 2.0, 'estimated_days': 2, 'order': 7},
            {'phase_number': 1, 'item_code': '1-6', 'name': 'テスト', 'estimated_hours': 2.0, 'estimated_days': None, 'order': 8},
            
            # Phase 2: フロントエンド基礎2
            {'phase_number': 2, 'item_code': '2-A', 'name': 'JavaScript入門', 'estimated_hours': 3.0, 'estimated_days': 1, 'order': 1},
            {'phase_number': 2, 'item_code': '2-B', 'name': 'jQuery (クリック)', 'estimated_hours': 1.0, 'estimated_days': 1, 'order': 2},
            {'phase_number': 2, 'item_code': '2-C', 'name': 'イベント', 'estimated_hours': 2.0, 'estimated_days': 1, 'order': 3},
            {'phase_number': 2, 'item_code': '2-D', 'name': 'カウンター', 'estimated_hours': 3.0, 'estimated_days': 1, 'order': 4},
            {'phase_number': 2, 'item_code': '2-E', 'name': '値の判定 (if文)', 'estimated_hours': 3.0, 'estimated_days': 2, 'order': 5},
            {'phase_number': 2, 'item_code': '2-F', 'name': 'アニメーション', 'estimated_hours': 3.0, 'estimated_days': 2, 'order': 6},
            {'phase_number': 2, 'item_code': '2-G', 'name': 'フェードアウト', 'estimated_hours': 4.0, 'estimated_days': 2, 'order': 7},
            {'phase_number': 2, 'item_code': '2-H', 'name': 'テスト', 'estimated_hours': 2.0, 'estimated_days': 1, 'order': 8},
            
            # Phase 3: フロントエンド実践
            {'phase_number': 3, 'item_code': '3-A', 'name': 'レイアウト', 'estimated_hours': 8.0, 'estimated_days': 1, 'order': 1},
            {'phase_number': 3, 'item_code': '3-B', 'name': 'サンプルサイト作成1', 'estimated_hours': 40.0, 'estimated_days': 5, 'order': 2},
            {'phase_number': 3, 'item_code': '3-C', 'name': 'サンプルサイト作成2', 'estimated_hours': 16.0, 'estimated_days': 2, 'order': 3},
            {'phase_number': 3, 'item_code': '3-D', 'name': 'サンプルサイト作成3', 'estimated_hours': 56.0, 'estimated_days': 7, 'order': 4},
            
            # Phase 4: サーバーサイド基礎1
            {'phase_number': 4, 'item_code': '4-A', 'name': '開発環境構築', 'estimated_hours': 6.0, 'estimated_days': 3, 'order': 1},
            {'phase_number': 4, 'item_code': '4-B', 'name': 'PHP基礎', 'estimated_hours': 15.0, 'estimated_days': 5, 'order': 2},
            {'phase_number': 4, 'item_code': '4-C', 'name': '制御構造', 'estimated_hours': 9.0, 'estimated_days': 3, 'order': 3},
            {'phase_number': 4, 'item_code': '4-D', 'name': '関数と引数', 'estimated_hours': 24.0, 'estimated_days': 8, 'order': 4},
            {'phase_number': 4, 'item_code': '4-E', 'name': 'エラー処理', 'estimated_hours': 30.0, 'estimated_days': 11, 'order': 5},
            {'phase_number': 4, 'item_code': '4-F', 'name': 'アルゴリズム', 'estimated_hours': 2.0, 'estimated_days': 1, 'order': 6},
            {'phase_number': 4, 'item_code': '4-G', 'name': 'フォーム作成', 'estimated_hours': 2.0, 'estimated_days': 2, 'order': 7},
            {'phase_number': 4, 'item_code': '4-H', 'name': 'テスト', 'estimated_hours': 2.0, 'estimated_days': 2, 'order': 8},
            
            # Phase 5: サーバーサイド基礎2
            {'phase_number': 5, 'item_code': '5-A', 'name': 'DB基礎 (SQL)', 'estimated_hours': 5.0, 'estimated_days': 2, 'order': 1},
            {'phase_number': 5, 'item_code': '5-B', 'name': '講座 (DB)', 'estimated_hours': 18.0, 'estimated_days': 6, 'order': 2},
            {'phase_number': 5, 'item_code': '5-C', 'name': '課題 (SQL)', 'estimated_hours': 29.0, 'estimated_days': 10, 'order': 3},
            {'phase_number': 5, 'item_code': '5-D', 'name': 'フォーム(CRUD)', 'estimated_hours': 2.0, 'estimated_days': 1, 'order': 4},
            {'phase_number': 5, 'item_code': '5-E', 'name': 'テスト', 'estimated_hours': 2.0, 'estimated_days': 1, 'order': 5},
            
            # Phase 6: サーバーサイド実践
            {'phase_number': 6, 'item_code': '6-A', 'name': 'Laravel', 'estimated_hours': 12.0, 'estimated_days': 4, 'order': 1},
            {'phase_number': 6, 'item_code': '6-B', 'name': '環境構築', 'estimated_hours': 21.0, 'estimated_days': 7, 'order': 2},
            {'phase_number': 6, 'item_code': '6-C', 'name': 'SELECT', 'estimated_hours': 15.0, 'estimated_days': 5, 'order': 3},
            {'phase_number': 6, 'item_code': '6-D', 'name': 'INSERT', 'estimated_hours': 15.0, 'estimated_days': 5, 'order': 4},
            {'phase_number': 6, 'item_code': '6-E', 'name': 'UPDATE', 'estimated_hours': 15.0, 'estimated_days': 5, 'order': 5},
            {'phase_number': 6, 'item_code': '6-F', 'name': 'DELETE', 'estimated_hours': 18.0, 'estimated_days': 6, 'order': 6},
            {'phase_number': 6, 'item_code': '6-G', 'name': 'バリデーション', 'estimated_hours': 15.0, 'estimated_days': 3, 'order': 7},
            {'phase_number': 6, 'item_code': '6-H', 'name': 'エラーハンドリング', 'estimated_hours': 18.0, 'estimated_days': 6, 'order': 8},
            
            # Phase 7: WEBシステム自作
            {'phase_number': 7, 'item_code': '7-A', 'name': 'Git & Docker', 'estimated_hours': 27.0, 'estimated_days': 9, 'order': 1},
            {'phase_number': 7, 'item_code': '7-B', 'name': '設計', 'estimated_hours': 84.0, 'estimated_days': 28, 'order': 2},
            {'phase_number': 7, 'item_code': '7-C', 'name': '製造', 'estimated_hours': 3.0, 'estimated_days': 1, 'order': 3},
            {'phase_number': 7, 'item_code': '7-D', 'name': '発表', 'estimated_hours': 3.0, 'estimated_days': 1, 'order': 4},
        ]
        
        # カリキュラム項目を作成
        for item_data in curriculum_items:
            phase = Phase.objects.get(phase_number=item_data['phase_number'])
            
            item, created = CurriculumItem.objects.get_or_create(
                phase=phase,
                item_code=item_data['item_code'],
                defaults={
                    'name': item_data['name'],
                    'estimated_hours': item_data['estimated_hours'],
                    'estimated_days': item_data['estimated_days'],
                    'order': item_data['order'],
                }
            )
            
            if created:
                self.stdout.write(f'  {item.item_code}: {item.name} を作成しました')
        
        self.stdout.write(
            self.style.SUCCESS('カリキュラムデータの投入が完了しました！')
        )