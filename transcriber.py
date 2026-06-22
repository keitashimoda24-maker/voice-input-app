"""mlx-whisper (ローカル) + Anthropic Claude による音声文字起こし。"""

import json
import os
import re
import subprocess
import sys

from anthropic import Anthropic

from config import get_api_key, load_config, load_whisper_prompt
from dictionary import get_prompt_words
from learning import apply_corrections

# Anthropic clientをシングルトンで使い回す
_client = None
_client_key = None

_MLX_MODEL = "mlx-community/whisper-large-v3-turbo"

# whisper_worker.py のパス
_WORKER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whisper_worker.py")
# venv の Python パス
_VENV_PYTHON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "venv", "bin", "python3")


def _get_client() -> Anthropic:
    global _client, _client_key
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Anthropic APIキーが設定されていません。設定から入力してください。")
    if _client is None or _client_key != api_key:
        _client = Anthropic(api_key=api_key)
        _client_key = api_key
    return _client


# 文頭・文中のフィラーワード（長い順にマッチさせる）
_FILLER_WORDS = [
    "えーっと",
    "えーと",
    "あのー",
    "あのう",
    "そのー",
    "そのう",
    "まあその",
    "なんか",
    "なんだろう",
    "なんていうか",
    "えっと",
    "えー",
    "あー",
    "うー",
    "んー",
    "まー",
    "あの",
    "その",
    "まあ",
    "まぁ",
    "ええ",
]
# 正規表現パターン: フィラー + 任意の区切り文字
_FILLER_PATTERN = re.compile(r"(?:" + "|".join(re.escape(w) for w in _FILLER_WORDS) + r")[、,，\s]*", re.IGNORECASE)


def _remove_fillers(text: str) -> str:
    """フィラーワード（えー、あー、えーと等）を除去する。"""
    result = _FILLER_PATTERN.sub("", text)
    # 連続する区切り文字を整理
    result = re.sub(r"[、,]{2,}", "、", result)
    result = result.strip("、,，  \t")
    return result.strip()


def _compress_to_mp3(wav_path: str) -> str:
    """WAVをMP3に圧縮してローカルWhisper処理を高速化。
    小さいファイル（500KB未満）は圧縮をスキップ。失敗時はWAVをそのまま返す。"""
    try:
        if os.path.getsize(wav_path) < 512_000:
            return wav_path
        import subprocess

        mp3_path = wav_path.replace(".wav", ".mp3")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-ar", "16000", "-ac", "1", "-b:a", "32k", mp3_path],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0 and os.path.exists(mp3_path):
            return mp3_path
    except Exception:
        pass
    return wav_path


def _transcribe_local(audio_path: str, language: str, prompt: str) -> str:
    """mlx-whisperを別プロセスで実行（GILブロッキングによるUIフリーズを防止）。"""
    python_exe = _VENV_PYTHON if os.path.exists(_VENV_PYTHON) else sys.executable
    input_data = json.dumps({
        "audio_path": audio_path,
        "language": language,
        "prompt": prompt,
        "model": _MLX_MODEL,
    })

    try:
        proc = subprocess.run(
            [python_exe, _WORKER_SCRIPT],
            input=input_data,
            capture_output=True,
            text=True,
            timeout=120,  # 最大2分
        )
        if proc.returncode == 0 and proc.stdout.strip():
            result = json.loads(proc.stdout)
            return (result.get("text", "") or "").strip()
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    # サブプロセス失敗時はインプロセスにフォールバック（最後の手段）
    try:
        import mlx_whisper

        kwargs = {"path_or_hf_repo": _MLX_MODEL, "verbose": False}
        if language and language != "auto":
            kwargs["language"] = language
        if prompt:
            kwargs["initial_prompt"] = prompt
        result = mlx_whisper.transcribe(audio_path, **kwargs)
        return (result.get("text", "") or "").strip()
    except Exception:
        return ""


