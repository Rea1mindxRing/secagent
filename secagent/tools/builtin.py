import subprocess
from typing import Dict

from ..security.safety_manager import SafetyManager
from ..mcp.manager import MCPManager
from .registry import ToolRegistry


def execute_command(command: str) -> Dict[str, object]:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "命令执行超时", "stdout": "", "stderr": ""}


def build_default_registry(safety_manager: SafetyManager, mcp_manager: MCPManager = None) -> ToolRegistry:
    registry = ToolRegistry()

    @registry.register(
        "shell_command",
        "在当前安全测试环境执行命令。仅用于用户请求范围内的侦察、验证和分析。",
        {
            "type": "object",
            "properties": {"command": {"type": "string", "description": "要执行的 shell 命令"}},
            "required": ["command"],
            "additionalProperties": False,
        },
    )
    def shell_command(command: str):
        return safety_manager.execute_with_safety(command, execute_command)

    if mcp_manager is not None:
        @registry.register(
            "mcp_call",
            "调用已配置的 MCP 服务方法，并返回结构化结果。",
            {
                "type": "object",
                "properties": {
                    "server": {"type": "string"},
                    "method": {"type": "string"},
                    "params": {"type": "object"},
                },
                "required": ["server", "method"],
                "additionalProperties": False,
            },
        )
        def mcp_call(server: str, method: str, params: dict = None):
            return mcp_manager.call(server, method, **(params or {}))

    return registry
