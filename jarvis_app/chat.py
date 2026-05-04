import uuid
from dataclasses import dataclass
from typing import List, Optional, Tuple

from jarvis_app.agent import AgentError, run_agent_turn
from jarvis_app.memory import MemoryDB, format_memory_context, init_memory
from jarvis_app.providers import ProviderError
from jarvis_app.session import SYSTEM_PROMPT, ChatSession
from jarvis_app.voice import NoSpeechDetected, VoiceConfig, VoiceInput, VoiceInputError, VoiceSpeaker


def _pick_session(memory_db: MemoryDB) -> List[Tuple[str, str, str]]:
    sessions = memory_db.list_sessions()
    if not sessions:
        print("No previous sessions found.")
        return []

    print("\nPrevious sessions:")
    for i, s in enumerate(sessions, 1):
        preview = s["first_message"][:60].replace("\n", " ")
        print(f"  {i}. [{s['started']}]  {s['turns']} turns  —  \"{preview}\"")

    print()
    while True:
        try:
            raw = input(f"Select session (1-{len(sessions)}) or Enter to skip: ").strip()
        except (KeyboardInterrupt, EOFError):
            return []
        if not raw:
            return []
        if raw.isdigit() and 1 <= int(raw) <= len(sessions):
            chosen = sessions[int(raw) - 1]
            turns = memory_db.get_session_turns(chosen["session_id"])
            print(f"Loaded session from {chosen['started']} ({len(turns)} turns).\n")
            return turns
        print(f"Enter a number between 1 and {len(sessions)}.")


@dataclass
class AppConfig:
    model: str
    voice_input: bool = False
    voice_output: bool = False
    hands_free: bool = False
    allow_actions: bool = False
    continue_session: bool = False
    voice_config: Optional[VoiceConfig] = None
    tts_voice: Optional[str] = None
    tts_rate: int = 180


def _handle_command(raw: str, session: ChatSession) -> str:
    if raw == "/exit":
        print("Goodbye.")
        return "exit"
    if raw == "/reset":
        session.reset()
        print("Conversation history reset.")
        return "handled"
    if raw == "/save":
        file_path = session.save()
        print(f"Saved: {file_path}")
        return "handled"
    return "continue"


def _read_user_text(voice_input: Optional[VoiceInput]) -> Optional[str]:
    if voice_input is None:
        try:
            return input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            return None

    try:
        raw = input("\nYou [Enter=record | /text <msg> | /exit]: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting.")
        return None

    if raw.startswith("/text "):
        return raw[len("/text "):].strip()
    if raw and raw != "/voice" and not raw.startswith("/"):
        return raw
    if raw in {"/exit", "/reset", "/save"}:
        return raw
    if raw in {"", "/voice"}:
        try:
            text = voice_input.capture_and_transcribe()
        except VoiceInputError as e:
            print(f"Voice input error: {e}")
            return ""
        print(f"You (voice): {text}")
        return text
    print("Unknown command.")
    return ""


def _handle_spoken_command(raw: str, session: ChatSession) -> str:
    normalized = " ".join(raw.lower().strip().split())
    if normalized in {"jarvis exit", "jarvis stop"}:
        print("Goodbye.")
        return "exit"
    if normalized == "jarvis reset":
        session.reset()
        print("Conversation history reset.")
        return "handled"
    if normalized == "jarvis save":
        file_path = session.save()
        print(f"Saved: {file_path}")
        return "handled"
    return "continue"


def run_chat(config: AppConfig) -> None:
    memory_db = init_memory()
    session_id = str(uuid.uuid4())

    if config.continue_session:
        recent = _pick_session(memory_db)
        system_prompt = SYSTEM_PROMPT + format_memory_context(recent)
    else:
        recent = []
        system_prompt = SYSTEM_PROMPT
    session = ChatSession(system_prompt=system_prompt)

    voice_input = VoiceInput(config.voice_config) if config.voice_input and config.voice_config else None
    speaker = VoiceSpeaker(voice=config.tts_voice, rate=config.tts_rate) if config.voice_output else None

    print(f"Jarvis started (model={config.model}). Type /exit to quit.")
    if recent:
        print(f"Continuing previous session ({len(recent)} turns loaded from memory).")
    if voice_input:
        print("Voice input is enabled.")
    if speaker:
        print(f"Voice output is enabled (voice={config.tts_voice or 'default'}).")
    if config.hands_free:
        print("Hands-free dialogue is enabled. Speak naturally; no key press needed.")
        print("Say 'jarvis exit' to stop, 'jarvis reset' to clear memory, 'jarvis save' to save chat.")
    if config.allow_actions:
        print("Actions enabled — ask naturally (e.g. 'open Chrome', 'close Safari').")

    while True:
        if config.hands_free and voice_input is not None:
            try:
                user_text = voice_input.capture_and_transcribe(announce=False, skip_silence=True)
            except NoSpeechDetected:
                continue
            except VoiceInputError as e:
                print(f"Voice input error: {e}")
                continue
            print(f"\nYou (voice): {user_text}")
        else:
            user_text = _read_user_text(voice_input=voice_input)

        if user_text is None:
            return
        if not user_text:
            continue

        if config.hands_free:
            command_result = _handle_spoken_command(user_text, session)
        else:
            command_result = _handle_command(user_text, session)
        if command_result == "exit":
            return
        if command_result == "handled":
            continue

        messages = session.build_messages(user_text)
        try:
            assistant_text = run_agent_turn(
                model=config.model,
                messages=messages,
                allow_tools=config.allow_actions,
            )
        except (ProviderError, AgentError) as e:
            print(f"Error: {e}")
            continue

        if assistant_text:
            print(f"Jarvis: {assistant_text}")
            if speaker:
                speaker.speak(assistant_text)
        memory_db.save_turn(session_id, user_text, assistant_text)
        session.add_turn(user_text, assistant_text)
