from __future__ import annotations

import calendar
import html
import re
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from app.collectors.base import BaseCollector, RawItem

_TAG_RE = re.compile(r"<[^>]+>")
_USER_AGENT = "ai-news-aggregator/1.0 (personal local use)"


def strip_html(text: str) -> str:
    """去掉 HTML 标签并反转义。"""
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    return html.unescape(text).strip()


def _entry_content(entry) -> str:
    """提取 RSS/Atom 条目的正文或摘要文本。"""
    content = entry.get("content")
    if content and isinstance(content, list) and content:
        value = content[0].get("value", "")
        if value:
            return strip_html(value)
    for key in ("summary", "description"):
        value = entry.get(key)
        if value:
            return strip_html(value)
    return ""


def _struct_to_dt(ts) -> datetime | None:
    try:
        return datetime.fromtimestamp(calendar.timegm(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


class RSSCollector(BaseCollector):
    """通用 RSS/Atom 采集器。

    可用于：官网/博客 RSS、GitHub releases.atom、国内媒体 RSS。
    完全公开，无需登录。
    """

    source_type = "rss"

    def __init__(
        self,
        name: str,
        feed_url: str,
        max_items: int = 20,
        max_age_hours: int = 72,
    ) -> None:
        self.source = name
        self.feed_url = feed_url
        self.max_items = max_items
        self.max_age_hours = max_age_hours

    def collect(self) -> list[RawItem]:
        with httpx.Client(
            headers={"User-Agent": _USER_AGENT},
            follow_redirects=True,
            timeout=15,
        ) as client:
            resp = client.get(self.feed_url)
            resp.raise_for_status()
            parsed = feedparser.parse(resp.content)

        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.max_age_hours)
        items: list[RawItem] = []
        for entry in parsed.entries:
            ts = entry.get("published_parsed") or entry.get("updated_parsed")
            if ts:
                dt = _struct_to_dt(ts)
                if dt and dt < cutoff:
                    continue
            url = entry.get("link", "")
            if not url:
                continue
            title = strip_html(entry.get("title", ""))
            content = _entry_content(entry)
            published = entry.get("published") or entry.get("updated")
            items.append(
                RawItem(
                    url=url,
                    title=title,
                    source=self.source,
                    source_type=self.source_type,
                    published_at=published,
                    content=content,
                    raw={"entry": dict(entry)},
                )
            )
            if len(items) >= self.max_items:
                break
        return items
