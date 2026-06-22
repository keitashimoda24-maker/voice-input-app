"""リサーチ代行機能: 音声入力の「調べる」意図を検出し、バックグラウンドで調査。"""

import json
import threading
from datetime import datetime

from config import CONFIG_DIR

RESEARCH_FILE = CONFIG_DIR / "research_results.json"


def load_results() -> list:
    RESEARCH_FILE.parent.mkdir(exist_ok=True)
    if RESEARCH_FILE.exists():
        with open(RESEARCH_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_results(results: list):
    RESEARCH_FILE.parent.mkdir(exist_ok=True)
    with open(RESEARCH_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


def mark_all_read():
    results = load_results()
    for r in results:
        r["read"] = True
    save_results(results)


def unread_count() -> int:
    return sum(1 for r in load_results() if not r.get("read"))


def process_direct(query: str, on_new_result=None, on_error=None):
    """ウェイクワードで明示されたクエリを直接リサーチ（意図検出なし）。"""

    def _run():
        try:
            from ai_actions import research_item

            answer = research_item(query)
            results = load_results()
            results.append(
                {
                    "item": query,
                    "answer": answer,
                    "timestamp": datetime.now().isoformat(),
                    "read": False,
                }
            )
            save_results(results)
            if on_new_result:
                on_new_result(query, answer)
        except Exception as e:
            if on_error:
                from config import safe_error_message

                on_error(safe_error_message(e))

    threading.Thread(target=_run, daemon=True).start()


def process_async(text: str, on_new_result=None):
    """[廃止予定] テキストにリサーチ意図があればバックグラウンドで調査して保存。
    現在はウェイクワード方式に移行したため呼ばれない。"""

    def _run():
        try:
            from ai_actions import detect_research_items, research_item

            items = detect_research_items(text)
            if not items:
                return
            results = load_results()
            for item in items:
                try:
                    answer = research_item(item)
                    results.append(
                        {
                            "item": item,
                            "answer": answer,
                            "timestamp": datetime.now().isoformat(),
                            "read": False,
                        }
                    )
                    save_results(results)
                    if on_new_result:
                        on_new_result(item)
                except Exception:
                    pass
        except Exception:
            pass

    threading.Thread(target=_run, daemon=True).start()
