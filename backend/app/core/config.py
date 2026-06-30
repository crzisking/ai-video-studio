# -*- coding: utf-8 -*-
"""全局配置（pydantic-settings）。可被 .env 覆盖。"""
import os
from pydantic_settings import BaseSettings

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Settings(BaseSettings):
    # 数据库：MVP 用 SQLite（零依赖）
    DATABASE_URL: str = f"sqlite:///{os.path.join(BACKEND_DIR, 'studio.db')}"
    # 本地数据目录（上传素材 / 生成结果）
    DATA_DIR: str = os.path.join(BACKEND_DIR, "data")
    # 允许的前端来源
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    # 线程池并发
    MAX_WORKERS: int = 8

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

UPLOAD_DIR = os.path.join(settings.DATA_DIR, "uploads")
OUTPUT_DIR = os.path.join(settings.DATA_DIR, "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
