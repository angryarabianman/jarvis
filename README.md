# Jarvis

You can find screen recordings in the repository.

AI voice assistant powered by [Nebius AI Studio](https://studio.nebius.com/).

## Implemented Features

| Feature | Details |
|---------|---------|
| Language Models Integration | Nebius AI Studio API (Llama 3.3 70B by default) with full tool-calling support |
| Handling Dialogue | Multi-turn conversation with in-session history (ChatSession) |
| Voice Recognition Integration | Microphone input transcribed via `faster-whisper` (Whisper STT), hands-free mode |
| Voice Generation Integration | Spoken responses via macOS `say` (built-in TTS), configurable voice and rate |
| Long-term Memory with Updatable Database | All conversations persisted to SQLite (`~/.jarvis/memory.db`); last 20 turns injected into each new session |
| Short-term Memory | Full in-session conversation history passed to the model on every turn |
| Routing and Tools | Agentic loop: model decides which tool to call based on user intent |
| Routing and Actions | `open_application` and `close_application` tools executed via native OS APIs |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-voice.txt  # for voice input
```

Create `.env` in the project root:

```
nebius_api_key=your_key_here
```

## Run

```bash
# Text chat
python jarvis.py

# Text chat with app actions (open/close apps)
python jarvis.py --allow-actions

# Voice input + spoken responses + actions (full mode)
python jarvis.py --voice-input --hands-free --voice-output --allow-actions
```

## Parameters

| Flag | Default | Description |
|------|---------|-------------|
| `--model` | `meta-llama/Llama-3.3-70B-Instruct` | Model name from Nebius |
| `--allow-actions` | off | Enable open/close app commands |
| `--voice-input` | off | Microphone input via Whisper STT |
| `--hands-free` | off | Continuous listen loop, no Enter needed (requires `--voice-input`) |
| `--voice-output` | off | Speak responses aloud via TTS |
| `--tts-voice` | system default | TTS voice name. Run `say -v ?` to list macOS voices |
| `--tts-rate` | `180` | Speech rate in words per minute |
| `--stt-model` | `base` | Whisper model: `tiny` / `base` / `small` / `medium` / `large-v3` |
| `--stt-language` | `en` | STT language code, or `auto` for auto-detection |
| `--stt-device` | `auto` | Device for Whisper: `auto` / `cpu` / `cuda` |
| `--record-seconds` | `5` | Mic recording duration per turn |
| `--silence-threshold` | `300` | Peak amplitude below which audio is treated as silence |

## Chat commands

- `/exit` — quit
- `/reset` — clear conversation history
- `/save` — save chat log to `chat_log_<timestamp>.json`

In hands-free mode say: `jarvis exit`, `jarvis reset`, `jarvis save`
