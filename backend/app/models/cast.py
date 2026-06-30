# -*- coding: utf-8 -*-
import os
import datetime as dt
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class CastMember(Base):
    """参考主体（用于 wan2.7-r2v）：一张图或一段视频 + 可选音色音频。"""
    __tablename__ = "cast_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(100), default="")
    media_kind: Mapped[str] = mapped_column(String(10))   # image | video
    media_path: Mapped[str] = mapped_column(String(1024))
    voice_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ord: Mapped[int] = mapped_column(Integer, default=0)   # 排序（决定 图n/视频n 编号）
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "project_id": self.project_id, "name": self.name,
                "media_kind": self.media_kind, "ord": self.ord,
                "media_url": "/uploads/" + os.path.basename(self.media_path) if self.media_path else None,
                "voice_url": "/uploads/" + os.path.basename(self.voice_path) if self.voice_path else None}
