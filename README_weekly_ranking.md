# 週間ランキング機能 - 実装ガイド

## 🏆 機能概要

研修生の一週間の進捗を評価し、上位3位を表彰するランキング機能です。

### 評価基準（優先順）
1. **完了項目の標準日数合計** - 今週完了した項目の標準日数の合計
2. **進捗効率スコア** - 標準日数 ÷ 実際日数の平均値
3. **総学習時間** - 今週の総学習時間

### 表示仕様
- 上位3位のみ記録・表示
- 受賞した本人のみに表示（他の研修生には見えない）
- 受賞した次の週から表示される

## 📝 実装済み機能

### 1. データベース拡張
- `DailyProgress.item_completed` - 項目完了フラグ
- `WeeklyRanking` - 週間ランキング記録テーブル

### 2. 項目完了判定
- 手動: 進捗記録フォームの「項目完了」チェックボックス
- 自動: 次の項目に進んだ際に前の項目を自動完了

### 3. ランキング計算
- `calculate_weekly_ranking()` 関数でランキング算出
- 毎週の月曜〜日曜を対象期間として計算

### 4. 個人ダッシュボード表示
- 受賞歴が過去4週間分表示される
- ランキングウィジェットで美しく表示

## 🚀 セットアップ手順

### 1. データベースマイグレーション実行

```bash
cd /path/to/student-progress-app
python manage.py migrate
```

### 2. 週間ランキング自動実行設定

#### 手動実行（テスト用）
```bash
# ドライラン（実際の処理は行わない）
python manage.py weekly_tasks --dry-run

# 実際にランキング計算を実行
python manage.py calculate_weekly_ranking
```

#### 自動実行設定（cron）
```bash
# cron設定を開く
crontab -e

# 以下の行を追加（毎週日曜日23:00に実行）
0 23 * * 0 cd /path/to/student-progress-app && /usr/bin/python3 manage.py weekly_tasks

# ログ出力付きの場合
0 23 * * 0 cd /path/to/student-progress-app && /usr/bin/python3 manage.py weekly_tasks >> /var/log/weekly_ranking.log 2>&1
```

### 3. 個人ダッシュボードにランキング表示追加

`progress/templates/progress/student_dashboard.html` に以下を追加：

```html
<!-- 基本統計の後に追加 -->
{% include 'progress/components/weekly_ranking_widget.html' %}
```

## 🎯 使用方法

### 研修生側
1. 日々の進捗記録で「項目完了」をチェック
2. または次の項目に進むと自動で前の項目が完了扱い
3. 受賞した場合、翌週から個人ダッシュボードにランキングが表示

### 管理者側
1. 週次でランキング計算が自動実行される
2. 手動実行も可能：`python manage.py calculate_weekly_ranking`

## 📊 ランキング算出例

```
田中さん（今週）:
- 項目A完了（標準5日） + 項目B完了（標準3日） = 8日分
- 効率: (5÷3 + 3÷3) ÷ 2 = 1.33
- 学習時間: 35時間

佐藤さん（今週）:
- 項目C完了（標準8日） = 8日分  
- 効率: 8÷6 = 1.33
- 学習時間: 40時間

→ 同じ標準日数、同じ効率なら学習時間で佐藤さんが1位
```

## 🔧 カスタマイズ

### 評価基準の変更
`views.py` の `calculate_weekly_ranking()` 関数内のソート条件を変更：

```python
ranking_data.sort(key=lambda x: (
    -x['total_standard_days'],  # 標準日数：多い順
    -x['avg_efficiency'],       # 効率：高い順  
    -x['total_study_hours']     # 学習時間：多い順
))
```

### 表示期間の変更
`get_user_weekly_rankings()` 関数の週数を変更：

```python
for week_offset in range(4):  # 4週間 → お好みの週数
```

## 🐛 トラブルシューティング

### ランキングが表示されない
1. マイグレーションが実行されているか確認
2. 週次タスクが実行されているか確認
3. 該当週に項目完了があるか確認

### 自動実行されない
1. cron設定を確認：`crontab -l`
2. パスが正しいか確認
3. 権限が適切か確認

### データの整合性確認
```bash
python manage.py shell
>>> from progress.models import WeeklyRanking
>>> WeeklyRanking.objects.all()
```

## 📈 今後の拡張予定

- 月間ランキング
- チーム対抗戦
- 個人成長レポート
- ランキング通知機能