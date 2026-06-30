# -*- coding: utf-8 -*-
import os
import datetime as dt
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Persona(Base):
    """数字人形象：肖像图 + 音色，可复用。"""
    __tablename__ = "personas"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    portrait_path: Mapped[str] = mapped_column(String(1024))   # 本地肖像图
    voice: Mapped[str] = mapped_column(String(60), default="longxiaochun_v2")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "project_id": self.project_id, "name": self.name,
                "voice": self.voice,
                "portrait_url": "/uploads/" + os.path.basename(self.portrait_path) if self.portrait_path else None}
