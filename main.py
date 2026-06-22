"""Voice Input App - macOS menubar application for speech-to-text input."""

import fcntl
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

_PID_DIR = Path.home() / ".voice_input_app"


def _install_excepthook():
    """PyQt6のスロット内で未処理例外が発生した際にqFatal()→abort()されるのを防ぐ。
    代わりにログに書き出して続行する。"""
    def _hook(exc_type, exc_value, exc_tb):
        import traceback
        try:
            log_file = _PID_DIR / "error.log"
            _PID_DIR.mkdir(mode=0o700, exist_ok=True)
            with open(log_file, "a") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Unhandled exception in slot:\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
        except Exception:
            pass
        # stderrにも出力（デバッグ用）
        traceback.print_exception(exc_type, exc_value, exc_tb)
    sys.excepthook = _hook


_install_excepthook()
_PID_FILE = str(_PID_DIR / "pid.lock")


def _kill_all_existing() -> None:
    """このアプリの既存プロセスだけを終了させる。

    広い `pgrep -f main.py` は無関係なPythonプロセスを誤終了させる可能性があるため、
    PIDファイルと現在の `main.py` 絶対パスに一致するプロセスだけを対象にする。
    """
    my_pid = os.getpid()

    pids = set()
    app_main = os.path.abspath(__file__)

    try:
        r = subprocess.run(["pgrep", "-f", app_main], capture_output=True, text=True)
        for p in r.stdout.strip().split():
            if p and int(p) != my_pid:
                pids.add(int(p))
    except Exception:
        pass

    # PIDファイルからも取得
    try:
        with open(_PID_FILE) as f:
            old_pid = int(f.read().strip())
        if old_pid != my_pid:
            pids.add(old_pid)
    except Exception:
        pass

    pids = list(pids)

    if not pids:
        return

    # SIGTERM で穏やかに終了
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

    # 最大 2 秒待つ
    deadline = time.time() + 2.0
    remaining = list(pids)
    while remaining and time.time() < deadline:
        time.sleep(0.1)
        still_alive = []
        for pid in remaining:
            try:
                os.kill(pid, 0)
                still_alive.append(pid)
            except ProcessLookupError:
                pass
        remaining = still_alive

    # まだ生きているプロセスは SIGKILL
    for pid in remaining:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    if remaining:
        time.sleep(0.3)


_lock_fd = None  # fcntlロック用ファイルディスクリプタ


