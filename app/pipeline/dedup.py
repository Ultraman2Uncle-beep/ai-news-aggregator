from __future__ import annotations

import difflib

from app.collectors.base import RawItem


def dedup_by_url(items: list[RawItem]) -> list[RawItem]:
    """按 URL 去重（保留首个）。"""
    seen: set[str] = set()
    result: list[RawItem] = []
    for item in items:
        key = item.url.strip()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def dedup_by_title_similarity(
    items: list[RawItem], threshold: float = 0.85
) -> list[RawItem]:
    """基于标题相似度去重，避免同一新闻被多源重复收录。"""
    result: list[RawItem] = []
    for item in items:
        dup = False
        norm = item.title.lower().strip()
        for existing in result:
            existing_norm = existing.title.lower().strip()
            if not norm or not existing_norm:
                continue
            ratio = difflib.SequenceMatcher(None, norm, existing_norm).ratio()
            if ratio >= threshold:
                dup = True
                break
        if not dup:
            result.append(item)
    return result


def dedup(items: list[RawItem]) -> list[RawItem]:
    """URL 去重 + 标题相似度去重。"""
    return dedup_by_title_similarity(dedup_by_url(items))
