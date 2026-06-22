"""Audio recording using sounddevice."""

import atexit
import os
import tempfile
import threading

import numpy as np
import scipy.io.wavfile as wavfile
import sounddevice as sd

from config import load_config

# 一時WAVファイルを追跡し、終了時に確実に削除する
_temp_files: list[str] = []


def _cleanup_temp_files():
    for f in _temp_files:
        try:
            os.unlink(f)
        except Exception:
            pass
    _temp_files.clear()


atexit.register(_cleanup_temp_files)


class AudioRecorder:
    def __init__(self):
        self._config = load_config()
        self._recording = False
        self._frames = []
        self._lock = threading.Lock()
        self._stream = None
        self._current_level = 0.0

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def current_level(self) -> float:
        """Return current audio level (0.0 - 1.0)."""
        return self._current_level

    def start(self):
        """Start recording audio."""
        self._config = load_config()
        sample_rate = self._config["sample_rate"]
        self._frames = []
        self._recording = True

        def callback(indata, frames, time, status):
            if self._recording:
                with self._lock:
                    self._frames.append(indata.copy())
                rms = float(np.sqrt(np.mean(indata**2)))
                self._current_level = min(rms * 8.0, 1.0)

        self._stream = sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", callback=callback)
        self._stream.start()

    def stop(self) -> str | None:
        """Stop recording and return path to WAV file, or None if no audio."""
        self._recording = False
        self._current_level = 0.0

        # フレームを先にコピー（ストリーム停止を待たない）
        with self._lock:
            frames = self._frames.copy()
        self._frames = []

        # ストリーム停止はバックグラウンドで非同期実行（WAV保存と並列）
        if self._stream:
            stream = self._stream
            self._stream = None

            def _stop_stream():
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    try:
                        stream.close()
                    except Exception:
                        pass
                    try:
                        stream.abort()
                    except Exception:
                        pass

            threading.Thread(target=_stop_stream, daemon=True).start()

        if not frames:
            return None

        audio_data = np.concatenate(frames, axis=0)
        sample_rate = self._config["sample_rate"]

        # 無音チェック: RMSが閾値以下なら送信しない（Whisper幻覚防止）
        rms = float(np.sqrt(np.mean(audio_data**2)))
        silence_threshold = self._config.get("silence_threshold", 0.02)
        if rms < silence_threshold:
            return None

        # Convert to int16 for WAV
        audio_int16 = (audio_data * 32767).astype(np.int16)

        # Save to temp file
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wavfile.write(tmp.name, sample_rate, audio_int16)
        _temp_files.append(tmp.name)
        return tmp.name
