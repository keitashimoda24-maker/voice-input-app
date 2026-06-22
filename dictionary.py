"""辞書データストア — カスタム単語でWhisper精度を向上。"""

import json
import os

_MAX_ENTRIES = 800
_DIR = os.path.expanduser("~/.voice_input_app")
_FILE = os.path.join(_DIR, "dictionary.json")


def _ensure_dir():
    os.makedirs(_DIR, exist_ok=True)


def load_dictionary() -> list[str]:
    """辞書ファイルから単語リストを読み込む。"""
    try:
        with open(_FILE, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [w for w in data if isinstance(w, str)]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def _save(words: list[str]):
    _ensure_dir()
    with open(_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)


def add_word(word: str):
    """単語を追加（重複・上限チェック付き）。"""
    word = word.strip()
    if not word:
        return
    words = load_dictionary()
    if word in words:
        return
    if len(words) >= _MAX_ENTRIES:
        return
    words.append(word)
    _save(words)


def remove_word(word: str):
    """単語を削除。"""
    words = load_dictionary()
    if word in words:
        words.remove(word)
        _save(words)


def get_prompt_words() -> str:
    """Whisperプロンプト用にカンマ区切り文字列を返す。"""
    words = load_dictionary()
    if not words:
        return ""
    return ", ".join(words)
