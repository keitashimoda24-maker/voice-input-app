"""音声入力からmacOSカレンダーに予定を追加する。"""

import json
import re
import subprocess
import threading
from datetime import datetime


def _parse_event(query: str) -> dict:
    """Claudeで音声テキストからイベント情報をJSON抽出。"""
    from anthropic import Anthropic

    from config import get_api_key

    api_key = get_api_key()
    client = Anthropic(api_key=api_key)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M (%A, JST)")
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=(
            f"現在日時: {now_str}\n"
            "音声入力テキストからカレンダーイベント情報を抽出し、以下のJSONのみ出力してください。\n"
            '{"title":"タイトル","start":"YYYY-MM-DDTHH:MM:00","end":"YYYY-MM-DDTHH:MM:00","notes":""}\n'
            "・日付が不明なら今日、時刻が不明なら次の正時、所要時間不明なら1時間とする。\n"
            "・notesは明示的な補足があれば入れる。なければ空文字。\n"
            "・JSONのみ出力。説明やマークダウン記法は不要。"
        ),
        messages=[{"role": "user", "content": query}],
    )
    raw = resp.content[0].text.strip()
    # Claudeがマークダウンで囲むことがあるので抽出
    if "```" in raw:
        m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
        if m:
            raw = m.group(1)
    data = json.loads(raw)
    # JSON スキーマ検証
    required = {"title", "start", "end"}
    if not required.issubset(data.keys()):
        raise ValueError(f"AIレスポンスに必須フィールドが不足: {required - data.keys()}")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise ValueError("タイトルが空です")
    datetime.fromisoformat(data["start"])
    datetime.fromisoformat(data["end"])
    if "notes" in data and not isinstance(data["notes"], str):
        data["notes"] = ""
    return data


def _escape_applescript(s: str) -> str:
    """AppleScript文字列リテラルを安全にエスケープする。"""
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    s = "".join(c for c in s if c >= " " or c == "\t")
    s = s.replace("\t", " ")
    return s


def _add_to_calendar(event: dict) -> str:
    """AppleScriptでmacOSカレンダーにイベントを追加。追加した予定の概要を返す。"""
    title = _escape_applescript(event.get("title", "予定"))
    notes = _escape_applescript(event.get("notes", ""))
    start = datetime.fromisoformat(event["start"])
    end = datetime.fromisoformat(event["end"])

    def _fmt(dt: datetime) -> str:
        return dt.strftime("%Y/%m/%d %H:%M:%S")

    notes_line = f'set description of ev to "{notes}"' if notes else ""

    script = f'''
tell application "Calendar"
    set target_cal to first calendar whose writable is true
    tell target_cal
        set ev to make new event with properties {{¬
            summary:"{title}", ¬
            start date:date "{_fmt(start)}", ¬
            end date:date "{_fmt(end)}"}}
        {notes_line}
    end tell
    reload calendars
end tell
'''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "AppleScript error")

    label = f"{title}（{start.strftime('%-m/%-d %-H:%M')}〜{end.strftime('%-H:%M')}）"
    return label


def process_async(query: str, on_done=None, on_error=None):
    """バックグラウンドでパース＆カレンダー追加。"""

    def _run():
        try:
            event = _parse_event(query)
            label = _add_to_calendar(event)
            if on_done:
                on_done(label)
        except Exception as e:
            if on_error:
                from config import safe_error_message

                on_error(safe_error_message(e))

    threading.Thread(target=_run, daemon=True).start()
