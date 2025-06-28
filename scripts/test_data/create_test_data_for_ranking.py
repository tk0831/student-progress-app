#!/usr/bin/env python3
"""
週間ランキングテスト用のサンプルデータ作成スクリプト
"""

import os
import sys
import django
from datetime import date, timedelta
from decimal import Decimal

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_progress_project.settings')
django.setup()

from progress.models import CustomUser, DailyProgress, CurriculumItem, Phase

def create_test_data():
    """ランキングテスト用のサンプルデータを作成"""
    print("📝 ランキングテスト用サンプルデータ作成開始")
    print("=" * 50)
    
    # 今週の日程を計算
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # 今週の月曜日
    
    # テスト用の研修生を取得（存在しない場合は作成）
    students = CustomUser.objects.filter(user_type='student')[:3]
    
    if students.count() < 3:
        print("❌ 研修生が3名未満です。先にテストユーザーを作成してください。")
        return
    
    # カリキュラム項目を取得
    curriculum_items = CurriculumItem.objects.all()[:5]  # 最初の5項目
    
    if curriculum_items.count() < 3:
        print("❌ カリキュラム項目が不足しています。先にカリキュラムデータを作成してください。")
        return
    
    print(f"👥 テスト対象研修生: {[s.username for s in students]}")
    print(f"📚 使用カリキュラム項目: {[item.item_code for item in curriculum_items]}")
    print()
    
    # 既存のテストデータをクリア
    DailyProgress.objects.filter(
        user__in=students,
        date__gte=week_start
    ).delete()
    
    # 学生1: 高成績（2項目完了、高効率）
    student1 = students[0]
    print(f"📊 {student1.username}さん（高成績想定）のデータ作成:")
    
    # 項目1: 標準5日を3日で完了
    item1 = curriculum_items[0]
    for day_offset in range(3):
        progress_date = week_start + timedelta(days=day_offset)
        is_completed = (day_offset == 2)  # 3日目に完了
        
        DailyProgress.objects.create(
            user=student1,
            date=progress_date,
            current_phase=item1.phase,
            current_item=item1,
            progress_detail=f"項目{item1.item_code}の学習",
            study_hours=Decimal('8.0'),
            reflection="順調に進んでいます",
            action_plan="明日も継続します",
            planned_hours=Decimal('8.0'),
            item_completed=is_completed,
            current_grade='A',
            days_elapsed=day_offset + 1
        )
        print(f"  {progress_date}: {item1.item_code} ({'完了' if is_completed else '学習中'})")
    
    # 項目2: 標準3日を2日で完了
    item2 = curriculum_items[1]
    for day_offset in range(2):
        progress_date = week_start + timedelta(days=day_offset + 3)
        is_completed = (day_offset == 1)  # 2日目に完了
        
        DailyProgress.objects.create(
            user=student1,
            date=progress_date,
            current_phase=item2.phase,
            current_item=item2,
            progress_detail=f"項目{item2.item_code}の学習",
            study_hours=Decimal('7.5'),
            reflection="効率よく進められました",
            action_plan="次の項目に進みます",
            planned_hours=Decimal('8.0'),
            item_completed=is_completed,
            current_grade='A',
            days_elapsed=day_offset + 4
        )
        print(f"  {progress_date}: {item2.item_code} ({'完了' if is_completed else '学習中'})")
    
    # 学生2: 中程度成績（1項目完了、標準的効率）
    student2 = students[1]
    print(f"\n📊 {student2.username}さん（中程度成績想定）のデータ作成:")
    
    # 項目1: 標準4日を4日で完了
    item3 = curriculum_items[2]
    for day_offset in range(4):
        progress_date = week_start + timedelta(days=day_offset)
        is_completed = (day_offset == 3)  # 4日目に完了
        
        DailyProgress.objects.create(
            user=student2,
            date=progress_date,
            current_phase=item3.phase,
            current_item=item3,
            progress_detail=f"項目{item3.item_code}の学習",
            study_hours=Decimal('6.0'),
            reflection="標準的なペースで進んでいます",
            action_plan="継続して頑張ります",
            planned_hours=Decimal('6.0'),
            item_completed=is_completed,
            current_grade='B',
            days_elapsed=day_offset + 1
        )
        print(f"  {progress_date}: {item3.item_code} ({'完了' if is_completed else '学習中'})")
    
    # 学生3: 低成績（項目完了なし）
    student3 = students[2]
    print(f"\n📊 {student3.username}さん（学習中、完了項目なし）のデータ作成:")
    
    # 項目1: まだ学習中
    item4 = curriculum_items[3]
    for day_offset in range(3):
        progress_date = week_start + timedelta(days=day_offset)
        
        DailyProgress.objects.create(
            user=student3,
            date=progress_date,
            current_phase=item4.phase,
            current_item=item4,
            progress_detail=f"項目{item4.item_code}の学習",
            study_hours=Decimal('4.5'),
            reflection="まだ理解が不十分です",
            action_plan="復習に時間をかけます",
            planned_hours=Decimal('5.0'),
            item_completed=False,  # まだ完了していない
            current_grade='C',
            days_elapsed=day_offset + 1
        )
        print(f"  {progress_date}: {item4.item_code} (学習中)")
    
    print(f"\n✅ テストデータ作成完了！")
    print(f"📅 対象期間: {week_start} - {week_start + timedelta(days=6)}")
    
    # 作成されたデータの要約
    total_progress = DailyProgress.objects.filter(
        user__in=students,
        date__gte=week_start
    ).count()
    
    completed_items = DailyProgress.objects.filter(
        user__in=students,
        date__gte=week_start,
        item_completed=True
    ).count()
    
    print(f"📝 作成された進捗記録: {total_progress}件")
    print(f"✅ 完了項目: {completed_items}件")
    
    # 期待されるランキング
    print(f"\n🏆 期待されるランキング:")
    print(f"  1位: {student1.username} (2項目完了、高効率)")
    print(f"  2位: {student2.username} (1項目完了、標準効率)")
    print(f"  3位: {student3.username} (完了項目なし)")

if __name__ == "__main__":
    create_test_data()