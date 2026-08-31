from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawItem:
    """采集层返回的原始条目（尚未提炼/翻译）。"""

    url: str
    title: str
    source: str
    source_type: str
    published_at: str | None = None
    hot_score: float = 0.0
    content: str = ""  # 正文/简介，供 LLM 提炼
    raw: dict[str, Any] = field(default_factory=dict)

    def key(self) -> str:
        """基于 URL 的稳定去重键。"""
        return hashlib.sha1(self.url.encode("utf-8")).hexdigest()


class BaseCollector:
    """采集器抽象基类。所有采集器必须实现 collect() 并返回 RawItem 列表。"""

    source: str = "base"
    source_type: str = "base"

    def collect(self) -> list[RawItem]:
        raise NotImplementedError
