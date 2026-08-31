from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app import sources
from app.config import settings
from app.database import SessionLocal, init_db
from app.feishu import push_news_digest
from app.models import Article
from app.pipeline.dedup import dedup
from app.pipeline.filter import filter_ai_related
from app.pipeline.llm import refine_with_check
from app.pipeline.scoring import normalize_scores


_CN_TZ = timezone(timedelta(hours=8))


def _parse_dt(s: str | None) -> datetime | None:
    """解析多种时间格式（ISO 8601 / RFC822），统一转为北京时间。"""
    if not s:
        return None
    s = s.strip()
    dt: datetime | None = None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass
    if dt is None:
        try:
            dt = parsedate_to_datetime(s)
        except (TypeError, ValueError):
            pass
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(_CN_TZ).replace(tzinfo=None)


def run_pipeline() -> dict:
    """执行一次完整流水线：采集 → 去重 → 过滤 → 热度 → LLM → 入库。"""
    init_db()
    # 1. 采集
    raw_items = []
    for collector in sources.build_collectors():
        try:
            raw_items.extend(collector.collect())
            print(f"[collector] {collector.source}: OK")
        except Exception as exc:  # noqa: BLE001
            print(f"[collector] {collector.source} 失败: {exc}")

    # 2. 去重 + 3. 关键词过滤 + 4. 热度归一化
    items = filter_ai_related(dedup(raw_items))
    normalize_scores(items)

    db = SessionLocal()
    try:
        existing = {row[0] for row in db.query(Article.url).all()}
    finally:
        db.close()
    items = [i for i in items if i.url not in existing]

    # 5. LLM 提炼 + 自检（未配置 API key 时跳过，仅存原文标题）
    has_key = bool(settings.dashscope_api_key)

    def _process(item):
        if not has_key:
            return (item, {"title_zh": "", "summary_zh": ""})
        try:
            data = refine_with_check(item)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] {item.url} 失败: {exc}")
            data = {"title_zh": "", "summary_zh": ""}
        if data is None:
            return None
        return (item, data)

    if has_key:
        with ThreadPoolExecutor(max_workers=6) as ex:
            results = list(ex.map(_process, items))
        refined = [r for r in results if r is not None]
    else:
        refined = [(item, {"title_zh": "", "summary_zh": ""}) for item in items]

    # 6. 入库
    db = SessionLocal()
    added = 0
    new_articles: list[dict] = []
    try:
        for item, data in refined:
            exists = db.query(Article).filter(Article.url == item.url).first()
            if exists:
                continue
            db.add(
                Article(
                    url=item.url,
                    title=item.title,
                    title_zh=data.get("title_zh", ""),
                    summary_zh=data.get("summary_zh", ""),
                    source=item.source,
                    source_type=item.source_type,
                    published_at=_parse_dt(item.published_at),
                    hot_score=item.hot_score,
                    raw_json=json.dumps(item.raw, ensure_ascii=False, default=str),
                )
            )
            added += 1
            new_articles.append(
                {
                    "title_zh": data.get("title_zh", ""),
                    "title": item.title,
                    "source": item.source,
                    "url": item.url,
                    "hot_score": item.hot_score,
                }
            )
        db.commit()
    finally:
        db.close()

    # 7. 飞书推送（新增 > 0 时按热度取 top 10，best-effort）
    if added > 0:
        try:
            top_articles = sorted(
                new_articles, key=lambda a: a["hot_score"], reverse=True
            )[:10]
            push_news_digest(top_articles)
        except Exception as exc:  # noqa: BLE001
            print(f"[feishu] 推送失败: {exc}")

    result = {"raw": len(raw_items), "filtered": len(items), "added": added}
    print(f"[pipeline] {result}")
    return result


def start_scheduler() -> BackgroundScheduler:
    """启动每天定时任务。"""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_pipeline,
        CronTrigger(hour=settings.update_hour, minute=settings.update_minute),
        id="daily_update",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
