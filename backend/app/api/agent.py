# -*- coding: utf-8 -*-
"""AI 规划 API：/agent/plan —— 人话需求 → 结构化分镜方案。

方案(Plan)由前端确定性编译器拼成节点图（保证合法），再由用户审核后运行。
"""
from __future__ import annotations
import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.planner import make_plan

router = APIRouter(prefix="/agent", tags=["agent"])


class PlanReq(BaseModel):
    message: str
    creds: dict = {}
    provider: str = "aliyun"
    assets: list = []   # [{name, url}] 用户上传的参考图


@router.post("/plan")
async def plan(req: PlanReq):
    if not req.message.strip():
        raise HTTPException(400, "请描述你想要的视频")
    try:
        p = await asyncio.to_thread(make_plan, req.message, req.creds, req.provider, req.assets)
    except Exception as e:
        raise HTTPException(400, str(e))
    return p.model_dump()
