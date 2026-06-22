"""録音開始・停止などのサウンドをnumpyで生成してキャッシュ再生する。
sound_genre 設定で録音開始音のジャンルを切り替え可能:
  "coin"    : コイン弾き（明るい金属音）
  "ping"    : ソナーピン（純音・余韻）
  "strum"   : ギターコードストラム
  "knock"   : ノック（短い打撃音）
  "flutter" : フラッター（トレモロ振動）
  "glass"   : グラスを叩く音
  "synth"   : シンセパッド短音
  "wood"    : 木琴単音
"""

import atexit
import os
import subprocess
import tempfile

import numpy as np
import scipy.io.wavfile as wav

_SR = 44100
_cache: dict[str, str] = {}  # kind -> tmp wav path


def _env(t: np.ndarray, attack: float = 0.01, decay: float = 1.0) -> np.ndarray:
    e = np.exp(-t * decay)
    fade = max(1, int(_SR * attack))
    e[:fade] *= np.linspace(0, 1, fade)
    return e


# ── 録音開始音（ジャンル別）─────────────────────────────────────────────────


def _make_start_coin() -> np.ndarray:
    """Coin: コインを弾いた明るい金属音（0.20s）"""
    n = int(_SR * 0.20)
    t = np.arange(n) / _SR
    # 金属の非整数倍音（2.76, 5.40, 8.93 倍がコイン的）
    f0 = 3200.0
    tone = (
        np.sin(2 * np.pi * f0 * t) * 0.50
        + np.sin(2 * np.pi * f0 * 2.76 * t) * 0.25
        + np.sin(2 * np.pi * f0 * 1.41 * t) * 0.20
        + np.sin(2 * np.pi * f0 * 0.55 * t) * 0.05  # 低域のコクを足す
    )
    env1 = np.exp(-t * 25.0)
    env2 = np.exp(-t * 8.0)
    mixed = (
        np.sin(2 * np.pi * f0 * t) * 0.50 * env1
        + np.sin(2 * np.pi * f0 * 2.76 * t) * 0.25 * env1
        + np.sin(2 * np.pi * f0 * 1.41 * t) * 0.20 * env2
        + np.sin(2 * np.pi * f0 * 0.55 * t) * 0.05 * env2
    )
    fade_in = int(_SR * 0.001)
    mixed[:fade_in] *= np.linspace(0, 1, fade_in)
    audio = mixed * 0.26
    audio[-int(_SR * 0.02) :] *= np.linspace(1, 0, int(_SR * 0.02))
    return audio


def _make_start_ping() -> np.ndarray:
    """Ping: ソナーのような純音（余韻あり, 0.38s）"""
    n = int(_SR * 0.38)
    t = np.arange(n) / _SR
    # 純音 + 微細なビブラートが徐々に消える
    vib_depth = np.exp(-t * 5.0) * 8.0
    phase = 2 * np.pi * np.cumsum(1760.0 + vib_depth * np.sin(2 * np.pi * 8.0 * t)) / _SR
    tone = np.sin(phase)
    audio = tone * _env(t, attack=0.004, decay=5.5) * 0.22
    audio[-int(_SR * 0.04) :] *= np.linspace(1, 0, int(_SR * 0.04))
    return audio


def _make_start_strum() -> np.ndarray:
    """Strum: ギターCコード（C-E-G-C を素早くアルペジオ, 0.30s）"""
    n = int(_SR * 0.30)
    audio = np.zeros(n)
    for freq, offset_s in ((262, 0.000), (330, 0.018), (392, 0.036), (523, 0.054)):
        s = int(offset_s * _SR)
        e = n
        nt = np.arange(e - s) / _SR
        note = (
            np.sin(2 * np.pi * freq * nt) * 0.55
            + np.sin(2 * np.pi * freq * 2 * nt) * 0.28
            + np.sin(2 * np.pi * freq * 3 * nt) * 0.12
            + np.sin(2 * np.pi * freq * 4 * nt) * 0.05
        )
        env_n = np.exp(-nt * 7.0)
        fade = int(_SR * 0.002)
        env_n[:fade] *= np.linspace(0, 1, fade)
        audio[s:] += note * env_n
    audio *= 0.18
    audio[-int(_SR * 0.03) :] *= np.linspace(1, 0, int(_SR * 0.03))
    return audio


def _make_start_knock() -> np.ndarray:
    """Knock: コツンという短い打撃音（0.14s）"""
    n = int(_SR * 0.14)
    t = np.arange(n) / _SR
    # 低域の共鳴 + 打撃ノイズ
    np.random.seed(3)
    noise_len = int(0.006 * _SR)
    noise = np.zeros(n)
    noise[:noise_len] = np.random.randn(noise_len) * 0.6
    # 共鳴トーン（周波数が少し下降）
    freq = np.linspace(320, 180, n)
    phase = 2 * np.pi * np.cumsum(freq) / _SR
    resonance = np.sin(phase) * np.exp(-t * 30.0)
    audio = (noise * np.exp(-t * 60.0) + resonance) * 0.28
    audio[-int(_SR * 0.01) :] *= np.linspace(1, 0, int(_SR * 0.01))
    return audio


