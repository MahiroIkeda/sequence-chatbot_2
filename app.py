from flask import Flask, request, jsonify, render_template
from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    """要件定義書からシーケンス図を生成する"""
    data = request.get_json()
    requirements = data.get("requirements", "")

    if not requirements:
        return jsonify({"error": "要件定義書が空です"}), 400

    system_prompt = """あなたはシステム設計の専門家です。ユーザーが提供する要件定義書を分析し、Mermaidのシーケンス図を生成してください。

【出力ルール】
- 必ずMermaidのsequenceDiagramフォーマットで出力する
- コードは```mermaidと```で囲む
- 参加者（participant）の名前はわかりやすい日本語または英語にする
- エラーハンドリングや条件分岐も可能な限り含める
- コード以外の説明も日本語で記述する"""

    user_message = f"""以下の要件定義書を分析して、システムの処理フローを表すMermaidシーケンス図を生成してください。

【要件定義書】
{requirements}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    reply = response.content[0].text
    return jsonify({"reply": reply})


@app.route("/refine", methods=["POST"])
def refine():
    """生成済みのシーケンス図を修正する"""
    data = request.get_json()
    current_code = data.get("current_code", "")
    request_text = data.get("request", "")
    history = data.get("history", [])

    if not current_code or not request_text:
        return jsonify({"error": "パラメータが不足しています"}), 400

    system_prompt = """あなたはMermaidシーケンス図の専門家です。ユーザーの要望に従って、現在のシーケンス図を修正してください。
修正版のMermaidコードは必ず```mermaidと```で囲んでください。説明は日本語で記述してください。"""

    user_message = f"""現在のシーケンス図：
```mermaid
{current_code}
```

修正依頼：{request_text}"""

    messages = history + [{"role": "user", "content": user_message}]

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=system_prompt,
        messages=messages,
    )

    reply = response.content[0].text
    return jsonify({"reply": reply})


if __name__ == "__main__":
    app.run(debug=True)