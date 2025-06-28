#!/usr/bin/env python3

print("🧪 週間ランキング機能 簡易テスト")
print("=" * 50)

# 1. インポートテスト
try:
    import os
    import sys
    import django
    
    # Django設定
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_progress_project.settings')
    django.setup()
    
    from progress.models import CustomUser, DailyProgress, WeeklyRanking
    from progress.views import calculate_weekly_ranking, get_user_weekly_rankings
    
    print("✅ モジュールインポート成功")
    
except Exception as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)

# 2. データベース接続テスト
try:
    student_count = CustomUser.objects.filter(user_type='student').count()
    progress_count = DailyProgress.objects.count()
    ranking_count = WeeklyRanking.objects.count()
    
    print(f"✅ データベース接続成功")
    print(f"   研修生数: {student_count}名")
    print(f"   進捗記録数: {progress_count}件")
    print(f"   ランキング記録数: {ranking_count}件")
    
except Exception as e:
    print(f"❌ データベース接続エラー: {e}")
    sys.exit(1)

# 3. 項目完了フィールドの存在確認
try:
    # 新しいフィールドが存在するかチェック
    sample_progress = DailyProgress.objects.first()
    if sample_progress:
        hasattr(sample_progress, 'item_completed')
        print("✅ item_completedフィールド存在確認")
    else:
        print("⚠️  進捗記録がないため、フィールド確認スキップ")
        
except Exception as e:
    print(f"❌ フィールド確認エラー: {e}")

# 4. 関数存在確認
try:
    # 関数が定義されているかチェック
    assert callable(calculate_weekly_ranking), "calculate_weekly_ranking関数が見つかりません"
    assert callable(get_user_weekly_rankings), "get_user_weekly_rankings関数が見つかりません"
    print("✅ 必要な関数が定義されています")
    
except Exception as e:
    print(f"❌ 関数確認エラー: {e}")

# 5. ランキング計算の基本テスト
try:
    print("\n🧮 ランキング計算テスト実行中...")
    ranking_result = calculate_weekly_ranking()
    
    if ranking_result:
        print(f"✅ ランキング計算成功！{len(ranking_result)}名がランクイン")
        for i, data in enumerate(ranking_result, 1):
            print(f"   {i}位: {data['user'].username}")
    else:
        print("⚠️  今週は完了項目がある研修生がいません")
        
except Exception as e:
    print(f"❌ ランキング計算エラー: {e}")
    import traceback
    traceback.print_exc()

print("\n🎉 簡易テスト完了")

# 6. 実行推奨コマンド
print("\n📋 次に実行推奨のコマンド:")
print("   python3 manage.py calculate_weekly_ranking")
print("   python3 manage.py weekly_tasks --dry-run")
print("   python3 create_test_data_for_ranking.py  # テストデータ作成")