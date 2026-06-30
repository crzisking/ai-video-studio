# -*- coding: utf-8 -*-
from pydantic import BaseModel
from typing import Optional


class ProjectCreate(BaseModel):
    name: str
    type: str = "promo"          # drama | promo
    provider: str = "aliyun"     # aliyun | volcano
    brief: str = ""
    video_engine: str = "r2v"    # r2v(参考生视频,默认) | i2v(首尾帧)


class Creds(BaseModel):
    api_key: str
    workspace_id: Optional[str] = ""
    # 火山可选：覆盖模型 id
    text_model: Optional[str] = None
    image_model: Optional[str] = None
    video_model: Optional[str] = None
    generate_audio: Optional[bool] = True


class TestImage(BaseModel):
    provider: str
    creds: Creds
    prompt: str
    size: str = "1024x1024"


class TestVideo(BaseModel):
    provider: str
    creds: Creds
    first_url: str
    last_url: Optional[str] = None
    prompt: str = ""
    duration: int = 5
    ratio: str = "9:16"
    resolution: str = "720p"
