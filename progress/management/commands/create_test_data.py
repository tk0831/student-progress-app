from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import date, timedelta
import random
from progress.models import Group, Phase, CurriculumItem, DailyProgress, UserStats

User = get_user_model()

class Command(BaseCommand):
    help = 'Create test data for demonstration'

    def handle(self, *args, **options):
        self.stdout.write('テストデータを作成中...')

        # 1. テストグループを作成
        groups_data = [
            {'name': 'チーム A', 'description': 'フロントエンド重点グループ'},
            {'name': 'チーム B', 'description': 'バックエンド重点グループ'},
            {'name': 'チーム C', 'description': 'フルスタック学習グループ'},
        ]

        groups = []
        for group_data in groups_data:
            group, created = Group.objects.get_or_create(
                name=group_data['name'],
                defaults={'description': group_data['description']}
            )
            groups.append(group)
            if created:
                self.stdout.write(f'✅ グループ「{group.name}」を作成')

        # 2. テスト研修生を作成（階級分布を考慮）
        students_data = [
            # S級グループ (120日以内で完了見込み) - 高パフォーマンス
            {'username': 'yamada_taro', 'first_name': '山田', 'last_name': '太郎', 'email': 'yamada@example.com', 'group': groups[0], 'days_progress': 60, 'performance': 'high'},
            {'username': 'sato_hanako', 'first_name': '佐藤', 'last_name': '花子', 'email': 'sato@example.com', 'group': groups[0], 'days_progress': 50, 'performance': 'high'},
            
            # A級グループ (150日以内で完了見込み) - 中パフォーマンス
            {'username': 'tanaka_ichiro', 'first_name': '田中', 'last_name': '一郎', 'email': 'tanaka@example.com', 'group': groups[0], 'days_progress': 85, 'performance': 'medium'},
            {'username': 'watanabe_jiro', 'first_name': '渡辺', 'last_name': '次郎', 'email': 'watanabe@example.com', 'group': groups[1], 'days_progress': 90, 'performance': 'medium'},
            
            # B級グループ (180日以内で完了見込み) - 中低パフォーマンス
            {'username': 'ito_yuki', 'first_name': '伊藤', 'last_name': '雪', 'email': 'ito@example.com', 'group': groups[1], 'days_progress': 120, 'performance': 'medium_low'},
            {'username': 'kobayashi_ken', 'first_name': '小林', 'last_name': '健', 'email': 'kobayashi@example.com', 'group': groups[1], 'days_progress': 125, 'performance': 'medium_low'},
            
            # C級グループ (210日以内で完了見込み) - 低パフォーマンス
            {'username': 'kato_miki', 'first_name': '加藤', 'last_name': '美樹', 'email': 'kato@example.com', 'group': groups[2], 'days_progress': 150, 'performance': 'low'},
            {'username': 'hayashi_shin', 'first_name': '林', 'last_name': '慎', 'email': 'hayashi@example.com', 'group': groups[2], 'days_progress': 155, 'performance': 'low'},
            
            # D級グループ (210日超過見込み) - 非常に低パフォーマンス
            {'username': 'nakamura_ai', 'first_name': '中村', 'last_name': '愛', 'email': 'nakamura@example.com', 'group': groups[2], 'days_progress': 180, 'performance': 'very_low'},
            {'username': 'takahashi_ryo', 'first_name': '高橋', 'last_name': '涼', 'email': 'takahashi@example.com', 'group': groups[2], 'days_progress': 190, 'performance': 'very_low'},
        ]

        # Phase・項目データを取得
        phases = list(Phase.objects.all().order_by('phase_number'))
        all_items = list(CurriculumItem.objects.all().order_by('phase__phase_number', 'order'))

        students = []
        for student_data in students_data:
            user, created = User.objects.get_or_create(
                username=student_data['username'],
                defaults={
                    'first_name': student_data['first_name'],
                    'last_name': student_data['last_name'],
                    'email': student_data['email'],
                    'user_type': 'student',
                    'group': student_data['group'],
                    'start_date': date.today() - timedelta(days=student_data['days_progress'])
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'✅ 研修生「{user.username}」を作成')
            
            students.append({
                'user': user,
                'days_progress': student_data['days_progress'],
                'performance': student_data['performance']
            })

        # 3. 進捗データを作成
        for student_info in students:
            user = student_info['user']
            days_progress = student_info['days_progress']
            performance = student_info['performance']
            
            # パフォーマンスレベルに応じた設定
            if performance == 'high':
                daily_hours_range = (3.0, 6.0)
                skip_probability = 0.05  # 5%の確率で記録なし
                current_phase_progress = min(7, (days_progress // 18) + 1)  # 早めに進行
                progress_multiplier = 1.4  # 高速進行
            elif performance == 'medium':
                daily_hours_range = (2.0, 4.5)
                skip_probability = 0.15  # 15%の確率で記録なし
                current_phase_progress = min(7, (days_progress // 22) + 1)  # 標準的進行
                progress_multiplier = 1.0  # 標準進行
            elif performance == 'medium_low':
                daily_hours_range = (1.5, 3.5)
                skip_probability = 0.20  # 20%の確率で記録なし
                current_phase_progress = min(7, (days_progress // 30) + 1)  # やや遅い進行
                progress_multiplier = 0.75  # やや遅い進行
            elif performance == 'low':
                daily_hours_range = (1.0, 3.0)
                skip_probability = 0.25  # 25%の確率で記録なし
                current_phase_progress = min(7, (days_progress // 40) + 1)  # 遅い進行
                progress_multiplier = 0.6  # 遅い進行
            else:  # very_low
                daily_hours_range = (0.5, 2.5)
                skip_probability = 0.30  # 30%の確率で記録なし
                current_phase_progress = min(7, (days_progress // 50) + 1)  # 非常に遅い進行
                progress_multiplier = 0.4  # 非常に遅い進行

            # 現在のPhaseと項目を決定
            current_phase = phases[current_phase_progress - 1]
            phase_items = [item for item in all_items if item.phase == current_phase]
            current_item = random.choice(phase_items) if phase_items else all_items[0]

            # 過去の進捗データを作成
            start_date = user.start_date
            total_hours = 0
            
            for i in range(days_progress):
                record_date = start_date + timedelta(days=i)
                
                # 一定確率で記録をスキップ
                if random.random() < skip_probability:
                    continue
                
                # その日の学習時間
                study_hours = round(random.uniform(*daily_hours_range), 1)
                total_hours += study_hours
                
                # 終了見込み日数に応じた階級計算
                days_elapsed = i + 1
                
                # 実際の進捗に基づく階級計算
                # 進捗に応じたPhase計算  
                actual_phase_num = min(7, max(1, (days_elapsed // (150 // 7)) + 1))
                actual_progress_rate = (actual_phase_num - 1) / 6.0  # 0-1の範囲
                
                # パフォーマンス別の実際の進捗調整
                if performance == 'high':
                    adjusted_progress = actual_progress_rate * 1.2  # 120%の進捗
                elif performance == 'medium':
                    adjusted_progress = actual_progress_rate * 1.0  # 100%の進捗
                elif performance == 'medium_low':
                    adjusted_progress = actual_progress_rate * 0.8  # 80%の進捗
                elif performance == 'low':
                    adjusted_progress = actual_progress_rate * 0.6  # 60%の進捗
                else:  # very_low
                    adjusted_progress = actual_progress_rate * 0.4  # 40%の進捗
                
                # 推定完了日数の計算
                if adjusted_progress > 0:
                    estimated_completion = days_elapsed / adjusted_progress
                else:
                    estimated_completion = 300  # 進捗がない場合は300日と設定
                
                # 終了見込み日数で階級決定
                if estimated_completion <= 120:
                    grade = 'S'
                elif estimated_completion <= 150:
                    grade = 'A'
                elif estimated_completion <= 180:
                    grade = 'B'
                elif estimated_completion <= 210:
                    grade = 'C'
                else:
                    grade = 'D'

                # 進捗に応じたPhase・項目
                progress_phase_num = min(7, max(1, (days_elapsed // (150 // 7)) + 1))
                progress_phase = phases[progress_phase_num - 1]
                phase_items = [item for item in all_items if item.phase == progress_phase]
                progress_item = random.choice(phase_items) if phase_items else all_items[0]

                # サンプル振り返りコメント
                reflections = [
                    "今日は理解が深まった。明日も頑張りたい。",
                    "少し難しい内容だったが、繰り返し学習して理解できた。",
                    "実装でつまずいたが、調べながら解決できた。",
                    "新しい概念を学び、興味深かった。",
                    "復習をしっかり行い、知識が定着した。",
                    "課題に時間がかかったが、最終的に完成できた。",
                ]
                
                goals = [
                    "明日は次の単元に進む。",
                    "今日の内容を復習してから先に進む。",
                    "実践的な課題に取り組む。",
                    "理解不足の部分を重点的に学習する。",
                    "新しい技術について調べる。",
                ]

                actions = [
                    "コードを書いて実践的に学ぶ。",
                    "ドキュメントを読んで理解を深める。",
                    "サンプルコードを写経する。",
                    "疑問点を整理して質問する。",
                    "復習ノートを作成する。",
                ]

                # 進捗記録を作成
                progress, created = DailyProgress.objects.get_or_create(
                    user=user,
                    date=record_date,
                    defaults={
                        'current_phase': progress_phase,
                        'current_item': progress_item,
                        'study_hours': study_hours,
                        'current_grade': grade,
                        'days_elapsed': days_elapsed,
                        'delay_days': max(0, days_elapsed - 150) if days_elapsed > 150 else 0,
                        'reflection': random.choice(reflections),
                        'next_goal': random.choice(goals),
                        'action_plan': random.choice(actions),
                        'planned_hours': round(random.uniform(2.0, 4.0), 1),
                        'feedback_requested': random.random() < 0.1,  # 10%の確率
                        'need_review': random.random() < 0.3,  # 30%の確率
                        'have_question': random.random() < 0.2,  # 20%の確率
                    }
                )

            # 最終的な階級を計算（終了見込みベース）
            final_actual_phase_num = min(7, max(1, (days_progress // (150 // 7)) + 1))
            final_actual_progress_rate = (final_actual_phase_num - 1) / 6.0  # 0-1の範囲
            
            # パフォーマンス別の最終進捗調整
            if performance == 'high':
                final_adjusted_progress = final_actual_progress_rate * 1.2
            elif performance == 'medium':
                final_adjusted_progress = final_actual_progress_rate * 1.0
            elif performance == 'medium_low':
                final_adjusted_progress = final_actual_progress_rate * 0.8
            elif performance == 'low':
                final_adjusted_progress = final_actual_progress_rate * 0.6
            else:  # very_low
                final_adjusted_progress = final_actual_progress_rate * 0.4
            
            if final_adjusted_progress > 0:
                final_estimated = days_progress / final_adjusted_progress
            else:
                final_estimated = 300
            
            if final_estimated <= 120:
                final_grade = 'S'
            elif final_estimated <= 150:
                final_grade = 'A'
            elif final_estimated <= 180:
                final_grade = 'B'
            elif final_estimated <= 210:
                final_grade = 'C'
            else:
                final_grade = 'D'

            # UserStatsを更新
            user_stats, created = UserStats.objects.get_or_create(
                user=user,
                defaults={
                    'total_study_hours': total_hours,
                    'current_phase': current_phase,
                    'current_item': current_item,
                    'current_grade': final_grade,
                    'days_elapsed': days_progress,
                    'delay_days': max(0, days_progress - 150) if days_progress > 150 else 0,
                    'completion_rate': round(final_adjusted_progress * 100, 1),
                }
            )
            
            if not created:
                user_stats.total_study_hours = total_hours
                user_stats.current_phase = current_phase
                user_stats.current_item = current_item
                user_stats.current_grade = final_grade
                user_stats.days_elapsed = days_progress
                user_stats.delay_days = max(0, days_progress - 150) if days_progress > 150 else 0
                user_stats.completion_rate = round(final_adjusted_progress * 100, 1)
                user_stats.save()

            self.stdout.write(f'✅ {user.username}の進捗データ（{days_progress}日分）を作成')

        self.stdout.write(
            self.style.SUCCESS(
                '\n🎉 テストデータの作成が完了しました！\n'
                '以下のアカウントでログインして確認してください：\n'
                '管理者: admin / admin123\n'
                '研修生例: yamada_taro / password123\n'
                'URL: http://localhost:8000'
            )
        )