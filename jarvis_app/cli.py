import argparse
import os
import sys

from jarvis_app.chat import AppConfig, run_chat
from jarvis_app.providers import DEFAULT_MODEL
from jarvis_app.voice import VoiceConfig


def _load_dotenv(path: str = ".env") -> None:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip().upper()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except FileNotFoundError:
        pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jarvis: terminal AI assistant powered by Nebius.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model name (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--voice-input",
        action="store_true",
        help="Enable microphone input and speech transcription.",
    )
    parser.add_argument(
        "--hands-free",
        action="store_true",
        help="Continuous voice conversation mode (no Enter key per turn). Requires --voice-input.",
    )
    parser.add_argument(
        "--allow-actions",
        action="store_true",
        help="Allow local device actions (e.g. 'open chrome', 'close safari').",
    )
    parser.add_argument(
        "--continue",
        dest="continue_session",
        action="store_true",
        help="Continue previous session by loading past conversations from memory.",
    )
    parser.add_argument(
        "--voice-output",
        action="store_true",
        help="Enable spoken responses via text-to-speech.",
    )
    parser.add_argument(
        "--tts-voice",
        default=None,
        help="TTS voice name. On macOS: 'Samantha', 'Daniel', 'Alex', etc. Run `say -v ?` to list all.",
    )
    parser.add_argument(
        "--tts-rate",
        type=int,
        default=180,
        help="TTS speech rate in words per minute (default: 180).",
    )
    parser.add_argument(
        "--stt-model",
        default="base",
        help="faster-whisper model name (tiny/base/small/medium/large-v3).",
    )
    parser.add_argument(
        "--stt-device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Device for faster-whisper.",
    )
    parser.add_argument(
        "--stt-compute-type",
        default="int8",
        help="Compute type for faster-whisper (int8/float16/float32).",
    )
    parser.add_argument(
        "--stt-language",
        default="en",
        help="STT language code (default: en). Use 'auto' for automatic language detection.",
    )
    parser.add_argument(
        "--record-seconds",
        type=int,
        default=5,
        help="Microphone recording length per turn.",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Microphone sample rate.",
    )
    parser.add_argument(
        "--silence-threshold",
        type=int,
        default=300,
        help="Peak int16 level below which a chunk is treated as silence in hands-free mode.",
    )
    return parser.parse_args()


def main() -> int:
    _load_dotenv()
    args = parse_args()
    if args.hands_free and not args.voice_input:
        print("Error: --hands-free requires --voice-input.", file=sys.stderr)
        return 2

    voice_config = None
    if args.voice_input:
        stt_language = None if args.stt_language.lower() == "auto" else args.stt_language.lower()
        voice_config = VoiceConfig(
            model=args.stt_model,
            device=args.stt_device,
            compute_type=args.stt_compute_type,
            language=stt_language,
            record_seconds=args.record_seconds,
            sample_rate=args.sample_rate,
            silence_threshold=args.silence_threshold,
        )

    config = AppConfig(
        model=args.model,
        voice_input=args.voice_input,
        voice_output=args.voice_output,
        hands_free=args.hands_free,
        allow_actions=args.allow_actions,
        continue_session=args.continue_session,
        voice_config=voice_config,
        tts_voice=args.tts_voice,
        tts_rate=args.tts_rate,
    )

    try:
        run_chat(config=config)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
