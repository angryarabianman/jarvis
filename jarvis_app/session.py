import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


SYSTEM_PROMPT = (
    "You are Jarvis, a concise and helpful AI assistant. "
    "Answer clearly and keep replies practical.\n\n"
    "TOOL USE RULES — follow strictly:\n"
    "- Use tools for any system-related request: opening/closing apps, system actions "
    "(shutdown, volume, brightness), checking system state (current volume, battery, running processes).\n"
    "- For system state queries (e.g. 'what is the current volume?'), run the appropriate shell command "
    "and report the result — do NOT tell the user to run it themselves.\n"
    "- NEVER use run_shell_command to search the internet or look up general knowledge — "
    "answer those from your training data.\n"
    "- For greetings and general conversation, respond with text only."
)


@dataclass
class ChatSession:
    system_prompt: str = SYSTEM_PROMPT
    messages: List[Dict[str, str]] = field(default_factory=list)

    def build_messages(self, user_text: str) -> List[Dict[str, str]]:
        base = [{"role": "system", "content": self.system_prompt}]
        return base + self.messages + [{"role": "user", "content": user_text}]

    def add_turn(self, user_text: str, assistant_text: str) -> None:
        self.messages.append({"role": "user", "content": user_text})
        self.messages.append({"role": "assistant", "content": assistant_text})

    def reset(self) -> None:
        self.messages.clear()

    def save(self) -> str:
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"chat_log_{now}.json"
        payload = {"system_prompt": self.system_prompt, "messages": self.messages}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return path

