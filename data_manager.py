"""ユーザーデータのエクスポート・削除機能。"""

import json
import os
from datetime import datetime

from config import (
    CONFIG_DIR,
    CONFIG_FILE,
    HISTORY_FILE,
    STYLE_PROMPT_FILE,
    VOCABULARY_FILE,
    WHISPER_PROMPT_FILE,
    _keychain_delete,
    _secure_dir,
)


def export_all_data(output_path: str) -> str:
    """全ユーザーデータをJSON形式でエクスポートする。"""
    data = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "app": "voice_input_app",
    }

    # config.json
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, encoding="utf-8") as f:
            data["config"] = json.load(f)
        # APIキーはエクスポートから除外
        if "openai_api_key" in data.get("config", {}):
            data["config"]["openai_api_key"] = "[除外]"

    # vocabulary.json
    if VOCABULARY_FILE.exists():
        with open(VOCABULARY_FILE, encoding="utf-8") as f:
            data["vocabulary"] = json.load(f)

    # correction_history.json
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, encoding="utf-8") as f:
            data["correction_history"] = json.load(f)

    # whisper_prompt.txt
    if WHISPER_PROMPT_FILE.exists():
        data["whisper_prompt"] = WHISPER_PROMPT_FILE.read_text(encoding="utf-8").strip()

    # style_prompt.txt
    if STYLE_PROMPT_FILE.exists():
        data["style_prompt"] = STYLE_PROMPT_FILE.read_text(encoding="utf-8").strip()

    # custom_instructions.txt
    instructions_path = CONFIG_DIR / "custom_instructions.txt"
    if instructions_path.exists():
        data["custom_instructions"] = instructions_path.read_text(encoding="utf-8").strip()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return output_path


def delete_all_data() -> list[str]:
    """全ユーザーデータを削除する。削除したファイルのリストを返す。"""
    deleted = []

    # データファイルを削除
    data_files = [
        VOCABULARY_FILE,
        HISTORY_FILE,
        WHISPER_PROMPT_FILE,
        STYLE_PROMPT_FILE,
        CONFIG_DIR / "custom_instructions.txt",
    ]

    for f in data_files:
        if f.exists():
            try:
                os.unlink(f)
                deleted.append(str(f.name))
            except Exception:
                pass

    # KeychainからAPIキーを削除
    try:
        _keychain_delete()
        deleted.append("Keychain APIキー")
    except Exception:
        pass

    # consent_accepted をリセット（config.jsonは保持して同意フラグだけ消す）
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                config = json.load(f)
            config.pop("consent_accepted", None)
            config["openai_api_key"] = ""
            _secure_dir()
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            deleted.append("config.json (APIキー・同意情報をリセット)")
        except Exception:
            pass

    return deleted


def get_data_summary() -> dict:
    """保存されているデータの概要を返す。"""
    summary = {}

    if CONFIG_FILE.exists():
        summary["設定ファイル"] = f"{CONFIG_FILE.stat().st_size:,} bytes"

    if VOCABULARY_FILE.exists():
        with open(VOCABULARY_FILE, encoding="utf-8") as f:
            vocab = json.load(f)
        word_count = len([k for k in vocab if k != "_phrases"])
        phrase_count = len(vocab.get("_phrases", {}))
        summary["語彙辞書"] = f"単語 {word_count}件, フレーズ {phrase_count}件"

    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, encoding="utf-8") as f:
            history = json.load(f)
        summary["修正履歴"] = f"{len(history)}件"

    if WHISPER_PROMPT_FILE.exists():
        summary["Whisperプロンプト"] = WHISPER_PROMPT_FILE.read_text(encoding="utf-8").strip()[:50]

    instructions_path = CONFIG_DIR / "custom_instructions.txt"
    if instructions_path.exists():
        summary["カスタム指示"] = f"{instructions_path.stat().st_size:,} bytes"

    return summary
