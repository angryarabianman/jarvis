import json
import os
from typing import Dict, List, Optional, Tuple
from urllib import error, request


Message = Dict[str, str]
ToolCallList = List[Dict]

NEBIUS_API_BASE = "https://api.studio.nebius.com/v1"
DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct"


class ProviderError(RuntimeError):
    pass


def _post_json(url: str, payload: Dict, headers: Dict[str, str]) -> Dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise ProviderError(f"HTTP {e.code}: {detail}") from e
    except error.URLError as e:
        raise ProviderError(f"Connection error: {e}") from e


def _normalize_tool_calls(raw_calls: List[Dict]) -> ToolCallList:
    result = []
    for i, call in enumerate(raw_calls):
        func = call.get("function", {})
        args = func.get("arguments", {})
        result.append({
            "id": call.get("id", f"call_{i}"),
            "type": "function",
            "function": {
                "name": func.get("name", ""),
                "arguments": json.dumps(args) if isinstance(args, dict) else args,
            },
        })
    return result


def chat_completion_with_tools(
    model: str,
    messages: List[Message],
    tools: Optional[List] = None,
) -> Tuple[Optional[str], Optional[ToolCallList]]:
    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        raise ProviderError("NEBIUS_API_KEY is not set.")

    payload: Dict = {"model": model, "messages": messages}
    if tools:
        payload["tools"] = tools

    response = _post_json(
        url=f"{NEBIUS_API_BASE}/chat/completions",
        payload=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        msg = response["choices"][0]["message"]
    except (KeyError, IndexError) as e:
        raise ProviderError(f"Unexpected response: {response}") from e

    raw_calls = msg.get("tool_calls")
    if raw_calls:
        return None, _normalize_tool_calls(raw_calls)
    content = (msg.get("content") or "").strip()
    return content, None
