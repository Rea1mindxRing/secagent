import os
import json
import requests
from typing import Dict, Iterator, Optional, Any
from .config import LLMConfig
from .thinking import get_thinking_params


# 模型上下文窗口限制（token）
MODEL_CONTEXT_LIMITS = {
    "deepseek-v4-flash": 128000,
    "deepseek-v4-pro": 128000,
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    "gpt-5.6-sol": 128000,
    "gpt-5.6-terra": 128000,
    "gpt-5.6-luna": 128000,
    "claude-fable-5": 200000,
    "claude-sonnet-5": 200000,
    "claude-opus-4.8": 200000,
    "claude-3-5-sonnet-20241022": 200000,
    "claude-3-haiku-20240307": 200000,
    "deepseek-chat": 65536,
}

# 模型价格估算（每百万 token，单位：元）
MODEL_PRICING = {
    "deepseek-v4-flash": {"input": 0.5, "output": 2.0},
    "deepseek-v4-pro": {"input": 2.0, "output": 8.0},
    "gpt-4o": {"input": 15.0, "output": 60.0},
    "gpt-4o-mini": {"input": 1.5, "output": 6.0},
    "claude-fable-5": {"input": 20.0, "output": 80.0},
    "claude-sonnet-5": {"input": 8.0, "output": 24.0},
    "deepseek-chat": {"input": 0.5, "output": 2.0},
}
DEFAULT_PRICING = {"input": 5.0, "output": 15.0}


class LLMRequestError(Exception):
    pass


def get_model_context_limit(model: str) -> int:
    for key, limit in MODEL_CONTEXT_LIMITS.items():
        if key in model:
            return limit
    return 128000


