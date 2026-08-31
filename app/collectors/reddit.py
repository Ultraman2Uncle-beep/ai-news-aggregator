from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.collectors.base import BaseCollector, RawItem

_USER_AGENT = "ai-news-aggregator/1.0 (personal local use)"


class RedditCollector(BaseCollector):
    """Reddit 公开 .json 端点采集（无需登录，只读）。"""

    source_type = "reddit"

    def __init__(self, subreddit: str, limit: int = 25) -> None:
        self.source = f"r/{subreddit}"
        self.subreddit = subreddit
        self.limit = limit

    def collect(self) -> list[RawItem]:
        url = (
            f"https://www.reddit.com/r/{self.subreddit}/hot.json"
            f"?limit={self.limit}&raw_json=1"
        )
        headers = {"User-Agent": _USER_AGENT}
        with httpx.Client(headers=headers, follow_redirects=True, timeout=20) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()

        items: list[RawItem] = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            permalink = post.get("permalink", "")
            if not permalink:
                continue
            post_url = f"https://www.reddit.com{permalink}"
            title = post.get("title", "")
            content = post.get("selftext", "") or ""
            score = int(post.get("score", 0) or 0)
            num_comments = int(post.get("num_comments", 0) or 0)
            hot = float(score) + float(num_comments) * 2.0
            published = None
            created_utc = post.get("created_utc")
            if created_utc:
                published = datetime.fromtimestamp(
                    float(created_utc), tz=timezone.utc
                ).isoformat()
            items.append(
                RawItem(
                    url=post_url,
                    title=title,
                    source=self.source,
                    source_type=self.source_type,
                    published_at=published,
                    hot_score=hot,
                    content=content,
                    raw=post,
                )
            )
        return items