def _make_start_flutter() -> np.ndarray:
    """Flutter: トレモロ（音が細かく振動, 0.26s）"""
    n = int(_SR * 0.26)
    t = np.arange(n) / _SR
    # トレモロ: 振幅を18Hzで変調
    tremolo = (1.0 + np.sin(2 * np.pi * 18.0 * t)) * 0.5
    tone = (
        np.sin(2 * np.pi * 1047 * t) * 0.65  # C6
        + np.sin(2 * np.pi * 1319 * t) * 0.35  # E6
    )
    audio = tone * tremolo * _env(t, attack=0.006, decay=6.0) * 0.22
    audio[-int(_SR * 0.03) :] *= np.linspace(1, 0, int(_SR * 0.03))
    return audio


def _make_start_glass() -> np.ndarray:
    """Glass: クリスタルグラスを叩く音（0.34s）"""
    n = int(_SR * 0.34)
    t = np.arange(n) / _SR
    # ガラス: 基音 + わずかにずれた倍音（共鳴ビート感）
    f0 = 2200.0
    tone = (
        np.sin(2 * np.pi * f0 * t) * 0.55
        + np.sin(2 * np.pi * f0 * 2.02 * t) * 0.28  # 微妙にずれた2倍音
        + np.sin(2 * np.pi * f0 * 3.01 * t) * 0.12
        + np.sin(2 * np.pi * f0 * 0.50 * t) * 0.05
    )
    audio = tone * _env(t, attack=0.002, decay=7.0) * 0.20
    audio[-int(_SR * 0.04) :] *= np.linspace(1, 0, int(_SR * 0.04))
    return audio


def _make_start_synth() -> np.ndarray:
    """Synth: 温かいシンセパッド短音（0.28s）"""
    n = int(_SR * 0.28)
    t = np.arange(n) / _SR
    f0 = 440.0
    # 矩形波近似（奇数倍音列）＋フィルタ効果として高次倍音を抑制
    tone = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in [1, 3, 5, 7])
    # ソフトフィルタ: 倍音ごとに速く減衰させることで丸みを出す
    filtered = (
        np.sin(2 * np.pi * f0 * t) * 0.50 * np.exp(-t * 4.0)
        + np.sin(2 * np.pi * f0 * 3 * t) * 0.25 * np.exp(-t * 10.0)
        + np.sin(2 * np.pi * f0 * 5 * t) * 0.15 * np.exp(-t * 20.0)
        + np.sin(2 * np.pi * f0 * 7 * t) * 0.10 * np.exp(-t * 35.0)
    )
    fade_in = int(_SR * 0.010)
    filtered[:fade_in] *= np.linspace(0, 1, fade_in)
    audio = filtered * 0.26
    audio[-int(_SR * 0.03) :] *= np.linspace(1, 0, int(_SR * 0.03))
    return audio


def _make_start_wood() -> np.ndarray:
    """Wood: 木琴を叩いた単音（0.22s）"""
    n = int(_SR * 0.22)
    t = np.arange(n) / _SR
    f0 = 587.0  # D5
    # 木琴: 基音 + 4倍音強め（マリンバより高く硬め）
    mixed = (
        np.sin(2 * np.pi * f0 * t) * 0.60 * np.exp(-t * 10.0)
        + np.sin(2 * np.pi * f0 * 4 * t) * 0.30 * np.exp(-t * 30.0)
        + np.sin(2 * np.pi * f0 * 10 * t) * 0.10 * np.exp(-t * 50.0)
    )
    # 打撃感: 最初の数ミリ秒に微小ノイズ
    np.random.seed(5)
    click_len = int(0.004 * _SR)
    mixed[:click_len] += np.random.randn(click_len) * 0.08
    fade_in = int(_SR * 0.001)
    mixed[:fade_in] *= np.linspace(0, 1, fade_in)
    audio = mixed * 0.26
    audio[-int(_SR * 0.02) :] *= np.linspace(1, 0, int(_SR * 0.02))
    return audio


def _make_start_aqua() -> np.ndarray:
    """Aqua: 水滴が落ちる音（0.18s）"""
    n = int(_SR * 0.18)
    t = np.arange(n) / _SR
    # 高い純音が急速に減衰（水滴のポチャン感）
    freq = 2800 - 800 * t / 0.18
    phase = 2 * np.pi * np.cumsum(freq) / _SR
    tone = np.sin(phase) * 0.45
    tone += np.sin(phase * 2.01) * 0.20  # 微妙にずれた倍音（水の響き）
    attack = int(_SR * 0.002)
    env = np.exp(-t * 22.0)
    env[:attack] = np.linspace(0, 1, attack)
    audio = tone * env * 0.22
    audio[-int(_SR * 0.01):] *= np.linspace(1, 0, int(_SR * 0.01))
    return audio


_START_GENRES = {
    "coin": _make_start_coin,
    "ping": _make_start_ping,
    "strum": _make_start_strum,
    "knock": _make_start_knock,
    "flutter": _make_start_flutter,
    "glass": _make_start_glass,
    "synth": _make_start_synth,
    "wood": _make_start_wood,
    "aqua": _make_start_aqua,
}


