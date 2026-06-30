# -*- coding: utf-8 -*-
"""进程内任务运行器（替代 Redis/Celery）。
线程池执行长任务，状态写回 Job 表。后端重启会丢失运行中任务（DB 里仍可见，标记中断）。
"""
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.core.db import SessionLocal
from app.models.job import Job

_executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)


def _set(job_id: int, **fields):
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job:
            for k, v in fields.items():
                setattr(job, k, v)
            db.commit()
    finally:
        db.close()


def run_async(job_id: int, fn):
    """提交后台任务。fn() -> dict(结果)；异常则记为 failed。"""
    def task():
        _set(job_id, status="running")
        try:
            result = fn()
            _set(job_id, status="succeeded", result=result, error=None)
        except Exception as e:
            _set(job_id, status="failed", error=str(e))
    _executor.submit(task)


def mark_interrupted_on_startup():
    """启动时把残留的 running/pending 标记为 failed(中断)。"""
    db = SessionLocal()
    try:
        for job in db.query(Job).filter(Job.status.in_(["running", "pending"])).all():
            job.status = "failed"
            job.error = "服务重启中断"
        db.commit()
    finally:
        db.close()
