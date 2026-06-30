# -*- coding: utf-8 -*-
"""SQLAlchemy 引擎/会话/Base。SQLite 需 check_same_thread=False 以支持线程池。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    # 导入模型以注册到 Base.metadata
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _automigrate_sqlite()


def _automigrate_sqlite():
    """SQLite 轻量自动迁移：给已存在的表补上模型里新增的列（MVP 省去 alembic）。"""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    with engine.begin() as conn:
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue
            cols = {c["name"] for c in insp.get_columns(table_name)}
            for col in table.columns:
                if col.name in cols:
                    continue
                coltype = col.type.compile(dialect=engine.dialect)
                default = ""
                if col.default is not None and getattr(col.default, "arg", None) is not None \
                        and not callable(col.default.arg):
                    val = col.default.arg
                    default = f" DEFAULT '{val}'" if isinstance(val, str) else f" DEFAULT {val}"
                conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col.name}" {coltype}{default}'))
