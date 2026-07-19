from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMConfig:
    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com"
    api_key: str = ""
    thinking: str = "medium"

    @classmethod
    def from_yaml(cls, path: str) -> "LLMConfig":
        import yaml
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        llm_data = data.get("llm", {})
        return cls(**llm_data)

    def to_yaml(self, path: str):
        import yaml
        data = {"llm": {
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "thinking": self.thinking,
        }}
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)