import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


class VoiceInputError(RuntimeError):
    pass


class NoSpeechDetected(VoiceInputError):
    pass


@dataclass
class VoiceConfig:
    model: str = "base"
    device: str = "auto"
    compute_type: str = "int8"
    language: Optional[str] = "en"
    record_seconds: int = 5
    sample_rate: int = 16000
    silence_threshold: int = 300


class FasterWhisperTranscriber:
    def __init__(
        self,
        model: str,
        device: str,
        compute_type: str,
        language: Optional[str],
    ) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            raise VoiceInputError(
                "Voice input dependencies are missing. "
                "Install with: python -m pip install -r requirements-voice.txt"
            ) from e

        self._model = WhisperModel(model, device=device, compute_type=compute_type)
        self._language = language

    def transcribe_file(self, audio_path: str) -> str:
        transcribe_kwargs = {"vad_filter": True, "task": "transcribe"}
        if self._language:
            transcribe_kwargs["language"] = self._language
        segments, _info = self._model.transcribe(audio_path, **transcribe_kwargs)
        text = " ".join(s.text.strip() for s in segments if s.text.strip()).strip()
        if not text:
            raise NoSpeechDetected("No speech detected in the recording.")
        return text


def record_wav(path: Path, seconds: int, sample_rate: int, announce: bool = True) -> Any:
    try:
        import sounddevice as sd
    except ImportError as e:
        raise VoiceInputError(
            "Microphone dependency is missing. Install with: python -m pip install -r requirements-voice.txt"
        ) from e

    if seconds <= 0:
        raise VoiceInputError("record_seconds must be > 0.")

    frames = int(seconds * sample_rate)
    if announce:
        print(f"Recording for {seconds}s...")
    try:
        audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="int16")
        sd.wait()
    except Exception as e:
        raise VoiceInputError(f"Microphone capture failed: {e}") from e

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio.tobytes())
    return audio


def _is_probably_silent(audio: Any, threshold: int) -> bool:
    if threshold <= 0:
        return False
    try:
        import numpy as np
    except ImportError:
        return False
    peak = int(np.max(np.abs(audio)))
    return peak < threshold


class VoiceSpeaker:
    def __init__(self, voice: Optional[str] = None, rate: int = 180) -> None:
        self._voice = voice
        self._rate = rate

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        if sys.platform == "darwin":
            cmd = ["say", "-r", str(self._rate)]
            if self._voice:
                cmd += ["-v", self._voice]
            cmd.append(text)
            subprocess.run(cmd, check=False)
        elif sys.platform.startswith("linux"):
            cmd = ["espeak", "-s", str(self._rate)]
            if self._voice:
                cmd += ["-v", self._voice]
            cmd.append(text)
            try:
                subprocess.run(cmd, check=False)
            except FileNotFoundError:
                pass
        elif sys.platform.startswith("win"):
            script = (
                f"Add-Type -AssemblyName System.Speech;"
                f"$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
                f"$s.Rate={max(-10, min(10, (self._rate - 180) // 20))};"
                f"$s.Speak('{text.replace(chr(39), '')}')"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", script], check=False)


class VoiceInput:
    def __init__(self, config: VoiceConfig) -> None:
        self._config = config
        self._transcriber: Optional[FasterWhisperTranscriber] = None

    def _get_transcriber(self) -> FasterWhisperTranscriber:
        if self._transcriber is None:
            self._transcriber = FasterWhisperTranscriber(
                model=self._config.model,
                device=self._config.device,
                compute_type=self._config.compute_type,
                language=self._config.language,
            )
        return self._transcriber

    def capture_and_transcribe(
        self, announce: bool = True, skip_silence: bool = False
    ) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)

        try:
            audio = record_wav(
                path=wav_path,
                seconds=self._config.record_seconds,
                sample_rate=self._config.sample_rate,
                announce=announce,
            )
            if skip_silence and _is_probably_silent(audio, self._config.silence_threshold):
                raise NoSpeechDetected("Silence detected.")
            return self._get_transcriber().transcribe_file(str(wav_path))
        finally:
            wav_path.unlink(missing_ok=True)
