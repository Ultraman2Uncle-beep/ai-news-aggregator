from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, RawItem

_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
_ITEM = "https://hacker-news.firebaseio.com/v0/item/{}.json"


class HackerNewsCollector(BaseCollector):
    """Hacker News 官方 API 采集（无需登录）。"""

    source = "hackernews"
    source_type = "hackernews"

    def __init__(self, top_n: int = 150, max_items: int = 100) -> None:
        self.top_n = top_n
        self.max_items = max_items

    def collect(self) -> list[RawItem]:
        with httpx.Client(timeout=20) as client:
            ids = client.get(_TOP_STORIES).json()[: self.top_n]
            items: list[RawItem] = []
            for story_id in ids:
                item = client.get(_ITEM.format(story_id)).json()
                if not item or item.get("type") != "story":
                    continue
                url = item.get("url")
                if not url:
                    url = f"https://news.ycombinator.com/item?id={story_id}"
                title = item.get("title", "")
                score = int(item.get("score", 0) or 0)
                comments = int(item.get("descendants", 0) or 0)
                hot = float(score) + float(comments) * 1.5
                created = item.get("time")
                published = None
                if created:
                    published = datetime.fromtimestamp(
                        float(created), tz=timezone.utc
                    ).isoformat()
                items.append(
                    RawItem(
                        url=url,
                        title=title,
                        source=self.source,
                        source_type=self.source_type,
                        published_at=published,
                        hot_score=hot,
                        content="",  # HN 为链接聚合，正文另抓（一期仅用标题）
                        raw=item,
                    )
                )
                if len(items) >= self.max_items:
                    break
            return items
