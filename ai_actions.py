"""Claude呼び出しの共通ユーティリティ。"""

import json


def _client():
    from anthropic import Anthropic

    from config import get_api_key

    api_key = get_api_key()
    if not api_key:
        raise ValueError("Anthropic APIキーが設定されていません。")
    return Anthropic(api_key=api_key)


def _chat(system: str, user: str, model: str = "claude-sonnet-4-6", max_tokens: int = 2048, temperature: float = 0.3) -> str:
    """Claude APIを呼び出してテキストを返す共通関数。"""
    client = _client()
    resp = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()


def tone_convert(text: str) -> str:
    """感情的・口語的テキストをビジネス文に変換。"""
    return _chat(
        system=(
            "あなたは日本語ビジネス文章の校正アシスタントです。"
            "入力テキストを感情・口語表現を排除し、従業員や取引先に"
            "そのまま送れる冷静・論理的なビジネステキストに変換してください。"
            "元の意図・情報を保持し、変換後のテキストのみ出力してください。"
        ),
        user=text,
    )


def structure_braindump(text: str) -> dict:
    """雑然とした音声テキストを構造化して返す。"""
    system = (
        "あなたは思考整理アシスタントです。音声入力された雑然とした発言を"
        "以下のカテゴリに分類・整理し、JSONのみを出力してください。\n\n"
        "カテゴリ（空なら含めない）:\n"
        "- 今日やること\n- アイデア・事業構想\n- 懸念事項・問題\n"
        "- 要調査・要確認\n- メモ・その他\n\n"
        '例: {"今日やること": ["タスクA"], "アイデア・事業構想": ["案B"]}'
    )
    raw = _chat(system=system, user=text, temperature=0.2)
    # JSON部分を抽出（Claudeがマークダウンで囲むことがある）
    if "```" in raw:
        import re
        m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {"メモ・その他": [raw if raw else "(音声の解析に失敗しました)"]}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if isinstance(v, list)}


def detect_research_items(text: str) -> list:
    """「調べる・確認する」意図の項目を抽出。なければ空リスト。"""
    prompt = (
        f"次の音声入力テキストに「後で調べる・確認する」意図が含まれるか判定し、"
        f'調査項目を抽出してください。\n\nテキスト: "{text}"\n\n'
        'JSONのみ出力: {"has_research": true/false, "items": ["項目1"]}'
    )
    raw = _chat(system="JSONのみ出力してください。", user=prompt, temperature=0.1)
    if "```" in raw:
        import re
        m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, dict):
        return []
    items = data.get("items", [])
    if not isinstance(items, list):
        return []
    return [str(i) for i in items if isinstance(i, str)] if data.get("has_research") else []


_FORMAT_PROMPTS = {
    "clean": (
        "【テキスト整形】\n"
        "話し言葉を読みやすい書き言葉に整形してください。\n"
        "- 冗長な表現を簡潔にする\n"
        "- 適切な句読点と改行を入れる\n"
        "- 口語表現を自然な書き言葉に変換する\n"
        "- 元の意味・情報は100%保持する\n"
        "- 整形後のテキストのみ出力する"
    ),
    "bullets": (
        "【箇条書き変換】\n"
        "テキストを箇条書きに変換してください。\n"
        "- 各ポイントを「・」で始める箇条書きにする\n"
        "- 関連する内容はグループ化する\n"
        "- 重要な情報を漏らさない\n"
        "- 冗長な表現は簡潔にまとめる\n"
        "- 箇条書きテキストのみ出力する"
    ),
    "paragraph": (
        "【段落整形】\n"
        "テキストを読みやすい段落構成に整形してください。\n"
        "- 話題ごとに段落を分ける\n"
        "- 各段落は2〜4文程度にまとめる\n"
        "- 適切な接続詞で段落間をつなげる\n"
        "- 口語を書き言葉に変換する\n"
        "- 整形後のテキストのみ出力する"
    ),
    "auto": (
        "【自動整形】\n"
        "テキストの内容に応じて最適な形式に整形してください。\n"
        "- 列挙・手順 → 箇条書き（「・」で始める）\n"
        "- 説明・報告 → 段落構成\n"
        "- 短いメモ → 簡潔な書き言葉\n"
        "- 口語表現を自然な書き言葉に変換する\n"
        "- 元の意味・情報は100%保持する\n"
        "- 整形後のテキストのみ出力する"
    ),
}


def auto_format(text: str, mode: str = "auto") -> str:
    """テキストを指定モードで整形する。"""
    prompt = _FORMAT_PROMPTS.get(mode)
    if not prompt:
        return text
    return _chat(
        system=prompt,
        user=text,
    )


def get_format_instruction(mode: str) -> str:
    """transcriber.pyの既存Claude呼び出しに統合するための整形指示を返す。"""
    return _FORMAT_PROMPTS.get(mode, "")


def research_item(item: str) -> str:
    """調査項目についてMarkdown形式で簡潔に回答する。"""
    return _chat(
        system=(
            "あなたは知識豊富なリサーチアシスタントです。"
            "Markdown形式（見出し・箇条書き・太字）を使って読みやすく回答してください。"
            "簡潔かつ正確に。不確実な情報には「※」を付けてください。"
        ),
        user=item,
        model="claude-sonnet-4-6",
    )
