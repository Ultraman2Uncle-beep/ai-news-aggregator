from __future__ import annotations

import math
from collections import defaultdict

from app.collectors.base import RawItem

_SOURCE_WEIGHT = {
    "hackernews": 1.0,
    "reddit": 1.0,
    "github": 0.9,
    "rss": 0.3,
}


def normalize_scores(items: list[RawItem]) -> list[RawItem]:
    """log 压缩量级 + 源内 min-max 归一化 + 源权重，使各源热度可比。"""
    for item in items:
        if item.hot_score > 0:
            item.hot_score = math.log1p(item.hot_score)

    groups: dict[str, list[RawItem]] = defaultdict(list)
    for item in items:
        groups[item.source_type].append(item)

    for source_type, group in groups.items():
        scores = [i.hot_score for i in group]
        lo, hi = min(scores), max(scores)
        weight = _SOURCE_WEIGHT.get(source_type, 1.0)
        for item in group:
            if hi > lo:
                item.hot_score = (item.hot_score - lo) / (hi - lo)
            else:
                item.hot_score = 1.0 if item.hot_score > 0 else 0.0
            item.hot_score = round(item.hot_score * weight, 4)
    return items


def sort_by_hotness(items: list[RawItem]) -> list[RawItem]:
    return sorted(items, key=lambda x: x.hot_score, reverse=True)
