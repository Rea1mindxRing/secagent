import requests
import json
from typing import List, Dict
from .cache import ModelCache


class ModelFetchError(Exception):
    pass

MODEL_KNOWLEDGE = {
    "claude-fable-5": {"pros": ["最强推理能力", "100万上下文", "视觉理解"], "cons": ["价格最高", "响应较慢"]},
    "claude-sonnet-5": {"pros": ["性价比高", "代码能力强", "适合日常安全任务"], "cons": ["推理能力略低于Fable"]},
    "claude-opus-4.8": {"pros": ["科学推理", "医疗分析", "长上下文"], "cons": ["订阅制", "价格高"]},
    "claude-3-5-sonnet-20241022": {"pros": ["成熟稳定", "代码能力强"], "cons": ["非最新版本"]},
    "claude-3-haiku-20240307": {"pros": ["快速响应", "低成本"], "cons": ["推理能力有限"]},
    "gpt-5.6-sol": {"pros": ["复杂编码", "网络安全优化", "科研级推理"], "cons": ["价格较高", "上下文有限"]},
    "gpt-5.6-terra": {"pros": ["平衡性能", "日常办公", "性价比"], "cons": ["推理能力略低于Sol"]},
    "gpt-5.6-luna": {"pros": ["快速响应", "低成本", "高吞吐量"], "cons": ["推理能力一般"]},
    "gpt-4o": {"pros": ["成熟稳定", "视觉理解"], "cons": ["非最新版本"]},
    "gpt-4o-mini": {"pros": ["快速响应", "低成本"], "cons": ["推理能力有限"]},
    "deepseek-chat": {"pros": ["开源友好", "中文支持", "低成本"], "cons": ["推理能力有限", "上下文较短"]},
}


class ModelFetcher:
    def __init__(self, provider: str, api_key: str, base_url: str):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.cache = ModelCache()

    def fetch(self, force_refresh: bool = False) -> List[Dict]:
        if not force_refresh:
            cached = self.cache.get(self.provider, self.base_url, self.api_key)
            if cached:
                return cached

        try:
            models = self._fetch_from_api()
            enriched = self._enrich_models(models)
            self.cache.set(self.provider, self.base_url, self.api_key, enriched)
            return enriched
        except Exception:
            return self._get_fallback_models()

    def fetch_verified(self, force_refresh: bool = True) -> List[Dict]:
        if not self.api_key.strip():
            raise ModelFetchError("API Key 未配置。")

        if not force_refresh:
            cached = self.cache.get(self.provider, self.base_url, self.api_key)
            if cached:
                return cached

        try:
            models = self._fetch_from_api()
            if not models:
                raise ModelFetchError("接口可访问，但没有返回可用模型。")
            enriched = self._enrich_models(models)
            self.cache.set(self.provider, self.base_url, self.api_key, enriched)
            return enriched
        except requests.Timeout as exc:
            raise ModelFetchError(f"连接模型接口超时：`{self.base_url}`") from exc
        except requests.ConnectionError as exc:
            raise ModelFetchError(f"无法连接模型接口：`{self.base_url}`") from exc
        except requests.HTTPError as exc:
            detail = exc.response.text[:300] if exc.response is not None else str(exc)
            raise ModelFetchError(f"模型接口认证或请求失败：{detail}") from exc
        except requests.RequestException as exc:
            raise ModelFetchError(f"模型接口请求失败：{exc}") from exc

    def _fetch_from_api(self) -> List[Dict]:
        headers = self._build_headers()
        endpoint = f"{self.base_url}/v1/models"

        resp = requests.get(endpoint, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        return self._parse_response(data)

    def _build_headers(self) -> Dict[str, str]:
        if self.provider == "anthropic":
            return {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            }
        return {"Authorization": f"Bearer {self.api_key}"}

    def _parse_response(self, data: Dict) -> List[Dict]:
        models = []
        for model in data.get("data", []):
            models.append({
                "id": model["id"],
                "name": model.get("name", model["id"]),
                "description": model.get("description", ""),
                "max_tokens": model.get("max_tokens", model.get("max_context_tokens", 0)),
            })
        return models

    def _enrich_models(self, models: List[Dict]) -> List[Dict]:
        enriched = []
        for model in models:
            knowledge = MODEL_KNOWLEDGE.get(model["id"], {})
            enriched.append({
                **model,
                "pros": knowledge.get("pros", []),
                "cons": knowledge.get("cons", []),
            })
        return enriched

    def _get_fallback_models(self) -> List[Dict]:
        return [
            {
                "id": model_id,
                "name": model_id,
                "description": "",
                "max_tokens": 0,
                **knowledge,
            }
            for model_id, knowledge in MODEL_KNOWLEDGE.items()
        ]
