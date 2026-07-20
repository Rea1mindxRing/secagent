import json
from dataclasses import dataclass
from typing import Any, Callable, Dict, List


@dataclass
class RegisteredTool:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        def decorator(handler: Callable[..., Any]):
            self._tools[name] = RegisteredTool(name, description, parameters, handler)
            return handler
        return decorator

    def schemas(self, provider: str = "openai") -> List[Dict[str, Any]]:
        if provider == "anthropic":
            return [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in self._tools.values()
            ]
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            return {"success": False, "error": f"未知工具: {name}"}
        try:
            result = tool.handler(**arguments)
            if isinstance(result, dict):
                return result
            return {"success": True, "result": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def __contains__(self, name: str) -> bool:
        return name in self._tools


def json_tool_result(result: Dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, default=str)
