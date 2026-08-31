from __future__ import annotations

from contextlib import asynccontextmanager

from datetime import timedelta

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db, init_db
from app.models import Article
from app.scheduler import run_pipeline, start_scheduler

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


@app.post("/update")
def trigger_update():
    """手动触发一次更新（联调/测试用）。"""
    return run_pipeline()
