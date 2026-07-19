import os
import json
import time
import hashlib
from typing import Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    data: Any
    timestamp: float
    ttl: float


class ModelCache:
    def __init__(self, cache_dir: str = "~/.secagent/cache"):
        self.cache_dir = os.path.expanduser(cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._file_ttl = 86400
        self._hits = 0
        self._misses = 0
        self._warmup()

    def _warmup(self):
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.cache_dir, filename)
                try:
                    with open(filepath, encoding="utf-8") as f:
                        data = json.load(f)
                    key = filename[:-5]
                    self._memory_cache[key] = CacheEntry(
                        data=data,
                        timestamp=os.path.getmtime(filepath),
                        ttl=self._file_ttl
                    )
                except Exception:
                    pass

    def _generate_key(self, provider: str, base_url: str, api_key: str) -> str:
        key_hash = hashlib.md5(api_key.encode()).hexdigest()[:8]
        url_hash = hashlib.md5(base_url.encode()).hexdigest()[:8]
        return f"{provider}_{url_hash}_{key_hash}"

    def get(self, provider: str, base_url: str, api_key: str) -> Optional[Any]:
        key = self._generate_key(provider, base_url, api_key)

        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if time.time() - entry.timestamp < entry.ttl:
                self._hits += 1
                return entry.data

        filepath = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(filepath):
            mtime = os.path.getmtime(filepath)
            if time.time() - mtime < self._file_ttl:
                try:
                    with open(filepath, encoding="utf-8") as f:
                        data = json.load(f)
                    self._memory_cache[key] = CacheEntry(
                        data=data,
                        timestamp=mtime,
                        ttl=self._file_ttl
                    )
                    self._hits += 1
                    return data
                except Exception:
                    pass

        self._misses += 1
        return None

    def set(self, provider: str, base_url: str, api_key: str, data: Any, ttl: float = None):
        key = self._generate_key(provider, base_url, api_key)
        ttl = ttl or self._file_ttl
        timestamp = time.time()

        self._memory_cache[key] = CacheEntry(
            data=data,
            timestamp=timestamp,
            ttl=ttl
        )

        filepath = os.path.join(self.cache_dir, f"{key}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f)

        os.utime(filepath)

    def invalidate(self, provider: str, base_url: str, api_key: str):
        key = self._generate_key(provider, base_url, api_key)

        if key in self._memory_cache:
            del self._memory_cache[key]

        filepath = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

    def cleanup(self):
        now = time.time()

        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if now - entry.timestamp >= entry.ttl
        ]
        for key in expired_keys:
            del self._memory_cache[key]

        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.cache_dir, filename)
                if now - os.path.getmtime(filepath) >= self._file_ttl:
                    os.remove(filepath)

    def get_cache_hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total * 100

    def get_stats(self) -> Dict[str, Any]:
        return {
            "memory_entries": len(self._memory_cache),
            "file_entries": len([f for f in os.listdir(self.cache_dir) if f.endswith(".json")]),
            "cache_dir": self.cache_dir,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self.get_cache_hit_rate():.1f}%",
        }