#!/bin/bash

# 週間ランキング自動実行のためのcron設定スクリプト

echo "🔧 週間ランキング自動実行のcron設定"

# プロジェクトのパスを設定（実際の環境に合わせて変更してください）
PROJECT_PATH="/path/to/student-progress-app"
PYTHON_PATH="/path/to/venv/bin/python"  # 仮想環境のPythonパス

# cron設定の確認
echo "現在のcron設定："
crontab -l

echo ""
echo "追加する設定："
echo "# 週間ランキング計算（毎週日曜日の23:00に実行）"
echo "0 23 * * 0 cd $PROJECT_PATH && $PYTHON_PATH manage.py weekly_tasks"

echo ""
echo "⚠️  以下のコマンドでcron設定を追加してください："
echo ""
echo "1. crontab -e でcron設定を開く"
echo "2. 以下の行を追加："
echo "   0 23 * * 0 cd $PROJECT_PATH && $PYTHON_PATH manage.py weekly_tasks"
echo "3. 保存して終了"
echo ""
echo "📝 設定例（実際のパスに変更してください）："
echo "0 23 * * 0 cd /mnt/c/Users/tkygi/student-progress-app && /usr/bin/python3 manage.py weekly_tasks"
echo ""
echo "🧪 テスト実行："
echo "python manage.py weekly_tasks --dry-run"
echo "python manage.py calculate_weekly_ranking"
echo ""
echo "📊 ログ出力付きで実行する場合："
echo "0 23 * * 0 cd $PROJECT_PATH && $PYTHON_PATH manage.py weekly_tasks >> /var/log/weekly_ranking.log 2>&1"