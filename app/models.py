from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text)  # 原文标题
    title_zh: Mapped[str] = mapped_column(Text, default="")  # 中文标题
    summary_zh: Mapped[str] = mapped_column(Text, default="")  # 中文简介
    source: Mapped[str] = mapped_column(String(255), index=True)
    source_type: Mapped[str] = mapped_column(String(64), default="")
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    hot_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    # v2.0.0 五维评分 + 分类 + 已读/收藏
    category: Mapped[str] = mapped_column(String(64), default="", index=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    credibility_score: Mapped[float] = mapped_column(Float, default=0.0)
    importance_score: Mapped[float] = mapped_column(Float, default=0.0)
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0)
    action_value_score: Mapped[float] = mapped_column(Float, default=0.0)
    final_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_json: Mapped[str] = mapped_column(Text, default="")  # 原始数据备份
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
