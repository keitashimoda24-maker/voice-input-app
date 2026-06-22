"""Standalone mlx-whisper worker — runs in a subprocess to avoid GIL blocking the UI."""

import json
import sys


def main():
    """Read JSON args from stdin, run mlx_whisper, write JSON result to stdout."""
    try:
        args = json.loads(sys.stdin.read())
    except Exception:
        json.dump({"text": "", "error": "invalid input"}, sys.stdout)
        return

    audio_path = args.get("audio_path", "")
    language = args.get("language", "ja")
    prompt = args.get("prompt", "")
    model = args.get("model", "mlx-community/whisper-large-v3-turbo")

    if not audio_path:
        json.dump({"text": "", "error": "no audio_path"}, sys.stdout)
        return

    try:
        import mlx_whisper

        kwargs = {"path_or_hf_repo": model, "verbose": False}
        if language and language != "auto":
            kwargs["language"] = language
        if prompt:
            kwargs["initial_prompt"] = prompt

        result = mlx_whisper.transcribe(audio_path, **kwargs)
        text = (result.get("text", "") or "").strip()
        json.dump({"text": text}, sys.stdout)
    except Exception as e:
        json.dump({"text": "", "error": str(e)}, sys.stdout)


if __name__ == "__main__":
    main()
