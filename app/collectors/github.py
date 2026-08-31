from __future__ import annotations

from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, RawItem

_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class GitHubTrendingCollector(BaseCollector):
    """GitHub Trending 页面抓取（无需登录，HTML 解析）。"""

    source = "github-trending"
    source_type = "github"

    def __init__(self, since: str = "daily") -> None:
        self.since = since

    def collect(self) -> list[RawItem]:
        url = f"https://github.com/trending?since={self.since}"
        headers = {"User-Agent": _USER_AGENT, "Accept": "text/html"}
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        with httpx.Client(headers=headers, follow_redirects=True, timeout=20) as client:
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

        items: list[RawItem] = []
        for rank, article in enumerate(soup.select("article.Box-row")):
            h2 = article.select_one("h2 a")
            if not h2:
                continue
            href = h2.get("href", "").strip().strip("/")
            if href.count("/") != 1 or not href:
                continue
            full_name = href
            desc_el = article.select_one("p")
            description = desc_el.get_text(" ", strip=True) if desc_el else ""
            stars = 0
            star_el = article.select_one("a[href$='/stargazers']")
            if star_el:
                star_text = star_el.get_text(strip=True).replace(",", "")
                try:
                    stars = int(star_text)
                except ValueError:
                    stars = 0
            items.append(
                RawItem(
                    url=f"https://github.com/{full_name}",
                    title=full_name,
                    source=self.source,
                    source_type=self.source_type,
                    published_at=now_utc,
                    hot_score=float(100 - rank),
                    content=description,
                    raw={"full_name": full_name, "stars": stars, "rank": rank + 1},
                )
            )
        return items
