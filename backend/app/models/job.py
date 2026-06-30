# -*- coding: utf-8 -*-
import datetime as dt
from sqlalchemy import String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    # type: test-image | test-video | image | video | tts | render ...
    type: Mapped[str] = mapped_column(String(30))
    provider: Mapped[str] = mapped_column(String(20), default="")
    # status: pending | running | succeeded | failed
    status: Mapped[str] = mapped_column(String(20), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow,
                                                    onupdate=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "project_id": self.project_id, "type": self.type,
                "provider": self.provider, "status": self.status,
                "result": self.result, "error": self.error,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None}
