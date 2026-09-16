from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# v2.0.0 新增列：列名 → 建列 DDL（ADD COLUMN 补列用，默认值安全，不重建表）
_NEW_COLUMNS: dict[str, str] = {
    "category": "VARCHAR(64) DEFAULT ''",
    "relevance_score": "FLOAT DEFAULT 0.0",
    "credibility_score": "FLOAT DEFAULT 0.0",
    "importance_score": "FLOAT DEFAULT 0.0",
    "novelty_score": "FLOAT DEFAULT 0.0",
    "action_value_score": "FLOAT DEFAULT 0.0",
    "final_score": "FLOAT DEFAULT 0.0",
    "is_read": "BOOLEAN DEFAULT 0",
    "is_starred": "BOOLEAN DEFAULT 0",
    "brief": "TEXT DEFAULT ''",
}


def _migrate_articles() -> None:
    """轻量迁移：为旧库补上 v2.0.0 新增列，保留既有数据（不 DROP 表）。"""
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(articles)"))}
        for column, ddl in _NEW_COLUMNS.items():
            if column not in existing:
                conn.execute(text(f"ALTER TABLE articles ADD COLUMN {column} {ddl}"))
        conn.commit()


def init_db() -> None:
    """建表（幂等）。导入 models 以确保模型已注册，并执行轻量迁移。"""
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_articles()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
