#!/usr/bin/env python3
"""
週間ランキング機能の動作テストスクリプト
"""

import os
import sys
import django
from datetime import date, timedelta

# Django設定
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_progress_project.settings')
django.setup()

from progress.models import CustomUser, DailyProgress, WeeklyRanking, CurriculumItem
from progress.views import calculate_weekly_ranking

def test_database_status():
    """データベースの現在状況をテスト"""
    print("🔍 データベース状況確認")
    print("=" * 50)
    
    # 1. ユーザー数確認
    students = CustomUser.objects.filter(user_type='student')
    print(f"👥 研修生数: {students.count()}名")
    
    # 2. 進捗記録数確認
    total_progress = DailyProgress.objects.count()
    print(f"📝 総進捗記録数: {total_progress}件")
    
    # 3. 項目完了記録数確認
    completed_items = DailyProgress.objects.filter(item_completed=True)
    print(f"✅ 項目完了記録数: {completed_items.count()}件")
    
    # 4. 今週の進捗記録確認
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    
    this_week_progress = DailyProgress.objects.filter(
        date__gte=week_start,
        date__lte=week_end
    )
    print(f"📅 今週の進捗記録数: {this_week_progress.count()}件 ({week_start} - {week_end})")
    
    this_week_completed = DailyProgress.objects.filter(
        date__gte=week_start,
        date__lte=week_end,
        item_completed=True
    )
    print(f"🏆 今週の項目完了数: {this_week_completed.count()}件")
    
    # 5. カリキュラム項目確認
    curriculum_items = CurriculumItem.objects.count()
    print(f"📚 カリキュラム項目数: {curriculum_items}件")
    
    # 6. 既存のランキング記録確認
    existing_rankings = WeeklyRanking.objects.count()
    print(f"🏅 既存のランキング記録数: {existing_rankings}件")
    
    print()

def test_ranking_calculation():
    """ランキング計算機能をテスト"""
    print("🧮 ランキング計算テスト")
    print("=" * 50)
    
    try:
        # ランキング計算実行
        ranking_data = calculate_weekly_ranking()
        
        if ranking_data:
            print(f"✅ ランキング計算成功！上位{len(ranking_data)}名:")
            for i, data in enumerate(ranking_data, 1):
                print(f"  {i}位: {data['user'].username}")
                print(f"    - 完了項目標準日数: {data['total_standard_days']}日")
                print(f"    - 進捗効率: {data['avg_efficiency']:.2f}")
                print(f"    - 学習時間: {data['total_study_hours']}時間")
                print()
        else:
            print("⚠️  今週は項目完了者がいませんでした")
            
    except Exception as e:
        print(f"❌ ランキング計算でエラー: {str(e)}")
        import traceback
        traceback.print_exc()

def test_sample_data():
    """サンプルデータの存在確認"""
    print("📊 サンプルデータ確認")
    print("=" * 50)
    
    # 最新の進捗記録を確認
    recent_progress = DailyProgress.objects.order_by('-date')[:5]
    
    if recent_progress:
        print("📝 最新の進捗記録 (上位5件):")
        for progress in recent_progress:
            completed_mark = "✅" if progress.item_completed else "⏳"
            print(f"  {completed_mark} {progress.user.username} - {progress.date}")
            print(f"     項目: {progress.current_item.item_code}")
            print(f"     学習時間: {progress.study_hours}時間")
            print()
    else:
        print("❌ 進捗記録が見つかりません")

def test_user_rankings():
    """ユーザー別ランキング表示テスト"""
    print("👤 ユーザー別ランキング確認")
    print("=" * 50)
    
    # 各ユーザーのランキング記録を確認
    users_with_rankings = WeeklyRanking.objects.values('user__username').distinct()
    
    if users_with_rankings:
        for user_data in users_with_rankings:
            username = user_data['user__username']
            user_rankings = WeeklyRanking.objects.filter(
                user__username=username
            ).order_by('-week_start')
            
            print(f"🏆 {username}さんの受賞歴:")
            for ranking in user_rankings:
                print(f"  {ranking.rank}位 - {ranking.week_start}週")
                print(f"    完了項目: {ranking.completed_standard_days}日分")
                print(f"    効率: {ranking.efficiency_score}")
            print()
    else:
        print("📝 まだランキング記録がありません")

if __name__ == "__main__":
    print("🚀 週間ランキング機能 動作テスト開始")
    print("=" * 60)
    print()
    
    # 1. データベース状況確認
    test_database_status()
    
    # 2. サンプルデータ確認
    test_sample_data()
    
    # 3. ランキング計算テスト
    test_ranking_calculation()
    
    # 4. ユーザー別ランキング確認
    test_user_rankings()
    
    print("🎉 動作テスト完了！")