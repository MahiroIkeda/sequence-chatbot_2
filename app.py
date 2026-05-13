"""
SpecFlow — 仕様駆動開発アシスタント
Flask サーバー
"""

from flask import Flask, request, jsonify, render_template
from anthropic import Anthropic
from dotenv import load_dotenv
import os
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime

load_dotenv()

app = Flask(__name__)

# ════════════════════════════════
#  定数
# ════════════════════════════════

MODEL = "claude-sonnet-4-5"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO  = os.getenv("GITHUB_REPO")
GITHUB_BASE  = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

GITHUB_HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "Content-Type": "application/json",
}

# ════════════════════════════════
#  システムプロンプト定数
# ════════════════════════════════

PROMPT_AMBIGUITY = """あなたはソフトウェア要求工学と形式手法の専門家です。
要件定義書の曖昧性を検出し、形式的定義で補完してください。

【検出する曖昧性の種類】
1. 主語の省略・指示語の多用（「それ」「この」「当該」）
2. 循環構造・境界条件の不明確さ（「最後の次」「端の場合」）
3. 終了条件・例外条件の欠落
4. 用語の揺れ（同一概念に複数の名称）
5. 暗黙の前提（記述されていない前提条件）
6. 数量・順序・方向の曖昧さ

【出力フォーマット】
## 曖昧性検出レポート
### 検出された曖昧箇所
各箇所について：
- **箇所**: 該当する文や表現
- **種別**: 上記1〜6のどれか
- **問題**: なぜ曖昧か
- **影響**: LLMが誤解しやすい理由

### 形式的定義による補完
曖昧箇所を形式的・数学的表現で明確化した定義を提示する。

### 補完済み要件定義書
形式的定義を組み込んだ改善版の要件定義書を全文で出力。

回答はすべて日本語で記述してください。"""

PROMPT_REVIEW = """あなたは仕様駆動開発の専門家です。要件定義書を以下の観点でレビューしてください。

【レビューの観点】
1. 明確性（Clarity）：曖昧な表現がないか
2. 完全性（Completeness）：WhyとWhatが明確か
3. 一貫性（Consistency）：矛盾・用語の揺れがないか
4. 実装可能性（Feasibility）：技術的に実現可能か

【出力フォーマット】
## レビュー結果
### 1. 明確性
### 2. 完全性
### 3. 一貫性
### 4. 実装可能性
## 改善提案
## 改善済み仕様書
（改善を反映した全文）

日本語で記述してください。"""

PROMPT_REFINE = """あなたはMermaidシーケンス図の専門家です。ユーザーの要望に従って修正してください。
修正版のMermaidコードは必ず```mermaidと```で囲んでください。日本語で記述してください。"""

PROMPT_DIFF = """あなたは仕様駆動開発の専門家です。2つの仕様書を比較し、変更点を分析してください。

【出力フォーマット】
## 変更サマリー
（変更の全体像を2〜3文で）
## 追加された要件
## 削除された要件
## 変更された要件
## 影響範囲の分析
（シーケンス図・実装に与える影響）
## 推奨アクション
（次にすべきこと）

日本語で記述してください。"""

# ════════════════════════════════
#  Anthropic API ヘルパー
# ════════════════════════════════

_client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def call_claude(user_message, system_prompt=None, history=None, max_tokens=2000):
    """Claude API を呼び出す共通関数"""
    messages = (history or []) + [{"role": "user", "content": user_message}]
    kwargs = dict(model=MODEL, max_tokens=max_tokens, messages=messages)
    if system_prompt:
        kwargs["system"] = system_prompt
    response = _client.messages.create(**kwargs)
    return response.content[0].text


def extract_section(text, heading):
    """レスポンステキストから特定の見出し以降のテキストを抽出する。
    見出しレベル（#, ##, ###）や太字（**）に依存せずキーワードで検索する。
    """
    keyword = heading.lstrip('#').strip().lstrip('*').rstrip('*').strip()
    lines = text.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip().lstrip('#').strip().lstrip('*').rstrip('*').strip()
        if stripped == keyword or keyword in stripped:
            return '\n'.join(lines[i+1:]).strip()
    return ""


