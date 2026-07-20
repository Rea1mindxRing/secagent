import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secagent.mcp.server import MCPServer
from secagent.mcp.manager import MCPManager
from secagent.security.policy import SafetyMode
from secagent.security.safety_manager import SafetyManager
from secagent.tools.builtin import build_default_registry


def test_mcp_server():
    server = MCPServer(host="127.0.0.1", port=9999)

    @server.register("test_method", "测试方法", {"param1": "参数1", "param2": "参数2"})
    def test_method(param1: str, param2: str = "default") -> str:
        return f"Hello {param1} {param2}"

    methods = server.get_methods()
    assert "test_method" in methods
    assert methods["test_method"]["description"] == "测试方法"
    print("✓ MCPServer 测试通过")


if __name__ == "__main__":
    test_mcp_server()
    print("\n所有测试通过！")


def test_mcp_tool_is_registered_when_manager_is_available():
    registry = build_default_registry(SafetyManager(SafetyMode.SMART), MCPManager())
    names = [tool["function"]["name"] for tool in registry.schemas()]
    assert "shell_command" in names
    assert "mcp_call" in names
