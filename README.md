# 研修生進捗確認アプリ

Nexterカリキュラムの進捗管理・分析・グループ競争促進を目的とした研修進捗管理システム

## 🎯 概要

- **対象ユーザー**: 研修生40名 + 管理者10名
- **技術スタック**: Django(Python), TailwindCSS, SQLite
- **開発期間**: 6ヶ月（3段階リリース）

## ⚡ クイックスタート（GitHub Codespaces）

1. **環境セットアップ**
```bash
# 依存関係のインストール
pip install -r requirements.txt

# データベースマイグレーション
python manage.py migrate

# カリキュラムデータ投入
python manage.py load_curriculum

# 管理者ユーザー作成
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('管理者ユーザーを作成しました: admin / admin123')
else:
    print('管理者ユーザーは既に存在します')
"

# 開発サーバー起動
python manage.py runserver
```

2. **アクセス**
- アプリケーション: http://localhost:8000/
- 管理画面: http://localhost:8000/admin/
- 管理者: admin / admin123

## 🚀 主な機能

### 研修生機能
- ✅ 詳細な進捗記録フォーム
- ✅ ダッシュボード（進捗表示、階級、統計）
- ✅ カリキュラム進捗可視化
- ✅ 階級システム（S〜D級）

### 管理者機能
- ✅ 管理者ダッシュボード
- ✅ 階級分布表示
- ✅ 最近の進捗確認
- ✅ Django管理画面連携

### カリキュラム構造
- **Phase 1**: フロントエンド基礎1 (7日)
- **Phase 2**: フロントエンド基礎2 (7日)
- **Phase 3**: フロントエンド実践 (16日)
- **Phase 4**: サーバーサイド基礎1 (30日)
- **Phase 5**: サーバーサイド基礎2 (18日)
- **Phase 6**: サーバーサイド実践 (32日)
- **Phase 7**: WEBシステム自作 (40日)

## 🎮 階級システム

- **S級**: 120日以内完了（プラチナエフェクト）
- **A級**: 150日以内完了（ゴールドエフェクト）
- **B級**: 180日以内完了（シルバーエフェクト）
- **C級**: 210日以内完了（ブロンズエフェクト）
- **D級**: 210日超過（グレーアウト・警告）

## 📊 実装状況

### Phase 1 完了 ✅
- [x] データベース設計・実装
- [x] ユーザー認証・権限管理
- [x] TailwindCSSセットアップ
- [x] 基本UI実装
- [x] カリキュラムデータ完全投入（47項目）

### Phase 2 予定
- [ ] Slack連携機能
- [ ] グループランキング詳細
- [ ] アラート・通知システム
- [ ] 詳細分析機能

### Phase 3 予定
- [ ] AI分析機能
- [ ] 高度な予測アルゴリズム
- [ ] 自動レポート生成

## 🛠️ 開発者向け

### 主要ファイル構造
```
student-progress-app/
├── manage.py
├── requirements.txt
├── CLAUDE.md                    # 開発進捗記録
├── student_progress_project/    # Django設定
├── progress/                    # メインアプリ
│   ├── models.py               # データベースモデル
│   ├── views.py                # ビュー
│   ├── forms.py                # フォーム
│   ├── admin.py                # 管理画面設定
│   ├── templates/              # HTMLテンプレート
│   └── management/commands/    # カスタムコマンド
└── README.md
```

### カスタムコマンド
```bash
# カリキュラムデータ投入
python manage.py load_curriculum
```

## 📱 スクリーンショット

（実際のスクリーンショットはCodespaces起動後に追加）

---

**開発者**: Claude Code  
**最終更新**: 2024年6月14日