from __future__ import annotations

from contextlib import asynccontextmanager

from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.models import Article
from app.pipeline.briefing import generate_briefing, generate_weekly_summary
from app.pipeline.radar import build_radar
from app.scheduler import recent_window_start, run_pipeline, start_scheduler

templates = Jinja2Templates(directory="app/templates")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = start_scheduler()
    yield
    scheduler.shutdown()


app = FastAPI(title="AI 资讯聚合", lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db), page: int = 1):
    per_page = 50
    total = db.query(Article).count()
    articles = (
        db.query(Article)
        .order_by(
            func.date(Article.published_at).desc(),
            Article.hot_score.desc(),
            Article.published_at.desc(),
        )
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    total_pages = (total + per_page - 1) // per_page
    latest = db.query(func.max(Article.created_at)).scalar()
    latest_cn = latest + timedelta(hours=8) if latest else None
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "articles": articles,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "latest_cn": latest_cn,
        },
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/history", response_class=HTMLResponse)
def history(request: Request):
    return templates.TemplateResponse(request, "history.html", {})


@app.post("/update")
def trigger_update():
    """手动触发一次更新（联调/测试用）。"""
    return run_pipeline()


def _article_to_dict(a: Article) -> dict:
    """把 Article ORM 对象序列化为 JSON 友好的 dict。"""
    return {
        "id": a.id,
        "title": a.title,
        "title_zh": a.title_zh,
        "summary_zh": a.summary_zh,
        "brief": a.brief,
        "source": a.source,
        "url": a.url,
        "category": a.category,
        "final_score": a.final_score,
        "hot_score": a.hot_score,
        "relevance_score": a.relevance_score,
        "credibility_score": a.credibility_score,
        "importance_score": a.importance_score,
        "novelty_score": a.novelty_score,
        "action_value_score": a.action_value_score,
        "is_read": a.is_read,
        "is_starred": a.is_starred,
        "published_at": a.published_at.isoformat() if a.published_at else None,
    }


def _brief_dict(a: Article) -> dict:
    """供 Briefing / 周报 LLM 使用的精简 dict。"""
    return {
        "title_zh": a.title_zh,
        "title": a.title,
        "source": a.source,
        "final_score": a.final_score,
        "summary_zh": a.summary_zh,
    }


@app.get("/api/articles")
def list_articles(
    category: str | None = None,
    status: str | None = None,
    sort: str = "final_score",
    page: int = 1,
    per_page: int = 20,
    since: str | None = None,
    date: str | None = None,
    days: int | None = None,
    db: Session = Depends(get_db),
):
    """文章列表 JSON API：支持分类/状态筛选、日期窗口过滤、排序与分页。"""
    query = db.query(Article)
    if category:
        query = query.filter(Article.category == category)
    if status == "unread":
        query = query.filter(Article.is_read.is_(False))
    elif status == "starred":
        query = query.filter(Article.is_starred.is_(True))

    if since:
        try:
            since_dt = datetime.strptime(since, "%Y-%m-%d")
            query = query.filter(Article.published_at >= since_dt)
        except ValueError:
            pass
    if date:
        try:
            date_dt = datetime.strptime(date, "%Y-%m-%d")
            next_dt = date_dt + timedelta(days=1)
            query = query.filter(
                Article.published_at >= date_dt,
                Article.published_at < next_dt,
            )
        except ValueError:
            pass
    if days is not None:
        query = query.filter(Article.published_at >= recent_window_start(days - 1))

    if sort == "hot":
        query = query.order_by(Article.hot_score.desc())
    elif sort == "latest":
        query = query.order_by(Article.published_at.desc().nullslast())
    else:
        query = query.order_by(Article.final_score.desc())

    total = query.count()
    articles = (
        query.offset((page - 1) * per_page).limit(per_page).all()
    )
    return {"total": total, "articles": [_article_to_dict(a) for a in articles]}


@app.post("/api/articles/{article_id}/read")
def mark_read(article_id: int, db: Session = Depends(get_db)):
    """标记已读（幂等置 True）。"""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    article.is_read = True
    db.commit()
    db.refresh(article)
    return _article_to_dict(article)


@app.post("/api/articles/{article_id}/star")
def toggle_star(article_id: int, db: Session = Depends(get_db)):
    """切换收藏状态。"""
    article = db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    article.is_starred = not article.is_starred
    db.commit()
    db.refresh(article)
    return _article_to_dict(article)


@app.get("/api/briefing")
def get_briefing(db: Session = Depends(get_db)):
    """即时生成今日 AI Briefing（取综合分 top 10）。"""
    top = (
        db.query(Article)
        .order_by(Article.final_score.desc())
        .limit(10)
        .all()
    )
    briefing = generate_briefing([_brief_dict(a) for a in top])
    return {"briefing": briefing}


@app.get("/api/radar")
def get_radar(days: int | None = None, db: Session = Depends(get_db)):
    """模型发布雷达。"""
    if days is not None:
        articles = (
            db.query(Article)
            .filter(Article.published_at >= recent_window_start(days - 1))
            .all()
        )
    else:
        articles = db.query(Article).all()
    return build_radar(articles)


@app.post("/api/weekly")
def get_weekly(db: Session = Depends(get_db)):
    """触发生成过去 7 天的每周总结。"""
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    articles = (
        db.query(Article)
        .filter(Article.created_at >= cutoff)
        .order_by(Article.final_score.desc())
        .limit(50)
        .all()
    )
    weekly = generate_weekly_summary([_brief_dict(a) for a in articles])
    return {"weekly": weekly}