# ════════════════════════════════
#  GitHub API ヘルパー
# ════════════════════════════════

def github_request(method, path, body=None):
    """GitHub REST API を呼び出す共通関数"""
    url = f"{GITHUB_BASE}/{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=GITHUB_HEADERS, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8')}"


def validate_github_config():
    """GitHub 設定が揃っているか確認する"""
    missing = [k for k, v in {"GITHUB_TOKEN": GITHUB_TOKEN, "GITHUB_OWNER": GITHUB_OWNER, "GITHUB_REPO": GITHUB_REPO}.items() if not v]
    return (False, f"GitHub設定が不足しています: {', '.join(missing)}") if missing else (True, None)


def encode_content(text):
    """テキストを Base64 エンコードする"""
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def get_file_sha(path, branch=None):
    """ファイルの SHA を取得する（存在しない場合は None）"""
    query = f"contents/{path}" + (f"?ref={branch}" if branch else "")
    result, _ = github_request("GET", query)
    return result["sha"] if result else None


def get_file_content(path):
    """ファイルの内容を取得する（存在しない場合は None）"""
    result, _ = github_request("GET", f"contents/{path}")
    if result and "content" in result:
        return base64.b64decode(result["content"]).decode("utf-8")
    return None


def upsert_file(path, content, commit_message, branch=None):
    """ファイルを作成または更新する（branch 指定でブランチ上に操作）"""
    sha = get_file_sha(path, branch)
    body = {"message": commit_message, "content": encode_content(content)}
    if sha:
        body["sha"] = sha
    if branch:
        body["branch"] = branch
    return github_request("PUT", f"contents/{path}", body)


def get_default_branch():
    """デフォルトブランチ名を取得する"""
    result, _ = github_request("GET", "")
    return result.get("default_branch", "main") if result else "main"


def get_branch_sha(branch):
    """ブランチの最新コミット SHA を取得する"""
    result, _ = github_request("GET", f"git/ref/heads/{branch}")
    return result["object"]["sha"] if result else None


def create_branch(branch_name, from_sha):
    """新しいブランチを作成する"""
    return github_request("POST", "git/refs", {"ref": f"refs/heads/{branch_name}", "sha": from_sha})


def create_pull_request(title, body, head, base):
    """Pull Request を作成する"""
    return github_request("POST", "pulls", {"title": title, "body": body, "head": head, "base": base})


# ════════════════════════════════
#  ドキュメントテンプレート
# ════════════════════════════════

def make_spec_doc(content, now):
    return f"# 仕様書\n\n> 最終更新: {now}\n> 生成ツール: SpecFlow（仕様駆動開発アシスタント）\n\n---\n\n{content}\n"


def make_diagram_doc(mermaid_code, now):
    return f"# シーケンス図\n\n> 最終更新: {now}\n> 生成ツール: SpecFlow（仕様駆動開発アシスタント）\n\n---\n\n```mermaid\n{mermaid_code}\n```\n"


def make_readme(now):
    return f"""# {GITHUB_REPO}

仕様駆動開発アシスタント **SpecFlow** によって管理されるリポジトリです。

## 仕様とコードの同期状態

| ドキュメント | 最終更新 |
|---|---|
| [仕様書](docs/specification.md) | {now} |
| [シーケンス図](docs/sequence.md) | {now} |

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
"""