class LLMClient:
    def __init__(self, config: LLMConfig):
        self.config = config
        self.session = requests.Session()
        self._last_usage: Optional[Dict[str, int]] = None
        self._session_input_tokens = 0
        self._session_output_tokens = 0
        self._session_cost = 0.0

    def _render_key(self) -> str:
        key = self.config.api_key
        if key.startswith("${ENV:") and key.endswith("}"):
            env_var = key[6:-1]
            return os.environ.get(env_var, "")
        return key

    def _build_headers(self) -> Dict[str, str]:
        key = self._render_key()
        headers = {"Content-Type": "application/json"}

        if self.config.provider == "anthropic":
            headers["x-api-key"] = key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {key}"

        return headers

    def _validate_config(self):
        key = self._render_key().strip()
        if not key:
            raise LLMRequestError("API Key 未配置，请先设置 `OPENAI_API_KEY` 或重新执行 `config`。")

    def _build_body(
        self,
        prompt: str,
        system: str = "",
        tools: Optional[list] = None,
        stream: bool = False,
        messages: Optional[list] = None,
    ) -> Dict[str, Any]:
        thinking = get_thinking_params(self.config.thinking)

        if self.config.provider == "anthropic":
            body = {
                "model": self.config.model,
                "max_tokens": thinking["max_tokens"],
                "temperature": thinking["temperature"],
                "stream": stream,
                "messages": messages or [{"role": "user", "content": prompt}],
            }
            if system:
                body["system"] = system
            if tools:
                body["tools"] = tools
        else:
            request_messages = list(messages or [])
            if system and not any(message.get("role") == "system" for message in request_messages):
                request_messages.insert(0, {"role": "system", "content": system})
            if not request_messages:
                request_messages.append({"role": "user", "content": prompt})

            body = {
                "model": self.config.model,
                "max_tokens": thinking["max_tokens"],
                "temperature": thinking["temperature"],
                "top_p": thinking["top_p"],
                "stream": stream,
                "messages": request_messages,
            }
            if tools:
                body["tools"] = tools

        return body

    def _get_endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        if self.config.provider == "anthropic":
            return f"{base}/v1/messages"
        return f"{base}/v1/chat/completions"

    def set_thinking(self, level: str):
        """设置思考强度（low/medium/high/max/ultra）"""
        self.config.thinking = level

    def stream(self, prompt: str, system: str = "", tools: Optional[list] = None) -> Iterator[str]:
        """流式请求 LLM，逐 chunk 返回文本"""
        self._validate_config()
        headers = self._build_headers()
        body = self._build_body(prompt, system=system, tools=tools, stream=True)
        endpoint = self._get_endpoint()
        try:
            resp = self.session.post(endpoint, headers=headers, json=body, stream=True, timeout=120)
            resp.raise_for_status()

            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line[5:].strip()
                if line == "[DONE]":
                    break
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for chunk in self._parse_stream_chunk(data):
                    yield chunk
        except requests.Timeout as exc:
            raise LLMRequestError(f"连接模型超时：`{endpoint}`") from exc
        except requests.ConnectionError as exc:
            raise LLMRequestError(f"无法连接模型接口：`{endpoint}`") from exc
        except requests.HTTPError as exc:
            detail = exc.response.text[:300] if exc.response is not None else str(exc)
            raise LLMRequestError(f"模型接口返回错误：{detail}") from exc
        except requests.RequestException as exc:
            raise LLMRequestError(f"模型请求失败：{exc}") from exc

    def chat(self, prompt: str, system: str = "", tools: Optional[list] = None) -> Dict[str, Any]:
        """非流式请求 LLM"""
        return self.chat_messages(
            [{"role": "user", "content": prompt}],
            system=system,
            tools=tools,
        )

    def chat_messages(
        self,
        messages: list,
        system: str = "",
        tools: Optional[list] = None,
    ) -> Dict[str, Any]:
        """Send a non-streaming request with conversation and tool-call support."""
        self._validate_config()
        headers = self._build_headers()
        body = self._build_body(
            messages[-1].get("content", "") if messages else "",
            system=system,
            tools=tools,
            stream=False,
            messages=messages,
        )
        endpoint = self._get_endpoint()
        try:
            resp = self.session.post(endpoint, headers=headers, json=body, timeout=120)
            resp.raise_for_status()
            return self._parse_response(resp.json())
        except requests.Timeout as exc:
            raise LLMRequestError(f"连接模型超时：`{endpoint}`") from exc
        except requests.ConnectionError as exc:
            raise LLMRequestError(f"无法连接模型接口：`{endpoint}`") from exc
        except requests.HTTPError as exc:
            detail = exc.response.text[:300] if exc.response is not None else str(exc)
            raise LLMRequestError(f"模型接口返回错误：{detail}") from exc
        except requests.RequestException as exc:
            raise LLMRequestError(f"模型请求失败：{exc}") from exc

    def _parse_response(self, data: Dict) -> Dict[str, Any]:
        usage = data.get("usage", {})
        self._last_usage = {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
        self._accumulate_usage(self._last_usage)

        if self.config.provider == "anthropic":
            content = "".join(
                item.get("text", "") for item in data.get("content", []) if item.get("type") == "text"
            )
            tool_calls = [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "arguments": item.get("input", {}),
                }
                for item in data.get("content", [])
                if item.get("type") == "tool_use"
            ]
            return {
                "content": content,
                "model": self.config.model,
                "tool_calls": tool_calls,
                "assistant_message": {"role": "assistant", "content": data.get("content", [])},
            }
        message = data.get("choices", [{}])[0].get("message", {})
        tool_calls = []
        for call in message.get("tool_calls", []) or []:
            function = call.get("function", {})
            try:
                arguments = json.loads(function.get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}
            tool_calls.append({
                "id": call.get("id", ""),
                "name": function.get("name", ""),
                "arguments": arguments,
            })
        return {
            "content": message.get("content") or "",
            "model": self.config.model,
            "tool_calls": tool_calls,
            "assistant_message": message,
        }

    def _parse_stream_chunk(self, data: Dict) -> Iterator[str]:
        # 捕获 usage 信息（OpenAI 兼容格式：最后一条 chunk 含 usage 字段）
        if "usage" in data and data.get("usage"):
            self._last_usage = {
                "prompt_tokens": data["usage"].get("prompt_tokens", 0),
                "completion_tokens": data["usage"].get("completion_tokens", 0),
                "total_tokens": data["usage"].get("total_tokens", 0),
            }
            self._accumulate_usage(self._last_usage)

        if self.config.provider == "anthropic":
            if "content" in data:
                for item in data["content"]:
                    if item["type"] == "text":
                        yield item["text"]
        else:
            if data.get("choices"):
                content = data["choices"][0]["delta"].get("content", "")
                if content:
                    yield content

    def _accumulate_usage(self, usage: Dict[str, int]):
        self._session_input_tokens += usage.get("prompt_tokens", 0)
        self._session_output_tokens += usage.get("completion_tokens", 0)
        self._session_cost += self._estimate_cost(usage)

    def _estimate_cost(self, usage: Dict[str, int]) -> float:
        model_key = self.config.model
        pricing = MODEL_PRICING.get(model_key, DEFAULT_PRICING)
        input_cost = usage.get("prompt_tokens", 0) / 1_000_000 * pricing["input"]
        output_cost = usage.get("completion_tokens", 0) / 1_000_000 * pricing["output"]
        return round(input_cost + output_cost, 6)

    @property
    def last_usage(self) -> Dict[str, Any]:
        return self._last_usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    @property
    def session_stats(self) -> Dict[str, Any]:
        return {
            "input_tokens": self._session_input_tokens,
            "output_tokens": self._session_output_tokens,
            "total_tokens": self._session_input_tokens + self._session_output_tokens,
            "cost": round(self._session_cost, 6),
        }
