import json
import os
import re
import subprocess
from pathlib import Path

CONFIG_DIR = Path.home() / ".voice_input_app"
CONFIG_FILE = CONFIG_DIR / "config.json"
VOCABULARY_FILE = CONFIG_DIR / "vocabulary.json"
HISTORY_FILE = CONFIG_DIR / "correction_history.json"
WHISPER_PROMPT_FILE = CONFIG_DIR / "whisper_prompt.txt"
STYLE_PROMPT_FILE = CONFIG_DIR / "style_prompt.txt"

DEFAULT_CONFIG = {
    "openai_api_key": "",  # レガシー（未使用）
    "anthropic_api_key": "",
    "language": "ja",
    "model": "mlx-whisper",
    "sample_rate": 16000,
    "max_recording_seconds": 120,
    "input_mode": "window",
    "app_format_enabled": True,
    "style_learn_enabled": True,
    "team_vocab_path": "",
    "hotkey": {
        "keycode": 15,  # Virtual Key Code: 'r'
        "quartz_flags": 1572864,  # kCGEventFlagMaskCommand | kCGEventFlagMaskAlternate
        "display": "Cmd+Option+R",
    },
    "paste_last_hotkey": {
        "keycode": 9,  # Virtual Key Code: 'v'
        "quartz_flags": 1310720,  # kCGEventFlagMaskCommand | kCGEventFlagMaskControl
        "display": "Cmd+Ctrl+V",
    },
    "memo_wake_words": "メモ,めも,memo,ボイスメモ,音声メモ,おんせいメモ",
    "research_wake_words": "リサーチ,りさーち,research,調べて,しらべて,調べてください,調べておいて,リサーチして,リサーチしてください",
    "calendar_wake_words": "カレンダー,かれんだー,calendar,予定追加,スケジュール追加",
    "app_rules": {},
    "return_key_action": "send",  # "send" = Return で送信, "paste" = Return で貼り付けのみ
    "transcription_mode": "edit",  # "edit" = 編集ウィンドウ表示, "direct" = 入力欄に直接貼り付け
    "deep_context_enabled": False,  # 画面キャプチャはデフォルト無効（プライバシー保護）
    "consent_accepted": False,  # プライバシーポリシー同意フラグ
    "auto_format_mode": "off",  # "off", "clean", "bullets", "paragraph", "auto"

}


def load_config():
    CONFIG_DIR.mkdir(exist_ok=True)
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return {**DEFAULT_CONFIG, **data}
    return DEFAULT_CONFIG.copy()


def _secure_dir():
    """CONFIG_DIRを作成し、権限を700に設定。"""
    CONFIG_DIR.mkdir(exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except Exception:
        pass


def _secure_file(path):
    """ファイルの権限を600（所有者のみ読み書き）に設定。"""
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def save_config(config: dict):
    _secure_dir()
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    _secure_file(CONFIG_FILE)


# ── APIキー管理（Keychain優先）──────────────────────────────────────────────

_KEYCHAIN_SERVICE = "voice_input_app"
_KEYCHAIN_ACCOUNT = "anthropic_api_key"
_KEYCHAIN_ACCOUNT_LEGACY = "openai_api_key"


def _keychain_get() -> str:
    """macOS KeychainからAPIキーを取得。"""
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-a", _KEYCHAIN_ACCOUNT, "-s", _KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def _keychain_set(api_key: str):
    """macOS KeychainにAPIキーを保存。"""
    try:
        subprocess.run(
            ["security", "add-generic-password", "-a", _KEYCHAIN_ACCOUNT, "-s", _KEYCHAIN_SERVICE, "-w", api_key, "-U"],
            capture_output=True,
            timeout=3,
        )
    except Exception:
        pass


def _keychain_delete():
    """macOS KeychainからAPIキーを削除。"""
    try:
        subprocess.run(
            ["security", "delete-generic-password", "-a", _KEYCHAIN_ACCOUNT, "-s", _KEYCHAIN_SERVICE],
            capture_output=True,
            timeout=3,
        )
    except Exception:
        pass


def get_api_key() -> str:
    """Anthropic APIキーを安全に取得（Keychain → config.json → 環境変数の順）。"""
    # 1. Keychain（Anthropic）
    key = _keychain_get()
    if key:
        return key
    # 2. config.json
    config = load_config()
    key = config.get("anthropic_api_key", "").strip()
    if key:
        _keychain_set(key)
        config["anthropic_api_key"] = ""
        save_config(config)
        return key
    # 3. 環境変数
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    # 4. Global Keychain entry shared under the current user account
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", "ANTHROPIC_API_KEY", "-w"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def save_api_key(api_key: str):
    """Anthropic APIキーをKeychainに保存（config.jsonには保存しない）。"""
    if api_key.strip():
        _keychain_set(api_key.strip())
    else:
        _keychain_delete()
    config = load_config()
    if config.get("anthropic_api_key"):
        config["anthropic_api_key"] = ""
        save_config(config)


# ── エラーメッセージのサニタイズ ─────────────────────────────────────────────


def safe_error_message(e: Exception) -> str:
    """APIキーを含まないエラーメッセージを生成。"""
    msg = str(e)
    # sk-で始まるAPIキーパターンを除去
    msg = re.sub(r"sk-ant-[a-zA-Z0-9_-]{20,}", "[APIキー]", msg)
    msg = re.sub(r"sk-[a-zA-Z0-9_-]{20,}", "[APIキー]", msg)
    lower = msg.lower()
    if "authentication" in lower or "api_key" in lower or "invalid api key" in lower:
        return "Anthropic APIキーが無効です。設定を確認してください。"
    return msg


def load_vocabulary():
    CONFIG_DIR.mkdir(exist_ok=True)
    if VOCABULARY_FILE.exists():
        with open(VOCABULARY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_vocabulary(vocab: dict):
    _secure_dir()
    with open(VOCABULARY_FILE, "w", encoding="utf-8") as f:
        json.dump(vocab, f, indent=2, ensure_ascii=False)
    _secure_file(VOCABULARY_FILE)


def load_history() -> list:
    CONFIG_DIR.mkdir(exist_ok=True)
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history: list):
    _secure_dir()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    _secure_file(HISTORY_FILE)


def load_whisper_prompt() -> str:
    CONFIG_DIR.mkdir(exist_ok=True)
    if WHISPER_PROMPT_FILE.exists():
        return WHISPER_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return ""


def save_whisper_prompt(prompt: str):
    _secure_dir()
    WHISPER_PROMPT_FILE.write_text(prompt, encoding="utf-8")
    _secure_file(WHISPER_PROMPT_FILE)


def load_style_prompt() -> str:
    CONFIG_DIR.mkdir(exist_ok=True)
    if STYLE_PROMPT_FILE.exists():
        return STYLE_PROMPT_FILE.read_text(encoding="utf-8").strip()
    return ""


def save_style_prompt(prompt: str):
    _secure_dir()
    STYLE_PROMPT_FILE.write_text(prompt, encoding="utf-8")
    _secure_file(STYLE_PROMPT_FILE)