# ════════════════════════════════
#  Flask ルート
# ════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/detect_ambiguity", methods=["POST"])
def detect_ambiguity():
    """要件定義書の曖昧性を卒論の観点で自動検出し形式的定義を補完する"""
    requirements = request.get_json().get("requirements", "")
    if not requirements:
        return jsonify({"error": "要件定義書が空です"}), 400

    reply = call_claude(
        f"以下の要件定義書を分析し、曖昧性を検出して形式的定義で補完してください。\n\n【要件定義書】\n{requirements}",
        system_prompt=PROMPT_AMBIGUITY,
        max_tokens=8000,
    )
    return jsonify({
        "report": reply,
        "enhanced": extract_section(reply, "### 補完済み要件定義書"),
    })


@app.route("/review", methods=["POST"])
def review():
    """仕様書をAIがレビューして改善提案と改善済み仕様書を返す"""
    requirements = request.get_json().get("requirements", "")
    if not requirements:
        return jsonify({"error": "要件定義書が空です"}), 400

    reply = call_claude(
        f"以下の要件定義書をレビューしてください。\n\n{requirements}",
        system_prompt=PROMPT_REVIEW,
        max_tokens=8000,
    )
    return jsonify({
        "review": reply,
        "improved": extract_section(reply, "## 改善済み仕様書"),
    })


@app.route("/generate", methods=["POST"])
def generate():
    """要件定義書からMermaidシーケンス図を生成する"""
    requirements = request.get_json().get("requirements", "")
    if not requirements:
        return jsonify({"error": "要件定義書が空です"}), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    system_prompt = f"""あなたはシステム設計の専門家です。要件定義書を分析しMermaidのシーケンス図を生成してください。

【出力ルール】
- sequenceDiagramフォーマットで出力
- コードは```mermaidと```で囲む
- 参加者の名前はわかりやすい日本語または英語にする
- エラーハンドリング・条件分岐も含める
- コード末尾に以下のコメントを追加する：
  %% 仕様参照: docs/specification.md
  %% 生成日時: {now}
- 日本語で説明を記述する"""

    reply = call_claude(
        f"以下の要件定義書からシーケンス図を生成してください。\n\n{requirements}",
        system_prompt=system_prompt,
        max_tokens=4000,
    )
    return jsonify({"reply": reply})


@app.route("/refine", methods=["POST"])
def refine():
    """生成済みのシーケンス図をチャットで修正する"""
    data = request.get_json()
    current_code = data.get("current_code", "")
    request_text = data.get("request", "")
    history = data.get("history", [])

    if not current_code or not request_text:
        return jsonify({"error": "パラメータが不足しています"}), 400

    reply = call_claude(
        f"現在のシーケンス図：\n```mermaid\n{current_code}\n```\n\n修正依頼：{request_text}",
        system_prompt=PROMPT_REFINE,
        history=history,
    )
    return jsonify({"reply": reply})


@app.route("/save_to_github", methods=["POST"])
def save_to_github():
    """仕様書・シーケンス図・READMEをGitHubのデフォルトブランチに保存する"""
    ok, err = validate_github_config()
    if not ok:
        return jsonify({"error": err}), 400

    data = request.get_json()
    specification  = data.get("specification", "")
    mermaid_code   = data.get("mermaid_code", "")
    commit_message = data.get("commit_message", "仕様を更新")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    errors = []

    files = []
    if specification:
        files.append(("docs/specification.md", make_spec_doc(specification, now),
                      f"docs: {commit_message} — 仕様書を更新 ({now})"))
    if mermaid_code:
        files.append(("docs/sequence.md", make_diagram_doc(mermaid_code, now),
                      f"docs: {commit_message} — シーケンス図を更新 ({now})"))
    # README.md は手動管理のため自動上書きしない

    for path, content, msg in files:
        _, err = upsert_file(path, content, msg)
        if err:
            errors.append(f"{path} の保存に失敗: {err}")

    if errors:
        return jsonify({"error": "\n".join(errors)}), 500

    return jsonify({
        "success": True,
        "message": f"GitHubに保存しました ({now})",
        "url": f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}",
    })


