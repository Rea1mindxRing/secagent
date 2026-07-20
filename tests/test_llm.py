import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unittest.mock import patch

from secagent.llm.config import LLMConfig
from secagent.llm.thinking import get_thinking_params, list_thinking_levels
from secagent.llm.cache import ModelCache
from secagent.llm.client import LLMClient, LLMRequestError
from secagent.llm.model_fetcher import ModelFetcher, ModelFetchError
from secagent.cli.main import main
from secagent.skills.registry import build_runtime_system_prompt, select_skills
from secagent.skills.task_parser import parse_security_task
from secagent.tools.loop import run_tool_loop
from secagent.tools.registry import ToolRegistry
import requests


def test_config():
    config = LLMConfig(provider="openai", model="gpt-4o", thinking="high")
    assert config.provider == "openai"
    assert config.model == "gpt-4o"
    assert config.thinking == "high"
    print("✓ LLMConfig 测试通过")


def test_thinking():
    params = get_thinking_params("high")
    assert params["temperature"] == 0.2
    assert params["max_tokens"] == 4096
    levels = list_thinking_levels()
    assert "high" in levels
    assert "medium" in levels
    print("✓ Thinking 测试通过")


def test_cache():
    cache = ModelCache("~/.secagent/test_cache")
    cache.set("test_provider", "http://localhost", "test_key", {"models": ["test"]})
    result = cache.get("test_provider", "http://localhost", "test_key")
    assert result == {"models": ["test"]}
    cache.cleanup()
    print("✓ Cache 测试通过")


def test_cli_args_passed_to_main_interactive():
    with patch("secagent.cli.main.main_interactive") as mock_main:
        with patch.object(sys, "argv", ["secagent", "--config", "/tmp/a.yaml", "--thinking", "high", "--safety", "strict"]):
            main()
    mock_main.assert_called_once_with(
        config_path="/tmp/a.yaml",
        thinking="high",
        safety="strict",
    )


def test_llm_client_requires_api_key():
    client = LLMClient(LLMConfig(api_key=""))
    try:
        list(client.stream("hello"))
        assert False
    except LLMRequestError as exc:
        assert "API Key 未配置" in str(exc)


def test_llm_client_wraps_connection_error():
    client = LLMClient(LLMConfig(api_key="test-key"))
    with patch.object(client.session, "post", side_effect=requests.ConnectionError("boom")):
        try:
            list(client.stream("hello"))
            assert False
        except LLMRequestError as exc:
            assert "无法连接模型接口" in str(exc)


def test_model_fetcher_requires_valid_key():
    fetcher = ModelFetcher("openai", "", "https://api.openai.com")
    try:
        fetcher.fetch_verified()
        assert False
    except ModelFetchError as exc:
        assert "API Key 未配置" in str(exc)


def test_model_fetcher_does_not_fallback_on_auth_error():
    fetcher = ModelFetcher("openai", "bad-key", "https://api.openai.com")
    response = requests.Response()
    response.status_code = 401
    response._content = b'{"error":{"message":"invalid key"}}'
    http_error = requests.HTTPError(response=response)
    with patch.object(fetcher, "_fetch_from_api", side_effect=http_error):
        try:
            fetcher.fetch_verified()
            assert False
        except ModelFetchError as exc:
            assert "invalid key" in str(exc)


def test_security_task_parser_extracts_target_and_intent():
    task = parse_security_task("我有一个目标 https://demo.example.com:8443，帮我探测端口并找 API 漏洞")
    assert task.targets == ["https://demo.example.com:8443"]
    assert task.intent == "外网侦察与攻击面枚举"
    assert "api" in task.vulnerability_hints


def test_skill_router_injects_relevant_skill_context():
    selected = select_skills("探测目标 192.0.2.10 的端口和 Web API")
    assert "scanning-network-with-nmap-advanced" in selected
    assert "conducting-api-security-testing" in selected
    selected, prompt = build_runtime_system_prompt("探测目标 192.0.2.10 的端口")
    assert selected
    assert "ACTIVE SKILL" in prompt


def test_greeting_does_not_route_to_security_skill():
    assert select_skills("hi") == []
    assert select_skills("你好，你是什么模型") == []


def test_openai_tool_call_response_is_normalized():
    client = LLMClient(LLMConfig(api_key="test-key"))
    response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "shell_command", "arguments": '{"command":"nmap -sV 192.0.2.10"}'},
                }],
            },
        }],
        "usage": {},
    }
    parsed = client._parse_response(response)
    assert parsed["tool_calls"][0]["name"] == "shell_command"
    assert parsed["tool_calls"][0]["arguments"]["command"].startswith("nmap")


def test_tool_loop_executes_and_returns_tool_result():
    class FakeClient:
        config = LLMConfig(provider="openai")

        def __init__(self):
            self.calls = 0

        def chat_messages(self, messages, system="", tools=None):
            self.calls += 1
            if self.calls == 1:
                return {
                    "content": "",
                    "tool_calls": [{"id": "call-1", "name": "echo", "arguments": {"value": "ok"}}],
                    "assistant_message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [{"id": "call-1", "type": "function", "function": {"name": "echo", "arguments": '{"value":"ok"}'}}],
                    },
                }
            assert messages[-1]["role"] == "tool"
            return {"content": "完成", "tool_calls": [], "assistant_message": {"role": "assistant", "content": "完成"}}

    registry = ToolRegistry()
    registry.register("echo", "echo", {"type": "object", "properties": {"value": {"type": "string"}}})(lambda value: {"value": value})
    content, trace = run_tool_loop(FakeClient(), "执行", "system", registry)
    assert content == "完成"
    assert trace[0]["result"] == {"value": "ok"}


if __name__ == "__main__":
    test_config()
    test_thinking()
    test_cache()
    print("\n所有测试通过！")
