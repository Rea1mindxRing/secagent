import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from secagent.llm.config import LLMConfig
from secagent.llm.thinking import get_thinking_params, list_thinking_levels
from secagent.llm.cache import ModelCache


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


if __name__ == "__main__":
    test_config()
    test_thinking()
    test_cache()
    print("\n所有测试通过！")