@app.route("/create_pull_request", methods=["POST"])
def create_pr():
    """新しいブランチにコミットしPull Requestを作成する"""
    ok, err = validate_github_config()
    if not ok:
        return jsonify({"error": err}), 400

    data = request.get_json()
    specification = data.get("specification", "")
    mermaid_code  = data.get("mermaid_code", "")
    pr_title      = data.get("pr_title", "仕様の更新")
    pr_body_text  = data.get("pr_body", "")
    now           = datetime.now().strftime("%Y-%m-%d %H:%M")
    branch_name   = f"spec-update-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    default_branch = get_default_branch()
    base_sha = get_branch_sha(default_branch)
    if not base_sha:
        return jsonify({"error": "ベースブランチのSHAを取得できませんでした"}), 500

    _, err = create_branch(branch_name, base_sha)
    if err:
        return jsonify({"error": f"ブランチ作成に失敗: {err}"}), 500

    files = []
    if specification:
        files.append(("docs/specification.md", make_spec_doc(specification, now),
                      f"docs: 仕様書を更新 ({now})"))
    if mermaid_code:
        files.append(("docs/sequence.md", make_diagram_doc(mermaid_code, now),
                      f"docs: シーケンス図を更新 ({now})"))

    for path, content, msg in files:
        _, err = upsert_file(path, content, msg, branch=branch_name)
        if err:
            return jsonify({"error": f"{path} のコミットに失敗: {err}"}), 500

    ai_pr_body = _generate_pr_body(pr_body_text, specification, now)
    pr_result, err = create_pull_request(pr_title, ai_pr_body, branch_name, default_branch)
    if err:
        return jsonify({"error": f"Pull Request作成に失敗: {err}"}), 500

    return jsonify({
        "success": True,
        "pr_url": pr_result.get("html_url", ""),
        "pr_number": pr_result.get("number", ""),
        "branch": branch_name,
        "message": f"Pull Request #{pr_result.get('number')} を作成しました",
    })


@app.route("/detect_diff", methods=["POST"])
def detect_diff():
    """現在の仕様とGitHub上の前回保存仕様を比較しAIが変更点を解説する"""
    ok, err = validate_github_config()
    if not ok:
        return jsonify({"error": err}), 400

    current_spec = request.get_json().get("current_spec", "")
    if not current_spec:
        return jsonify({"error": "現在の仕様が空です"}), 400

    previous_spec = get_file_content("docs/specification.md")

    if not previous_spec:
        return jsonify({"has_previous": False,
                        "message": "GitHubにまだ仕様書が保存されていません。初回の保存になります。"})

    if previous_spec.strip() == current_spec.strip():
        return jsonify({"has_previous": True, "no_change": True,
                        "message": "前回の保存から変更はありません。"})

    diff_report = call_claude(
        f"【前回の仕様書】\n{previous_spec}\n\n【現在の仕様書】\n{current_spec}",
        system_prompt=PROMPT_DIFF,
        max_tokens=2000,
    )
    return jsonify({"has_previous": True, "no_change": False, "diff_report": diff_report})


# ════════════════════════════════
#  内部ヘルパー（ルートから非公開）
# ════════════════════════════════

def _generate_pr_body(user_description, specification, now):
    """AIがPull Requestの説明文を生成する（内部専用）"""
    prompt = f"""以下の情報を元に、GitHubのPull Request説明文を日本語で作成してください。
仕様駆動開発の観点から、変更の意図・内容・影響範囲を明確に記述してください。

【変更の概要】
{user_description or "仕様の更新"}

【更新された仕様書の内容（抜粋）】
{specification[:500] if specification else "（なし）"}

【出力フォーマット】
## 変更の概要
## 変更理由（Why）
## 変更内容（What）
## 影響範囲
## レビューのポイント
## AI利用の記録
- AI生成ツール: SpecFlow (Claude {MODEL})
- 生成日時: {now}
- Human in the Loop: レビュー・承認は人間が実施"""

    return call_claude(prompt, max_tokens=1000)


if __name__ == "__main__":
    app.run(debug=True)