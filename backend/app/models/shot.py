# -*- coding: utf-8 -*-
import datetime as dt
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    idx: Mapped[int] = mapped_column(Integer)               # 第几镜，从1开始
    scene: Mapped[str] = mapped_column(Text, default="")
    first_frame_prompt: Mapped[str] = mapped_column(Text, default="")
    last_frame_prompt: Mapped[str] = mapped_column(Text, default="")
    motion_prompt: Mapped[str] = mapped_column(Text, default="")
    dialogue: Mapped[str] = mapped_column(Text, default="")
    duration: Mapped[int] = mapped_column(Integer, default=5)
    # 生成方式：i2v(首尾帧) | avatar(数字人)
    kind: Mapped[str] = mapped_column(String(10), default="i2v")
    persona_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 后续阶段填充：
    first_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    last_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow,
                                                    onupdate=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "project_id": self.project_id, "idx": self.idx,
                "scene": self.scene, "first_frame_prompt": self.first_frame_prompt,
                "last_frame_prompt": self.last_frame_prompt, "motion_prompt": self.motion_prompt,
                "dialogue": self.dialogue, "duration": self.duration,
                "kind": self.kind, "persona_id": self.persona_id,
                "first_url": self.first_url, "last_url": self.last_url,
                "audio_url": self.audio_url, "video_url": self.video_url, "status": self.status}
