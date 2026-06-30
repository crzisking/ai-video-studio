# -*- coding: utf-8 -*-
import datetime as dt
from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    # kind: upload | image | video | audio
    kind: Mapped[str] = mapped_column(String(20))
    url: Mapped[str | None] = mapped_column(String(1024), nullable=True)   # 公网/临时URL
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # 本地路径
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "project_id": self.project_id, "kind": self.kind,
                "url": self.url, "path": self.path, "meta": self.meta,
                "created_at": self.created_at.isoformat() if self.created_at else None}
