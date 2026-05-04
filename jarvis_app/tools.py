import subprocess
import sys
from typing import Any, Dict, List

from jarvis_app.actions import (
    ActionError,
    _close_application_linux,
    _close_application_macos,
    _close_application_windows,
    _open_application_linux,
    _open_application_macos,
    _open_application_windows,
)


TOOL_SCHEMAS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "open_application",
            "description": "Open a desktop application by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to open, e.g. 'Chrome', 'Terminal', 'Safari'.",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "close_application",
            "description": "Close a running desktop application by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to close, e.g. 'Chrome', 'Terminal', 'Safari'.",
                    }
                },
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell_command",
            "description": (
                "Run a shell command on the user's computer and return its output. "
                "Use for system actions like shutting down, adjusting volume, "
                "getting system info, managing files, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute, e.g. 'osascript -e \"set volume 5\"'.",
                    }
                },
                "required": ["command"],
            },
        },
    },
]

MEMORY_SEARCH_SCHEMA: Dict = {
    "type": "function",
    "function": {
        "name": "search_memory",
        "description": "Search past conversations for relevant information.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keywords to search for in past conversations.",
                }
            },
            "required": ["query"],
        },
    },
}


def execute_tool(name: str, args: Dict[str, Any]) -> str:
    if name == "search_memory":
        from jarvis_app.memory import get_memory
        db = get_memory()
        if not db:
            return "Memory not available."
        results = db.search(args.get("query", ""))
        if not results:
            return "No relevant memories found."
        return "\n".join(f"[{ts}] User: {u} | Jarvis: {a}" for ts, u, a in results)

    if name == "run_shell_command":
        command = args.get("command", "").strip()
        if not command:
            return "Error: missing command argument."
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            output = (result.stdout + result.stderr).strip()
            if not output:
                return "Done." if result.returncode == 0 else f"Exit code {result.returncode}."
            return output[:1000]
        except subprocess.TimeoutExpired:
            return "Error: command timed out."

    app_name = args.get("app_name", "").strip()
    if not app_name:
        return "Error: missing app_name argument."
    try:
        if name == "open_application":
            if sys.platform == "darwin":
                _open_application_macos(app_name)
            elif sys.platform.startswith("linux"):
                _open_application_linux(app_name)
            elif sys.platform.startswith("win"):
                _open_application_windows(app_name)
            else:
                return f"Error: unsupported platform {sys.platform}."
            return f"Opened {app_name}."

        if name == "close_application":
            if sys.platform == "darwin":
                _close_application_macos(app_name)
            elif sys.platform.startswith("linux"):
                _close_application_linux(app_name)
            elif sys.platform.startswith("win"):
                _close_application_windows(app_name)
            else:
                return f"Error: unsupported platform {sys.platform}."
            return f"Closed {app_name}."

        return f"Error: unknown tool '{name}'."
    except ActionError as e:
        return f"Error: {e}"
