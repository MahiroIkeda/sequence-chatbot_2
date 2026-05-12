# sequence-chatbot_2

仕様駆動開発アシスタント **SpecFlow** によって管理されるリポジトリです。

## 仕様とコードの同期状態

| ドキュメント | 最終更新 |
|---|---|
| [仕様書](docs/specification.md) | 2026-05-12 19:30 |
| [シーケンス図](docs/sequence.md) | 2026-05-12 19:30 |

## セットアップ

```bash
pip install flask anthropic python-dotenv
python app.py
```

ブラウザで `http://localhost:5000` を開いてください。

## 仕様駆動開発の原則

- **原則1**: 仕様は"生きたドキュメント" — 継続的に更新される
- **原則2**: 仕様は"信頼できる唯一の情報源" — このリポジトリが基準
- **原則3**: 仕様は"変更と反復が前提" — Pull Requestで変更を追跡・承認
- **原則4**: AIでコストを抑える — SpecFlowがAI支援を提供

## ファイル構成

```
/
├── app.py                  # Flaskサーバー
├── templates/
│   └── index.html          # フロントエンド
├── docs/
│   ├── specification.md    # 仕様書（自動更新）
│   └── sequence.md         # シーケンス図（自動更新）
└── .env                    # APIキー（非公開）
```

## 研究背景

本ツールは池田眞浩（信州大学, 2025）の研究
「対象ドメイン定義に数学構造を含めてLLMに注入することによる推論性能の向上と検証」
の知見を実装に組み込んでいます。
