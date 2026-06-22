"""画面コンテキスト取得 — スクリーンショットからキーワードを抽出してWhisper精度を向上させる。"""

import base64
import os
import subprocess
import tempfile


def capture_screen_context() -> str:
    """スクリーンショットを撮影し、Claude visionでキーワードを抽出する。
    タイムアウト5秒。エラー時は空文字を返す（録音をブロックしない）。"""
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        subprocess.run(["screencapture", "-x", "-C", tmp_path], timeout=3, capture_output=True)
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
            return ""

        with open(tmp_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        from config import get_api_key

        api_key = get_api_key()
        if not api_key:
            return ""

        from anthropic import Anthropic

        client = Anthropic(api_key=api_key, timeout=5.0)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            system="画面に表示されているテキストから、音声認識の精度向上に役立つ固有名詞・専門用語・キーワードをカンマ区切りで抽出してください。最大30語。余計な説明は不要です。",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": img_b64,
                            },
                        }
                    ],
                },
            ],
        )
        keywords = response.content[0].text.strip()
        return keywords
    except Exception:
        return ""
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
