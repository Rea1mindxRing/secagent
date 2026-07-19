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


if __name__ == "__main__":
    test_config()
    test_thinking()
    test_cache()
    print("\n所有测试通过！")