# ── その他サウンド ────────────────────────────────────────────────────────────


def _make_stop() -> np.ndarray:
    """録音停止: 短い下降チャイム（0.22s）"""
    n = int(_SR * 0.22)
    audio = np.zeros(n)
    # G6 → E6 の短い2音下降（完了感のある音）
    for freq, offset_s, vol in ((1568, 0.00, 0.50), (1319, 0.08, 0.55)):
        s = int(offset_s * _SR)
        e = min(s + int(0.14 * _SR), n)
        nt = np.arange(e - s) / _SR
        note = (
            np.sin(2 * np.pi * freq * nt) * 0.60
            + np.sin(2 * np.pi * freq * 2 * nt) * 0.25
            + np.sin(2 * np.pi * freq * 3 * nt) * 0.10
        )
        note *= _env(nt, attack=0.003, decay=16.0) * vol
        audio[s:e] += note
    audio *= 0.22
    audio[-int(_SR * 0.02):] *= np.linspace(1, 0, int(_SR * 0.02))
    return audio


def _make_paste() -> np.ndarray:
    """貼り付け完了: 短いソフトクリック（0.12s）"""
    n = int(_SR * 0.12)
    t = np.arange(n) / _SR
    tone = (
        np.sin(2 * np.pi * 1047 * t) * 0.60  # C6
        + np.sin(2 * np.pi * 1319 * t) * 0.30  # E6
        + np.sin(2 * np.pi * 1568 * t) * 0.10  # G6
    )
    audio = tone * _env(t, attack=0.002, decay=28.0) * 0.16
    audio[-int(_SR * 0.02) :] *= np.linspace(1, 0, int(_SR * 0.02))
    return audio


def _make_calendar() -> np.ndarray:
    """カレンダー追加: 明るい上昇アルペジオ（0.28s）"""
    n = int(_SR * 0.28)
    audio = np.zeros(n)
    for freq, offset_s, vol in ((523, 0.00, 0.55), (659, 0.07, 0.50), (784, 0.14, 0.55)):
        s = int(offset_s * _SR)
        e = min(s + int(0.18 * _SR), n)
        nt = np.arange(e - s) / _SR
        note = np.sin(2 * np.pi * freq * nt) * _env(nt, attack=0.003, decay=14.0) * vol
        audio[s:e] += note
    audio *= 0.22
    audio[-int(_SR * 0.02) :] *= np.linspace(1, 0, int(_SR * 0.02))
    return audio


def _make_research() -> np.ndarray:
    """リサーチ: SFスキャンパルス×2（0.20s）"""
    n = int(_SR * 0.20)
    audio = np.zeros(n)
    for offset_s, freq in ((0.00, 660), (0.09, 990)):
        s = int(offset_s * _SR)
        e = min(s + int(0.08 * _SR), n)
        nt = np.arange(e - s) / _SR
        audio[s:e] += np.sin(2 * np.pi * freq * nt) * _env(nt, attack=0.002, decay=20.0) * 0.22
    audio[-int(_SR * 0.02) :] *= np.linspace(1, 0, int(_SR * 0.02))
    return audio


# ── 再生 ──────────────────────────────────────────────────────────────────────


def _get_genre() -> str:
    try:
        from config import load_config

        return load_config().get("sound_genre", "coin")
    except Exception:
        return "coin"


def _build(kind: str) -> str:
    """WAVファイルを生成してパスを返す。"""
    if kind == "start":
        genre = _get_genre()
        cache_key = f"start_{genre}"
        if cache_key in _cache:
            return _cache[cache_key]
        gen = _START_GENRES.get(genre, _make_start_coin)
        audio = gen()
    else:
        generators = {
            "stop": _make_stop,
            "paste": _make_paste,
            "calendar": _make_calendar,
            "research": _make_research,
        }
        if kind not in generators:
            return ""
        cache_key = kind
        if cache_key in _cache:
            return _cache[cache_key]
        audio = generators[kind]()

    audio_i16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    wav.write(tmp.name, _SR, audio_i16)
    tmp.close()
    _cache[cache_key] = tmp.name
    return tmp.name


def play(kind: str, genre: str | None = None):
    """指定サウンドを非同期再生。genre を指定するとそのジャンルで再生（試聴用）。"""
    if kind == "start" and genre is not None:
        cache_key = f"start_{genre}"
        if cache_key not in _cache:
            gen = _START_GENRES.get(genre, _make_start_coin)
            audio = gen()
            audio_i16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
            tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wav.write(tmp.name, _SR, audio_i16)
            tmp.close()
            _cache[cache_key] = tmp.name
        path = _cache[cache_key]
    else:
        path = _build(kind)
    if path:
        subprocess.Popen(
            ["afplay", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def clear_cache():
    """設定変更時にキャッシュをクリアして再生成させる。"""
    global _cache
    for path in _cache.values():
        try:
            os.unlink(path)
        except Exception:
            pass
    _cache = {}


atexit.register(clear_cache)
