"""Transcript history storage and retrieval."""

import json
from datetime import datetime
from pathlib import Path

_HISTORY_DIR = Path.home() / ".voice_input_app"
_HISTORY_FILE = _HISTORY_DIR / "transcript_history.json"
_MAX_ENTRIES = 500


def _ensure_dir():
    try:
        _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def _load_raw() -> list[dict]:
    try:
        if _HISTORY_FILE.exists():
            with open(_HISTORY_FILE, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _save_raw(data: list[dict]):
    _ensure_dir()
    try:
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_transcript(text: str):
    """Save a transcript with timestamp. Auto-prunes to MAX_ENTRIES."""
    if not text or not text.strip():
        return
    try:
        history = _load_raw()
        entry = {
            "text": text.strip(),
            "timestamp": datetime.now().isoformat(),
        }
        history.append(entry)
        # Auto-prune oldest entries
        if len(history) > _MAX_ENTRIES:
            history = history[-_MAX_ENTRIES:]
        _save_raw(history)
    except Exception:
        pass


def load_history() -> list[dict]:
    """Load all transcripts. Each has 'text' and 'timestamp'."""
    try:
        return _load_raw()
    except Exception:
        return []


def clear_history():
    """Clear all transcript history."""
    try:
        _save_raw([])
    except Exception:
        pass


def search_history(query: str) -> list[dict]:
    """Search transcripts by keyword (case-insensitive)."""
    try:
        if not query or not query.strip():
            return load_history()
        q = query.strip().lower()
        return [e for e in _load_raw() if q in e.get("text", "").lower()]
    except Exception:
        return []
