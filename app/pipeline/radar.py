from __future__ import annotations

from datetime import datetime

# 判定为「模型发布/更新」事件的标题/简介关键词
_RELEASE_KEYWORDS = (
    "发布", "推出", "开源", "上线", "release", "launch", "model", "模型",
)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def build_radar(articles: list) -> list[dict]:
    """从文章列表中识别「模型发布/更新」事件，按发布时间倒序返回（最多 20 条）。"""
    hits: list[dict] = []
    for a in articles:
        source = (getattr(a, "source", "") or "")
        title_zh = (getattr(a, "title_zh", "") or "")
        title = (getattr(a, "title", "") or "")
        summary_zh = (getattr(a, "summary_zh", "") or "")
        if source.startswith("github/"):
            is_release = True
        else:
            text = f"{title_zh} {title} {summary_zh}".lower()
            is_release = any(kw in text for kw in _RELEASE_KEYWORDS)
        if not is_release:
            continue
        hits.append(
            {
                "title_zh": title_zh,
                "title": title,
                "source": source,
                "url": getattr(a, "url", "") or "",
                "published_at": _iso(getattr(a, "published_at", None)),
                "final_score": getattr(a, "final_score", 0.0) or 0.0,
                "summary_zh": summary_zh,
            }
        )
    hits.sort(key=lambda x: x["published_at"] or "", reverse=True)
    return hits[:20]
