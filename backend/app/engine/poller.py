# -*- coding: utf-8 -*-
"""中央云任务轮询器。替代旧代码里每个节点一个线程 sleep(8) 的"轮询风暴"。

要点：
- provider 的 submit/poll 是同步 HTTP，这里用 asyncio.to_thread 丢线程池，**不阻塞事件循环**。
- 轮询用 asyncio.sleep + 指数退避（8s→最多 30s），同时受信号量限流，避免几十个任务同时打厂商。
- task_id 通过 on_submit 回调持久化，支持崩溃重启后 reattach（不重复提交、不重复花钱）。
- 全程 emit 进度事件给 WebSocket。
"""
from __future__ import annotations
import asyncio
from typing import Callable, Optional

# 同时在途的云任务上限（提交+轮询的并发）
_MAX_INFLIGHT = 6
_sem = asyncio.Semaphore(_MAX_INFLIGHT)

POLL_START = 8.0
POLL_MAX = 30.0
POLL_TIMEOUT = 30 * 60  # 单任务最长 30 分钟


class CloudTaskError(Exception):
    pass


async def run_cloud(
    *,
    submit: Callable[[], str],
    poll: Callable[[str], tuple],   # task_id -> (status, url, error)；status ∈ PENDING/RUNNING/SUCCEEDED/FAILED
    label: str,
    emit: Callable[[str, dict], None],
    existing_task_id: Optional[str] = None,
    on_submit: Optional[Callable[[str], None]] = None,
) -> str:
    """提交并轮询一个云任务，返回结果 URL。失败抛 CloudTaskError。

    existing_task_id: 若非空则跳过 submit，直接 reattach 轮询（重启恢复用）。
    on_submit(task_id): 提交成功后回调，用于把 task_id 落库以便 reattach。
    """
    async with _sem:
        if existing_task_id:
            task_id = existing_task_id
            emit("cloud_reattach", {"label": label, "task_id": task_id})
        else:
            task_id = await asyncio.to_thread(submit)
            if on_submit:
                on_submit(task_id)
            emit("cloud_submitted", {"label": label, "task_id": task_id})

        delay = POLL_START
        waited = 0.0
        while True:
            status, url, err = await asyncio.to_thread(poll, task_id)
            if status == "SUCCEEDED":
                emit("cloud_succeeded", {"label": label, "task_id": task_id})
                return url
            if status == "FAILED":
                raise CloudTaskError(f"{label} 失败: {err}")
            emit("cloud_progress", {"label": label, "task_id": task_id, "status": status, "waited": int(waited)})
            await asyncio.sleep(delay)
            waited += delay
            if waited >= POLL_TIMEOUT:
                raise CloudTaskError(f"{label} 轮询超时（>{POLL_TIMEOUT//60}分钟），task_id={task_id}")
            delay = min(delay * 1.3, POLL_MAX)
