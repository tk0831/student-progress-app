from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from progress.models import Group, Phase, CurriculumItem, DailyProgress, UserStats
from datetime import date, timedelta
import random

User = get_user_model()

class Command(BaseCommand):
    help = '多様な進捗状況のテストデータを作成します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='既存のテストデータを削除してから作成'
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('既存のテストデータを削除中...'))
            # 既存の研修生データを削除（adminは除く）
            User.objects.filter(user_type='student').exclude(username__in=['admin', 'training_admin']).delete()
            self.stdout.write(self.style.SUCCESS('削除完了'))

        # グループが存在しない場合は作成
        groups = []
        for group_name in ['チーム Alpha', 'チーム Beta', 'チーム Gamma', 'チーム Delta']:
            group, created = Group.objects.get_or_create(
                name=group_name,
                defaults={'description': f'{group_name}の説明'}
            )
            groups.append(group)

        # 多様なテストユーザーデータ
        test_users = [
            # S級ユーザー（先行中）
            {
                'username': 'ace_student', 'first_name': '優秀', 'last_name': '研修生',
                'start_date': date.today() - timedelta(days=20),
                'current_phase': 4, 'current_item': '4-1', 'item_order': 2,
                'group': groups[0]
            },
            {
                'username': 'fast_learner', 'first_name': '高速', 'last_name': '学習者',
                'start_date': date.today() - timedelta(days=15),
                'current_phase': 3, 'current_item': '3-2', 'item_order': 4,
                'group': groups[0]
            },
            
            # A級ユーザー（順調）
            {
                'username': 'steady_worker', 'first_name': '着実', 'last_name': '作業者',
                'start_date': date.today() - timedelta(days=30),
                'current_phase': 3, 'current_item': '3-3', 'item_order': 5,
                'group': groups[1]
            },
            {
                'username': 'good_pace', 'first_name': '良好', 'last_name': 'ペース',
                'start_date': date.today() - timedelta(days=25),
                'current_phase': 3, 'current_item': '3-1', 'item_order': 3,
                'group': groups[1]
            },
            
            # B級ユーザー（やや遅れ）
            {
                'username': 'average_student', 'first_name': '平均的', 'last_name': '生徒',
                'start_date': date.today() - timedelta(days=35),
                'current_phase': 2, 'current_item': '2-6', 'item_order': 8,
                'group': groups[2]
            },
            {
                'username': 'slow_but_steady', 'first_name': '遅いが', 'last_name': '着実',
                'start_date': date.today() - timedelta(days=40),
                'current_phase': 3, 'current_item': '3-A', 'item_order': 1,
                'group': groups[2]
            },
            
            # C級ユーザー（遅れ気味）
            {
                'username': 'struggling_student', 'first_name': '苦戦中', 'last_name': '学生',
                'start_date': date.today() - timedelta(days=50),
                'current_phase': 2, 'current_item': '2-3', 'item_order': 5,
                'group': groups[3]
            },
            {
                'username': 'needs_help', 'first_name': 'サポート', 'last_name': '必要',
                'start_date': date.today() - timedelta(days=45),
                'current_phase': 2, 'current_item': '2-2', 'item_order': 4,
                'group': groups[3]
            },
            
            # 新入生（開始したばかり）
            {
                'username': 'new_starter1', 'first_name': '新人1', 'last_name': '号',
                'start_date': date.today() - timedelta(days=5),
                'current_phase': 1, 'current_item': '1-4', 'item_order': 6,
                'group': groups[0]
            },
            {
                'username': 'new_starter2', 'first_name': '新人2', 'last_name': '号',
                'start_date': date.today() - timedelta(days=3),
                'current_phase': 1, 'current_item': '1-2', 'item_order': 4,
                'group': groups[1]
            },
        ]

        created_count = 0
        
        with transaction.atomic():
            for user_data in test_users:
                # ユーザー作成
                user, created = User.objects.get_or_create(
                    username=user_data['username'],
                    defaults={
                        'first_name': user_data['first_name'],
                        'last_name': user_data['last_name'],
                        'user_type': 'student',
                        'start_date': user_data['start_date'],
                        'group': user_data['group']
                    }
                )
                
                if created:
                    user.set_password('password123')
                    user.save()
                    created_count += 1

                # Phase と CurriculumItem を取得
                try:
                    phase = Phase.objects.get(phase_number=user_data['current_phase'])
                    current_item = CurriculumItem.objects.get(
                        phase=phase,
                        item_code=user_data['current_item']
                    )
                except (Phase.DoesNotExist, CurriculumItem.objects.DoesNotExist):
                    self.stdout.write(
                        self.style.ERROR(f'Phase {user_data["current_phase"]} または項目 {user_data["current_item"]} が見つかりません')
                    )
                    continue

                # 進捗記録作成（最新の進捗のみ）
                latest_date = user_data['start_date'] + timedelta(days=random.randint(1, 5))
                
                study_hours = random.uniform(3.0, 8.0)
                planned_hours = random.uniform(4.0, 9.0)
                
                progress, created = DailyProgress.objects.get_or_create(
                    user=user,
                    date=latest_date,
                    defaults={
                        'current_phase': phase,
                        'current_item': current_item,
                        'study_hours': study_hours,
                        'planned_hours': planned_hours,
                        'progress_detail': f'{current_item.name}を学習中',
                        'reflection': '順調に進んでいます',
                        'next_goal': '明日も頑張ります',
                        'action_plan': '復習と新しい内容の学習',
                        'days_elapsed': (latest_date - user.start_date).days + 1,
                        'current_grade': 'A',  # 仮の値、後で更新される
                    }
                )

                # UserStats作成・更新
                user_stats, stats_created = UserStats.objects.get_or_create(
                    user=user,
                    defaults={
                        'current_phase': phase,
                        'current_item': current_item,
                        'total_study_hours': random.uniform(10.0, 100.0)
                    }
                )
                
                # 統計情報を更新
                user_stats.current_phase = phase
                user_stats.current_item = current_item
                user_stats.update_all_stats()

                self.stdout.write(f'✓ {user.username} ({user.first_name} {user.last_name}) - {user_stats.current_grade}級')

        self.stdout.write(
            self.style.SUCCESS(f'\n多様なテストデータ作成完了: {created_count}名の新しいユーザーを作成しました')
        )
        
        # 階級分布を表示
        self.stdout.write('\n=== 階級分布 ===')
        grade_stats = {}
        for stats in UserStats.objects.all():
            grade = stats.current_grade
            grade_stats[grade] = grade_stats.get(grade, 0) + 1
        
        for grade in ['S', 'A', 'B', 'C', 'D']:
            count = grade_stats.get(grade, 0)
            self.stdout.write(f'{grade}級: {count}名')