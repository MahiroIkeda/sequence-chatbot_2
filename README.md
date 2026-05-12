# シーケンス図ジェネレーター

## Why（なぜ作るか）

要件定義書からシーケンス図を手動で作成するのは時間がかかる。
AIを活用して自動生成することで開発効率を上げる。

仕様駆動開発の原則に基づき、本リポジトリでは仕様（このREADME.md）とコードを常に同期させて管理する。

## What（何をするか）

- `.txt` 形式の要件定義書をアップロードする
- Claude AIがMermaid記法のシーケンス図を自動生成する
- 生成した図をブラウザで表示・編集できる
- チャットで追加の修正依頼ができる

## 技術スタック

| 役割 | 技術 |
|------|------|
| Webサーバー | Python / Flask |
| AI | Anthropic Claude API |
| 図のレンダリング | Mermaid.js |
| フロントエンド | HTML / CSS / JavaScript |

## セットアップ

### 1. 必要なライブラリのインストール

```bash
pip install flask anthropic python-dotenv
```

### 2. APIキーの設定

`.env` ファイルをプロジェクトルートに作成し、以下を記述する：

```
ANTHROPIC_API_KEY=sk-ant-ここにAPIキーを貼り付ける
```

### 3. サーバーの起動

```bash
python app.py
```

### 4. ブラウザでアクセス

```
http://localhost:5000
```

## ファイル構成

```
sequence-chatbot/
├── README.md        # 仕様書（本ファイル）
├── app.py           # Flaskサーバー（APIキーを安全に管理）
├── .env             # APIキー（GitHubには公開しない）
├── .gitignore       # .envをGitの管理から除外
└── templates/
    └── index.html   # フロントエンド
```

## 変更履歴

| 日付 | 内容 |
|------|------|
| 2025-05 | 初版作成（AI支援による自動生成） |
