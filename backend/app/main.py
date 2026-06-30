# -*- coding: utf-8 -*-
"""入口：节点图引擎版（重构后）。

启动时：建库 → 加载全部节点（触发 @register）→ 起执行 worker。
对外只暴露节点图 API（/object_info /prompt /history /ws /upload）+ 媒体静态服务。
旧的线性流水线路由（pipeline/storyboard/...）已退役，文件暂留待清理。
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings, OUTPUT_DIR, UPLOAD_DIR
from app.core.db import init_db
from app.engine.registry import load_all_nodes
from app.api import health, prompt as prompt_api

app = FastAPI(title="AI 短视频生成平台（节点图引擎）", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(prompt_api.router)

app.mount("/media", StaticFiles(directory=OUTPUT_DIR), name="media")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def _startup():
    init_db()
    load_all_nodes()
    prompt_api.start_worker()
