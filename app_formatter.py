"""アプリ別自動フォーマット + 文体反映
ローカル置換エンジン搭載: 単純なルールはGPT不要で即座に適用。"""

import re

from config import load_config, load_style_prompt


def get_active_app_name() -> str:
    try:
        from AppKit import NSWorkspace

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        return app.localizedName() if app else ""
    except Exception:
        return ""


def get_app_name_from_pid(pid: int) -> str:
    """PIDからアプリ名を取得する（バックグラウンドアプリも正しく識別）。"""
    if not pid:
        return get_active_app_name()
    try:
        from AppKit import NSRunningApplication

        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        return app.localizedName() if app else ""
    except Exception:
        return ""


# ── ローカル置換エンジン ────────────────────────────────────────────────────────

_SENTENCE_ENDINGS = re.compile(r"[。．.！!？?]+$")
_PERIOD = re.compile(r"[。．]")

# ルール断片ごとのパターン（順に試す）
_RULE_PATTERNS = [
    # 句読点除去（句読点 = 句点+読点の両方を除去）
    (
        re.compile(
            r"句読点[をは]?(使用|使わ|つかわ|付け|つけ)?(し?な[いくし]*|せず|しない)"
            r"|句読点なし|句読点[をは]?(除去|削除)|句読点不要"
        ),
        "remove_both",
    ),
    # 句点のみ除去: 「句点を使用せず」「句点なし」「。を使わない」等
    (
        re.compile(
            r"句点[をは]?(使用|使わ|つかわ|付け|つけ)?(し?な[いくし]*|せず|しない)"
            r"|句点なし|[。]なし|[。]+不要|句点[をは]?(除去|削除)"
        ),
        "remove_period",
    ),
    # 読点のみ除去
    (
        re.compile(
            r"読点[をは]?(使用|使わ|つかわ)?(し?な[いくし]*|せず|しない)"
            r"|読点なし|[、，,]なし|[、，,]+不要|読点[をは]?(除去|削除)"
        ),
        "remove_comma",
    ),
    # 末尾文字指定: 「！で終わらせて」「！をつけて」等
    (re.compile(r"([！!？?♪☆★…])\s*[でをに]?\s*(終わ[らりるれろっせ]*|終え|つけ|付け|追加)[てる]*"), "ensure_ending"),
    # 句点→別記号: 「句点の代わりに！」「。→！」「。を！に」
    (re.compile(r"[。句点]+\s*[のを]?\s*(代わり|→|➡|から)\s*[にへ]?\s*([！!？?♪]+)"), "replace_period"),
]

# 残りテキストから除去する接続詞・助詞・依頼表現
_FILLER = re.compile(r"[、,，。．\s　してくださいまたおよび・]+")


def _build_local_rules(rule_text: str):
    """ルール文字列を解析し、ローカル適用可能な関数リストを返す。
    全てローカル処理できれば (functions, True)、できなければ ([], False)。"""
    rule = rule_text.strip()
    if not rule:
        return [], True

    fns = []
    remaining = rule

    for pattern, action in _RULE_PATTERNS:
        m = pattern.search(remaining)
        if not m:
            continue

        if action == "remove_both":
            fns.append(lambda t: re.sub(r"[。．、，,]", "", t))
        elif action == "remove_period":
            fns.append(lambda t: _PERIOD.sub("", t))
        elif action == "remove_comma":
            fns.append(lambda t: re.sub(r"[、，,]", "", t))
        elif action == "ensure_ending":
            end_char = m.group(1)

            def _ensure(t, c=end_char):
                t = _SENTENCE_ENDINGS.sub("", t)
                return t + c

            fns.append(_ensure)
        elif action == "replace_period":
            repl_char = m.group(2)[0]
            fns.append(lambda t, c=repl_char: _PERIOD.sub(c, t))

        remaining = remaining[: m.start()] + remaining[m.end() :]

    # 残りに意味のある指示があるかチェック
    cleaned = _FILLER.sub("", remaining).strip()
    all_local = len(cleaned) == 0

    if fns and all_local:
        return fns, True
    return [], False


def _apply_local_rules(text: str, fns: list) -> str:
    """ローカル置換関数を順番に適用する。"""
    for fn in fns:
        text = fn(text)
    return text


def format_for_app(text: str, target_pid: int = 0) -> str:
    """アプリ別フォーマット。ローカル処理可能なルールは即座に適用。"""
    config = load_config()

    app_name = get_app_name_from_pid(target_pid)

    app_rules: dict = config.get("app_rules", {})
    custom_rule = ""
    if app_name:
        for rule_app, rule_text in app_rules.items():
            if rule_app and rule_app.lower() in app_name.lower():
                custom_rule = rule_text
                break

    if not custom_rule:
        return text

    # ローカル置換エンジンで処理を試みる
    local_fns, all_local = _build_local_rules(custom_rule)
    if all_local and local_fns:
        return _apply_local_rules(text, local_fns)

    # ローカルで処理できない場合のみClaudeにフォールバック
    from config import get_api_key

    api_key = get_api_key()
    if not api_key:
        return text

    style_prompt = load_style_prompt()
    system_parts = [
        "音声入力テキストの整形アシスタントです。",
        "ユーザーが話した内容をそのまま維持し、指定されたルールに従って文体だけ調整してください。",
        "内容の追加・補足・説明は絶対にしないでください。入力されたテキストのみを出力してください。",
        f"【アプリ別ルール ({app_name})】{custom_rule}",
    ]
    if config.get("style_learn_enabled") and style_prompt:
        system_parts.append(f"ユーザーの文体の特徴: {style_prompt}")

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system="\n".join(system_parts),
            messages=[{"role": "user", "content": text}],
        )
        return resp.content[0].text.strip() or text
    except Exception:
        return text
