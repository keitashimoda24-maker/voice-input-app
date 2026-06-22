"""AI learning: stores correction history and generates Whisper prompts locally."""

import re
import threading
from collections import Counter
from datetime import datetime

from config import (
    load_config,
    load_history,
    load_vocabulary,
    load_whisper_prompt,
    save_history,
    save_vocabulary,
    save_whisper_prompt,
)

# GPTによる学習プロンプト再生成は何件修正ごとに行うか
REGEN_EVERY = 3


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def learn_correction(original: str, corrected: str):
    """修正ペアを保存し、必要に応じてGPTで学習プロンプトを再生成する。"""
    orig = original.strip()
    corr = corrected.strip()
    if not orig or orig == corr:
        return

    # ── 1. 修正履歴に追加 ──
    history = load_history()
    history.append(
        {
            "at": datetime.now().isoformat(timespec="seconds"),
            "original": orig,
            "corrected": corr,
        }
    )
    save_history(history)

    # ── 2. 従来の単語/フレーズ置換辞書も更新 ──
    vocab = load_vocabulary()
    orig_tok = _tokenize(orig)
    corr_tok = _tokenize(corr)
    if len(orig_tok) == len(corr_tok):
        for ow, cw in zip(orig_tok, corr_tok):
            if ow != cw and len(ow) > 1:
                vocab.setdefault(ow, {})[cw] = vocab.get(ow, {}).get(cw, 0) + 1
    if len(orig) < 60:
        vocab.setdefault("_phrases", {})[orig] = corr
    save_vocabulary(vocab)

    # ── 3. REGEN_EVERY 件ごとにバックグラウンドでGPT学習 ──
    if len(history) % REGEN_EVERY == 0:
        threading.Thread(target=_regenerate_prompt, daemon=True).start()


def _regenerate_prompt():
    """修正履歴からローカルでキーワードを抽出し、Whisper用プロンプトを生成・保存する。
    プライバシー保護: 修正履歴を外部APIに送信しない。
    """
    try:
        history = load_history()
        if not history:
            return

        # 直近30件の「正解側」からキーワードを抽出（ローカル処理）
        recent = history[-30:]
        keywords = set()
        for h in recent:
            corrected = h.get("corrected", "")
            original = h.get("original", "")
            # 修正で変わった部分（正解側の単語）を抽出
            corr_tokens = set(_tokenize(corrected))
            orig_tokens = set(_tokenize(original))
            diff_tokens = corr_tokens - orig_tokens
            for token in diff_tokens:
                # 2文字以上の単語のみ（助詞等を除外）
                if len(token) >= 2:
                    keywords.add(token)

        if keywords:
            # 頻出順にソートして上位20個、50文字以内に収める
            all_tokens = []
            for h in recent:
                corr_tokens = set(_tokenize(h.get("corrected", "")))
                orig_tokens = set(_tokenize(h.get("original", "")))
                all_tokens.extend(corr_tokens - orig_tokens)
            freq = Counter(t for t in all_tokens if len(t) >= 2)
            sorted_keywords = [w for w, _ in freq.most_common(20)]
            prompt = ", ".join(sorted_keywords)
            if len(prompt) > 50:
                # 50文字以内に収まるまで末尾を削る
                while len(prompt) > 50 and sorted_keywords:
                    sorted_keywords.pop()
                    prompt = ", ".join(sorted_keywords)
            if prompt:
                save_whisper_prompt(prompt)

    except Exception:
        pass  # 失敗してもアプリの動作には影響しない


def _load_team_vocab() -> dict:
    """チーム語彙ファイルを読み込む。パストラバーサル対策あり。"""
    import json
    from pathlib import Path

    config = load_config()
    team_path = config.get("team_vocab_path", "").strip()
    if not team_path:
        return {}
    try:
        p = Path(team_path).resolve()
        home = Path.home().resolve()
        # ホームディレクトリ外のファイルはブロック（パストラバーサル防止）
        if not str(p).startswith(str(home)):
            return {}
        if p.exists() and p.suffix == ".json":
            with open(p, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def apply_corrections(text: str) -> str:
    """学習済み辞書（個人 + チーム）をテキストに適用する。"""
    vocab = load_vocabulary()
    team_vocab = _load_team_vocab()

    # チーム語彙をマージ（個人語彙が優先）
    merged_phrases = {**team_vocab.get("_phrases", {}), **vocab.get("_phrases", {})}
    for wrong, right in merged_phrases.items():
        text = text.replace(wrong, right)

    def fix(token):
        # 個人語彙を優先、なければチーム語彙
        cands = vocab.get(token, {})
        if cands:
            best = max(cands, key=lambda k: cands[k])
            if cands[best] >= 1:
                return best
        team_cands = team_vocab.get(token, {})
        if team_cands and isinstance(team_cands, dict):
            best = max(team_cands, key=lambda k: team_cands[k])
            if team_cands[best] >= 1:
                return best
        return token

    tokens = _tokenize(text)
    return " ".join(fix(t) for t in tokens) if tokens else text


def get_vocabulary_stats() -> dict:
    vocab = load_vocabulary()
    history = load_history()
    prompt = load_whisper_prompt()
    return {
        "word_substitutions": len([k for k in vocab if k != "_phrases"]),
        "phrase_substitutions": len(vocab.get("_phrases", {})),
        "correction_history": len(history),
        "whisper_prompt": prompt,
    }


def force_regenerate():
    """手動でGPT学習プロンプトを再生成する。"""
    threading.Thread(target=_regenerate_prompt, daemon=True).start()
