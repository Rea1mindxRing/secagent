import json
from typing import Any, Dict, List, Tuple

from ..llm.client import LLMClient, LLMRequestError
from .registry import ToolRegistry


class ToolLoopError(Exception):
    pass


def run_tool_loop(
    client: LLMClient,
    prompt: str,
    system: str,
    registry: ToolRegistry,
    max_rounds: int = 5,
) -> Tuple[str, List[Dict[str, Any]]]:
    messages: List[Dict[str, Any]] = [{"role": "user", "content": prompt}]
    trace: List[Dict[str, Any]] = []

    for round_number in range(1, max_rounds + 1):
        response = client.chat_messages(
            messages,
            system=system,
            tools=registry.schemas(client.config.provider),
        )
        tool_calls = response.get("tool_calls", [])
        assistant_message = response.get("assistant_message")
        if assistant_message:
            messages.append(assistant_message)

        if not tool_calls:
            return response.get("content", ""), trace

        for call in tool_calls:
            result = registry.execute(call["name"], call["arguments"])
            trace.append({
                "round": round_number,
                "tool": call["name"],
                "arguments": call["arguments"],
                "result": result,
            })
            if client.config.provider == "anthropic":
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": call["id"],
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }],
                })
            else:
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                })

    raise ToolLoopError(f"工具调用超过最大轮数: {max_rounds}")
