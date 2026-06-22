"""自動置換ルールの管理モジュール。"""

import json
import os

_DIR = os.path.expanduser("~/.voice_input_app")
_FILE = os.path.join(_DIR, "replacements.json")


def load_replacements() -> list[dict]:
    """置換ルールを読み込む。[{"from": "xxx", "to": "yyy"}, ...]"""
    if not os.path.exists(_FILE):
        return []
    try:
        with open(_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save(rules: list[dict]):
    """ルールをファイルに保存。"""
    os.makedirs(_DIR, exist_ok=True)
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


def add_replacement(from_text: str, to_text: str):
    """置換ルールを追加。同じ from_text があれば上書き。"""
    rules = load_replacements()
    # 既存ルールを上書き
    rules = [r for r in rules if r.get("from") != from_text]
    rules.append({"from": from_text, "to": to_text})
    _save(rules)


def remove_replacement(from_text: str):
    """置換ルールを削除。"""
    rules = load_replacements()
    rules = [r for r in rules if r.get("from") != from_text]
    _save(rules)


def apply_replacements(text: str) -> str:
    """全ての置換ルールをテキストに適用（大文字小文字を区別する完全一致）。"""
    rules = load_replacements()
    for rule in rules:
        fr = rule.get("from", "")
        to = rule.get("to", "")
        if fr:
            text = text.replace(fr, to)
    return text
