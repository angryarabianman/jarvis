import json
from typing import Dict, List

from jarvis_app.providers import chat_completion_with_tools
from jarvis_app.tools import MEMORY_SEARCH_SCHEMA, TOOL_SCHEMAS, execute_tool


_MAX_TOOL_ITERATIONS = 10


class AgentError(RuntimeError):
    pass


def run_agent_turn(
    model: str,
    messages: List[Dict],
    allow_tools: bool = False,
    allow_memory: bool = False,
) -> str:
    tools: List[Dict] = []
    if allow_tools:
        tools.extend(TOOL_SCHEMAS)
    if allow_memory:
        tools.append(MEMORY_SEARCH_SCHEMA)

    working = list(messages)

    for _ in range(_MAX_TOOL_ITERATIONS):
        text, tool_calls = chat_completion_with_tools(
            model=model,
            messages=working,
            tools=tools or None,
        )

        if text:
            return text

        if not tool_calls:
            raise AgentError("LLM returned neither text nor tool calls.")

        for call in tool_calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"])
            except (json.JSONDecodeError, TypeError):
                args = {}
            result = execute_tool(name, args)
            print(f"[Tool] {name}({args}) → {result}")
        return ""

    raise AgentError(f"Exceeded {_MAX_TOOL_ITERATIONS} tool call iterations.")
