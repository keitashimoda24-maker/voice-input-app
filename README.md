# voice-input-app

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![macOS](https://img.shields.io/badge/macOS-Apple%20Silicon-black.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)

A macOS menu-bar **speech-to-text input** app: hold a hotkey, talk, and your words are cleaned
up and pasted into whatever app has focus. Transcription runs **locally** (Apple-Silicon Whisper
via `mlx-whisper`); an optional Claude pass handles formatting, corrections, and "do something with
this" AI actions.

A real, shipped desktop app (~35 modules). All keys live in the macOS Keychain — nothing secret is
committed.

## What it does

- **Push-to-talk transcription** — global hotkey starts/stops capture; result is pasted at the cursor.
- **Local-first ASR** — `mlx-whisper` runs on-device on Apple Silicon (low latency, private). No
  audio leaves the machine for transcription.
- **AI cleanup & actions** — an optional Claude pass fixes punctuation/filler, applies a learned
  correction dictionary, and can run "AI actions" on the dictated text (rewrite, summarize, etc.).
- **Learns your vocabulary** — a personal dictionary plus a post-paste learner adapt to the terms
  and corrections you actually use.
- **Brain-dump & formatting windows** — capture long-form thoughts and reshape them.
- **Calendar helper** — turn dictated plans into calendar entries.
- **Privacy-conscious** — explicit consent dialog and a stated privacy policy; transcription stays local.

## Architecture (highlights)

| Area | Modules |
|---|---|
| Capture & ASR | `realtime_transcriber.py`, `transcriber.py`, `main.py` |
| Text shaping | `app_formatter.py`, `correction_window.py`, `dictionary.py` |
| AI actions | `ai_actions.py`, `deep_context.py` |
| Learning | `learning.py`, `post_paste_learner.py` |
| UX / windows | `braindump_window.py`, `dictionary_window.py`, `cursor_indicator.py`, menu icons |
| Integrations | `calendar_manager.py` |
| Privacy | `consent_dialog.py`, `privacy_policy.py` |
| Config & keys | `config.py` (Anthropic key stored in macOS Keychain) |

## Requirements

macOS on Apple Silicon (for `mlx-whisper`). Python 3.10+.

```bash
pip install -r requirements.txt   # PyQt6, anthropic, mlx-whisper, sounddevice, numpy, scipy, pyperclip, pynput
./setup.sh        # one-time setup
./run.sh          # launch the menu-bar app
```

The Anthropic API key (for the optional AI pass) is read from the macOS Keychain, an env var, or
entered in-app — never written to a committed file.

## Notes

- Transcription is on-device; only the optional AI-cleanup step calls the Claude API, and only with
  the dictated text you choose to process.
- This is a personal-productivity app shared as a reference implementation; review the consent and
  privacy modules before distributing.

## License

MIT — see [LICENSE](LICENSE).
