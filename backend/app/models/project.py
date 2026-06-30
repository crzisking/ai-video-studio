# -*- coding: utf-8 -*-
import datetime as dt
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    # 产品线：drama(短剧) | promo(企业宣传)
    type: Mapped[str] = mapped_column(String(20), default="promo")
    # 厂商：aliyun | volcano
    provider: Mapped[str] = mapped_column(String(20), default="aliyun")
    brief: Mapped[str] = mapped_column(Text, default="")
    # 分镜全局风格（导演生成时写入）
    style: Mapped[str] = mapped_column(Text, default="")
    # 视频引擎：r2v(参考生视频,默认) | i2v(首尾帧)
    video_engine: Mapped[str] = mapped_column(String(10), default="r2v")
    # 流水线阶段状态：created → scripting → imaging → audio → rendering → done
    status: Mapped[str] = mapped_column(String(30), default="created")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "type": self.type,
                "provider": self.provider, "brief": self.brief, "style": self.style,
                "video_engine": self.video_engine, "status": self.status,
                "created_at": self.created_at.isoformat() if self.created_at else None}
