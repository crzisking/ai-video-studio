# -*- coding: utf-8 -*-
"""厂商列表 + 最小闭环冒烟测试（出图 / 出视频）。验证抽象层+异步队列。"""
import time
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db, SessionLocal
from app.models.job import Job
from app.providers.registry import list_providers, get_provider
from app.schemas import TestImage, TestVideo
from app.workers.runner import run_async

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("")
def providers():
    return list_providers()


def _new_job(db, type_, provider, payload):
    job = Job(type=type_, provider=provider, status="pending", payload=payload)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job.id


@router.post("/test-image")
def test_image(body: TestImage, db: Session = Depends(get_db)):
    creds = body.creds.model_dump()
    jid = _new_job(db, "test-image", body.provider, {"prompt": body.prompt, "size": body.size})

    def work():
        prov = get_provider(body.provider, "image")
        url = prov.gen_image(creds, body.prompt, [], body.size)
        return {"image_url": url}

    run_async(jid, work)
    return {"job_id": jid}


@router.post("/test-video")
def test_video(body: TestVideo, db: Session = Depends(get_db)):
    creds = body.creds.model_dump()
    jid = _new_job(db, "test-video", body.provider,
                   {"first_url": body.first_url, "prompt": body.prompt})

    def work():
        prov = get_provider(body.provider, "video")
        tid = prov.submit(creds, body.first_url, body.last_url, body.prompt,
                          body.duration, body.ratio, body.resolution)
        # 轮询直到完成
        for _ in range(150):  # 最多约 20 分钟
            status, url, err = prov.poll(creds, tid)
            if status == "SUCCEEDED":
                return {"task_id": tid, "video_url": url}
            if status == "FAILED":
                raise RuntimeError(err or "视频任务失败")
            time.sleep(8)
        raise RuntimeError("轮询超时")

    run_async(jid, work)
    return {"job_id": jid}