def _write_pid() -> None:
    """自プロセスのPIDをファイルに書き込み、排他ロックを取得する。"""
    global _lock_fd
    try:
        _PID_DIR.mkdir(mode=0o700, exist_ok=True)
        _lock_fd = open(_PID_FILE, "w")
        fcntl.flock(_lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fd.write(str(os.getpid()))
        _lock_fd.flush()
        os.chmod(_PID_FILE, 0o600)
    except Exception:
        _log("PIDロック取得失敗。既存プロセスが起動中の可能性があるため終了します。")
        sys.exit(1)


def _release_pid():
    """PIDファイルのロックを解放して削除する。"""
    global _lock_fd
    try:
        if _lock_fd:
            fcntl.flock(_lock_fd.fileno(), fcntl.LOCK_UN)
            _lock_fd.close()
            _lock_fd = None
    except Exception:
        pass
    try:
        os.unlink(_PID_FILE)
    except Exception:
        pass


def _check_consent(app) -> bool:
    """初回起動時にプライバシーポリシー同意画面を表示。同意済みならTrue。"""
    from config import load_config, save_config

    config = load_config()
    if config.get("consent_accepted"):
        return True

    # 同意画面表示のためActivationPolicyを一時的にAccessoryに変更
    try:
        import AppKit

        AppKit.NSApplication.sharedApplication().setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    except Exception:
        pass

    from consent_dialog import ConsentDialog

    dialog = ConsentDialog()
    dialog.exec()

    if dialog.user_accepted:
        config["consent_accepted"] = True
        save_config(config)
        # Prohibitedに戻す
        try:
            import AppKit

            AppKit.NSApplication.sharedApplication().setActivationPolicy_(
                AppKit.NSApplicationActivationPolicyProhibited
            )
        except Exception:
            pass
        return True
    return False


def _log(msg: str):
    """起動ログを ~/.voice_input_app/startup.log に書き出す（フリーズ診断用）。"""
    try:
        log_file = _PID_DIR / "startup.log"
        _PID_DIR.mkdir(mode=0o700, exist_ok=True)
        with open(log_file, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass


def _force_restart():
    """プロセスを強制終了して新しいインスタンスを起動する（フリーズ回復用）。"""
    _log("!!! ウォッチドッグ: フリーズ検出 → 強制再起動 !!!")
    try:
        app_dir = os.path.dirname(os.path.abspath(__file__))
        venv_python = os.path.join(app_dir, "venv", "bin", "python3")
        python_exe = venv_python if os.path.exists(venv_python) else sys.executable
        subprocess.Popen(
            [python_exe, os.path.join(app_dir, "main.py")],
            cwd=app_dir,
            start_new_session=True,
        )
    except Exception:
        pass
    os._exit(1)  # 即座に終了（デッドロック状態でも確実に終了）


class _Watchdog:
    """メインスレッド（Qtイベントループ）の応答性を監視するウォッチドッグ。
    メインスレッドのQTimerでタイムスタンプを更新し、
    バックグラウンドスレッドがそれを監視する（スレッドセーフ）。"""

    def __init__(self, timeout: float = 20.0):
        self._timeout = timeout
        self._last_heartbeat = time.time()
        self._timer = None  # メインスレッドのQTimer
        self._thread = None

    def start(self):
        """メインスレッドから呼ぶこと。"""
        # メインスレッドで定期的にタイムスタンプを更新するQTimer
        self._timer = QTimer()
        self._timer.timeout.connect(self._heartbeat)
        self._timer.start(5000)  # 5秒ごと
        self._last_heartbeat = time.time()

        # 監視スレッド
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()

    def _heartbeat(self):
        """メインスレッドのQTimerから呼ばれる。"""
        self._last_heartbeat = time.time()

    def _watch(self):
        """バックグラウンドスレッド: タイムスタンプを監視。"""
        time.sleep(15)  # 起動直後の初期化を待つ（30→15秒に短縮）
        _log("ウォッチドッグ: 監視開始")

        consecutive_failures = 0
        while True:
            time.sleep(10)
            elapsed = time.time() - self._last_heartbeat
            if elapsed < self._timeout:
                consecutive_failures = 0
            else:
                consecutive_failures += 1
                # フリーズ時のスレッド情報を記録
                import sys
                import traceback
                thread_info = []
                for tid, frame in sys._current_frames().items():
                    thread_info.append(f"  Thread {tid}:")
                    for line in traceback.format_stack(frame, limit=5):
                        thread_info.append("    " + line.strip())
                _log(f"ウォッチドッグ: メインスレッド無応答 {elapsed:.0f}秒 ({consecutive_failures}回目)\n" + "\n".join(thread_info))
                if consecutive_failures >= 2:
                    _force_restart()


def main():
    # 既存インスタンスを全て終了させてから起動
    _log("=== 起動開始 ===")
    _kill_all_existing()
    _write_pid()
    _log("PID書き込み完了")

    # QApplication 生成前にポリシー設定（メニューバー/Dockにアイコンを出さない）
    try:
        import AppKit

        # Prohibited: Dockにもメニューバーにもアイコンを出さない
        AppKit.NSApplication.sharedApplication().setActivationPolicy_(AppKit.NSApplicationActivationPolicyProhibited)
    except Exception:
        pass

    _log("QApplication生成開始")
    app = QApplication(sys.argv)
    app.setApplicationName("音声入力")
    app.setQuitOnLastWindowClosed(False)
    app.aboutToQuit.connect(_release_pid)
    _log("QApplication生成完了")

    # 初回起動時の同意確認
    if not _check_consent(app):
        _release_pid()
        sys.exit(0)

    _log("TrayApp初期化開始")
    from tray_app import VoiceInputTrayApp

    tray = VoiceInputTrayApp(app)  # noqa: F841 - must stay in scope
    _log("TrayApp初期化完了 - イベントループ開始")

    # ウォッチドッグ起動（メインスレッドのフリーズを検出して自動再起動）
    watchdog = _Watchdog(timeout=20.0)
    watchdog.start()  # メインスレッドからQTimerを起動
    _log("ウォッチドッグ起動")

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    # SIGTERM でも Qt を正常終了させる（トレイアイコンの残骸防止）
    signal.signal(signal.SIGTERM, lambda *_: app.quit())
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