def transcribe(audio_file_path: str, target_pid: int = 0, screen_context: str = "") -> str:
    """音声ファイルをmlx-whisperで文字起こしし、Claudeで後処理する。"""
    config = load_config()

    # MP3に圧縮
    upload_path = _compress_to_mp3(audio_file_path)

    # AI学習済みプロンプトをWhisperに渡す（変換精度向上）
    learned_prompt = load_whisper_prompt()
    if learned_prompt and (len(learned_prompt) > 40 or any(c in learned_prompt for c in "。？！!?\n")):
        learned_prompt = ""

    # 辞書のカスタム単語をプロンプトに追加
    dict_words = get_prompt_words()
    prompt_parts = []
    if learned_prompt:
        prompt_parts.append(learned_prompt)
    if dict_words:
        prompt_parts.append(dict_words)
    if screen_context:
        prompt_parts.append(screen_context)
    combined_prompt = ", ".join(prompt_parts)

    _lang = config.get("language", "ja")

    try:
        raw_text = _transcribe_local(upload_path, _lang, combined_prompt)
    finally:
        if upload_path != audio_file_path:
            try:
                os.unlink(upload_path)
            except Exception:
                pass

    if not raw_text:
        return ""

    # Whisperが無音・静音時に返す既知の幻覚テキストをフィルタリング
    _HALLUCINATIONS = {
        "ご視聴ありがとうございました",
        "ご視聴ありがとうございます",
        "ありがとうございました",
        "ありがとうございます",
        "字幕は自動生成されています",
        "字幕制作",
        "お聞きください",
        "以上です",
        "Thank you for watching.",
        "Thanks for watching.",
        "Please subscribe.",
        "Subscribe.",
        ".",
        "。",
        "...",
        "…",
        "はい",
        "はい。",
        "うん",
        "うん。",
        "えー",
        "えーと",
        "あー",
        "あ",
        "え",
        "う",
        "ん",
        "ねー",
        "ね",
        "あのー",
        "あの",
        "まあ",
        "そうですね",
        "そうです",
        "よろしくお願いします",
        "よろしくお願いいたします",
        "失礼します",
        "失礼いたします",
        "お願いします",
    }
    normalized = raw_text.strip().rstrip("。．.、, 　")
    if raw_text in _HALLUCINATIONS or normalized in _HALLUCINATIONS:
        return ""

    meaningful = "".join(c for c in normalized if c.strip() and c not in "。、．，！？!?「」『』【】…・ー～")
    if len(meaningful) < 2:
        return ""

    raw_text = _remove_fillers(raw_text)
    if not raw_text:
        return ""

    corrected = apply_corrections(raw_text)

    # 置換ルールをClaude処理の前にも適用（完全一致ワードをAIに渡す前に変換）
    from replacements import apply_replacements

    corrected = apply_replacements(corrected)

    # 言い直し修正 + カスタム指示によるClaude後処理
    from instructions_window import load_custom_instructions

    # 辞書の単語をプロンプトに含める
    from dictionary import load_dictionary

    dict_words = load_dictionary()
    dict_section = ""
    if dict_words:
        dict_section = (
            "\n\n【4. 辞書（固有名詞・専門用語）】\n"
            "以下の単語が音声に含まれている可能性が高いです。音が近い場合はこれらの表記を優先してください:\n"
            + "、".join(dict_words)
        )

    # 置換ルールもヒントとしてプロンプトに含める
    from replacements import load_replacements

    repl_rules = load_replacements()
    repl_section = ""
    if repl_rules:
        repl_examples = [f"「{r['from']}」→「{r['to']}」" for r in repl_rules if r.get("from") and r.get("to")]
        if repl_examples:
            repl_section = (
                "\n\n【5. 自動置換ルール】\n"
                "以下の変換が登録されています。該当する表現があればこの通りに変換してください:\n"
                + "、".join(repl_examples)
            )

    # 学習済み修正履歴をプロンプトに含める（Claudeが学習済みの修正を上書きしないように）
    from config import load_vocabulary

    vocab = load_vocabulary()
    learned_section = ""
    phrases = vocab.get("_phrases", {})
    if phrases:
        # 直近20件のフレーズ修正を含める
        recent_phrases = list(phrases.items())[-20:]
        learned_examples = [f"「{orig}」→「{corr}」" for orig, corr in recent_phrases]
        learned_section = (
            "\n\n【6. ユーザーが過去に修正した履歴（最優先）】\n"
            "以下はユーザーが手動で修正した履歴です。同じ表現が出たら必ずこの修正を適用してください。"
            "ユーザーの修正を覆さないでください:\n"
            + "\n".join(learned_examples)
        )
    # 単語レベルの修正も含める
    word_fixes = {k: v for k, v in vocab.items() if k != "_phrases" and isinstance(v, dict)}
    if word_fixes:
        word_examples = []
        for wrong, candidates in list(word_fixes.items())[-15:]:
            best = max(candidates, key=lambda k: candidates[k])
            word_examples.append(f"「{wrong}」→「{best}」")
        if word_examples:
            learned_section += (
                "\n\n【7. 単語修正履歴（最優先）】\n"
                + "、".join(word_examples)
            )

    _REPHRASE_INSTRUCTION = (
        "あなたは音声入力の後処理アシスタントです。以下の修正を行ってください:\n"
        "\n"
        "【1. 言い直し修正】\n"
        "訂正表現があれば最終的な意図だけを残す。\n"
        "例: 「明日の…いや、明後日の会議」→「明後日の会議」\n"
        "「3時に…あ、4時に集合」→「4時に集合」\n"
        "「田中さんに…じゃなくて山田さんに連絡」→「山田さんに連絡」\n"
        "\n"
        "【2. 言い間違い・誤認識の修正】\n"
        "文脈上明らかに意味が通らない箇所を、最も自然な表現に修正する。\n"
        "同じ単語の不自然な繰り返し、音が似ているが意味が通らない語、文脈と矛盾する表現を修正する。\n"
        "ただし、意図的な強調や対比（「人は人、自分は自分」等）は修正しない。\n"
        "\n"
        "【3. 漢字変換・固有名詞の修正】\n"
        "- ひらがなのままになっている箇所を、文脈に合った正しい漢字に変換する\n"
        "- 固有名詞（人名・地名・サービス名・技術用語）は正しい表記にする\n"
        "- 例: 「くろーどこーど」→「Claude Code」、「とうきょうと」→「東京都」\n"
        "- 例: 「ぐーぐる」→「Google」、「らいん」→「LINE」\n"
        "- 同音異義語は文脈から最も適切な漢字を選ぶ\n"
        "- 例: 「きかん」→ 期間/機関/器官/帰還（文脈で判断）\n"
        + dict_section
        + repl_section
        + learned_section
        + "\n\n"
        "【共通ルール】\n"
        "- 修正不要ならそのまま返す\n"
        "- 余計な説明や装飾は一切加えず、修正後のテキストだけを返す\n"
        "- 元の意図をできるだけ忠実に保つ（大幅な書き換えはしない）"
    )

    custom_instructions = load_custom_instructions()
    system_prompt = _REPHRASE_INSTRUCTION
    if custom_instructions:
        system_prompt += "\n\nさらに以下のスタイル指示にも従ってください:\n" + custom_instructions

    # 自動整形モード
    fmt_mode = config.get("auto_format_mode", "off")
    if fmt_mode and fmt_mode != "off":
        from ai_actions import get_format_instruction
        fmt_instruction = get_format_instruction(fmt_mode)
        if fmt_instruction:
            system_prompt += "\n\n" + fmt_instruction

    try:
        client = _get_client()
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": corrected}],
        )
        refined = resp.content[0].text
        if refined and refined.strip():
            corrected = refined.strip()
    except Exception:
        pass

    # アプリ別フォーマット・文体反映
    if config.get("app_format_enabled") or config.get("style_learn_enabled") or config.get("app_rules"):
        from app_formatter import format_for_app

        corrected = format_for_app(corrected, target_pid=target_pid)

    # 自動置換ルールを適用
    from replacements import apply_replacements

    corrected = apply_replacements(corrected)

    return corrected
