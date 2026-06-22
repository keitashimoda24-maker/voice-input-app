"""Real-time transcription using macOS SFSpeechRecognizer."""

import atexit
import ctypes
import queue
import threading

from AVFoundation import AVAudioEngine
from Foundation import NSLocale
from Speech import (
    SFSpeechAudioBufferRecognitionRequest,
    SFSpeechRecognizer,
)

from config import load_config

_python_is_finalizing = False


def _mark_finalizing():
    global _python_is_finalizing
    _python_is_finalizing = True


atexit.register(_mark_finalizing)


class RealtimeTranscriber:
    """Uses macOS built-in speech recognition to show live transcription."""

    def __init__(self, on_update, on_error=None):
        self._on_update = on_update
        self._on_error = on_error or (lambda m: None)
        self._engine = None
        self._request = None
        self._task = None
        self._running = False
        self._recognizer = None
        # isFinal 後の再起動を ObjC コールバックスレッド外で行うためのキュー
        self._restart_queue = queue.Queue()

    def _restart_watcher(self):
        """isFinal を受け取ったら新しいタスクを起動する専用スレッド。
        ObjC コールバックスレッドでの PyObjC 生成を避けるために分離。"""
        while self._running:
            try:
                accumulated = self._restart_queue.get(timeout=0.3)
                if self._running:
                    self._start_task(accumulated)
            except queue.Empty:
                continue
            except Exception:
                continue

    def _start_task(self, accumulated: str = ""):
        """新しい認識リクエストとタスクを開始する。
        SFSpeechRecognizer は無音・発話区切りで isFinal=True を出し、
        タスクを自動終了するため、_restart_watcher から繰り返し呼ばれる。"""
        if not self._running or not self._recognizer:
            return
        try:
            request = SFSpeechAudioBufferRecognitionRequest.alloc().init()
            request.setShouldReportPartialResults_(True)
            # macOS 13+: 自動句読点を有効化
            try:
                request.setAddsPunctuation_(True)
            except Exception:
                pass  # macOS 12以前では未対応
            self._request = request  # tap_handler が新リクエストへ即書き込み開始

            def handler(result, error):
                if not self._running:
                    return
                if result:
                    seg_text = result.bestTranscription().formattedString()
                    is_final = bool(result.isFinal())
                    full_text = (accumulated + " " + seg_text).strip() if accumulated else seg_text
                    self._on_update(full_text, is_final)
                    if is_final and self._running:
                        # ObjC コールバックスレッドでは PyObjC を生成せず
                        # キューに積んで _restart_watcher に任せる
                        self._restart_queue.put(full_text)

            old_task = self._task
            self._task = self._recognizer.recognitionTaskWithRequest_resultHandler_(request, handler)
            # 古いタスクをキャンセル（二重実行防止）
            if old_task:
                try:
                    old_task.cancel()
                except Exception:
                    pass
        except Exception:
            pass

    def start(self):
        config = load_config()
        lang = config.get("language", "ja")
        locale_id = {"ja": "ja-JP", "en": "en-US", "zh": "zh-CN"}.get(lang, "ja-JP")

        recognizer = SFSpeechRecognizer.alloc().initWithLocale_(NSLocale.alloc().initWithLocaleIdentifier_(locale_id))
        if not recognizer or not recognizer.isAvailable():
            self._on_error("音声認識が利用できません")
            return

        self._recognizer = recognizer
        self._engine = AVAudioEngine.alloc().init()

        input_node = self._engine.inputNode()
        fmt = input_node.outputFormatForBus_(0)

        # tap_handler は CoreAudio IO スレッドから呼ばれるため、
        # self._running と self._request のチェックを最小限にし、
        # 例外で絶対にクラッシュしないようにする
        def tap_handler(buffer, when):
            try:
                if _python_is_finalizing or not self._running:
                    return
                req = self._request
                if req is None:
                    return
                gstate = ctypes.pythonapi.PyGILState_Ensure()
                try:
                    req.appendAudioPCMBuffer_(buffer)
                except Exception:
                    pass
                finally:
                    ctypes.pythonapi.PyGILState_Release(gstate)
            except Exception:
                pass

        self._tap_handler = tap_handler  # prevent GC
        input_node.installTapOnBus_bufferSize_format_block_(0, 1024, fmt, tap_handler)

        err_ptr = None
        self._engine.startAndReturnError_(err_ptr)
        self._running = True

        # 再起動専用スレッドを起動
        threading.Thread(target=self._restart_watcher, daemon=True).start()

        # 最初のタスクを開始
        self._start_task()

        atexit.register(self.stop)

    def stop(self):
        if not self._running and self._engine is None:
            return
        self._running = False  # tap_handler と _restart_watcher を即座に停止
        import time

        # ローカル変数にコピーしてからインスタンスをクリア
        # → tap_handler が self._request を読む前に None にする
        request = self._request
        self._request = None
        task = self._task
        self._task = None
        engine = self._engine
        self._engine = None
        self._recognizer = None

        # キューを先に空にする（_restart_watcher が新タスクを起動しないように）
        while not self._restart_queue.empty():
            try:
                self._restart_queue.get_nowait()
            except queue.Empty:
                break

        # IOスレッドが tap_handler を完了するのを待つ
        time.sleep(0.15)

        # 認識タスクを先に終了
        try:
            if request:
                request.endAudio()
        except Exception:
            pass
        try:
            if task:
                task.cancel()
        except Exception:
            pass

        # AVAudioEngine の安全な停止
        # デッドロック防止: 別スレッドで実行し、タイムアウト付きで待機
        if engine:
            stop_done = threading.Event()

            def _stop_engine():
                try:
                    engine.inputNode().removeTapOnBus_(0)
                except Exception:
                    pass
                time.sleep(0.1)
                try:
                    engine.pause()
                except Exception:
                    pass
                try:
                    engine.reset()
                except Exception:
                    pass
                try:
                    engine.stop()
                except Exception:
                    pass
                stop_done.set()

            threading.Thread(target=_stop_engine, daemon=True).start()
            # GILを解放しながら最大3秒待つ（デッドロック時はタイムアウトで先に進む）
            stop_done.wait(timeout=3.0)
