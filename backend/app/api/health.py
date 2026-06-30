# -*- coding: utf-8 -*-
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True, "service": "ai-video-studio", "version": "0.1.0"}
