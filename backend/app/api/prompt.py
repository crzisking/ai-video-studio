# -*- coding: utf-8 -*-
"""节点图 API（对标 ComfyUI 的 /object_info /prompt /history + WebSocket）。

流程：前端拉 /object_info 画节点 → 连线序列化成 Prompt JSON → POST /prompt
（先校验后入队，校验失败直接 400，不花钱）→ 单 worker 串行取图执行（图内部并行）
→ WebSocket 推 executing/progress/executed/final → 断线后 GET /history 重水合。

凭据走请求体、不入图：creds = {"aliyun": {...}, "volcano": {...}}。
"""
from __future__ import annotations
import asyncio
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from app.engine.registry import object_info
from app.engine.graph import parse_and_validate, GraphError
from app.engine.executor import ExecutionContext, execute_graph

router = APIRouter(tags=["prompt"])


# ---------------- WebSocket 连接管理 ----------------
class WSManager:
    def __init__(self):
        self.conns: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.conns.add(ws)

    def disconnect(self, ws: WebSocket):
        self.conns.discard(ws)

    async def broadcast(self, msg: dict):
        dead = []
        for ws in list(self.conns):
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = WSManager()


# ---------------- 历史/状态（重水合用，MVP 内存版）----------------
HISTORY: dict[str, dict] = {}   # prompt_id -> {status, events:[], outputs:{node:preview}, error}
TASK_IDS: dict[str, dict] = {}  # prompt_id -> {node_id: task_id}（reattach 用）


@router.get("/object_info")
def get_object_info():
    return object_info()


class PromptReq(BaseModel):
    prompt: dict
    creds: dict = {}                 # {provider: {api_key:..., workspace_id:...}}
    force_rerun: Optional[list] = None  # 要绕过缓存重新生成的节点 id


# ---------------- 队列 + worker ----------------
QUEUE: "asyncio.Queue" = asyncio.Queue()


@router.post("/prompt")
async def submit_prompt(req: PromptReq):
    # 先校验后花钱：图非法直接拒绝，不入队
    try:
        parse_and_validate(req.prompt)
    except GraphError as e:
        raise HTTPException(400, f"图校验失败：{e}")

    pid = uuid.uuid4().hex
    HISTORY[pid] = {"status": "pending", "events": [], "outputs": {}, "error": None}
    TASK_IDS[pid] = {}
    await QUEUE.put((pid, req.prompt, req.creds or {}, set(req.force_rerun or [])))
    await manager.broadcast({"type": "queued", "data": {"prompt_id": pid, "remaining": QUEUE.qsize()}})
    return {"prompt_id": pid, "queue_remaining": QUEUE.qsize()}


@router.get("/history/{prompt_id}")
def get_history(prompt_id: str):
    if prompt_id not in HISTORY:
        raise HTTPException(404, "无此任务")
    return HISTORY[prompt_id]


@router.get("/history")
def list_history():
    return HISTORY


async def _worker():
    """单 worker 串行取图（图内部分支并行）。对标 ComfyUI 的单执行器。"""
    while True:
        pid, prompt, creds, force = await QUEUE.get()
        h = HISTORY[pid]
        h["status"] = "running"

        def emit(event: str, data: dict):
            msg = {"type": event, "data": {"prompt_id": pid, **data}}
            h["events"].append(msg)
            node = data.get("node")
            if event in ("executed", "cached") and node is not None:
                h["outputs"][node] = data.get("outputs")
            if event in ("preview", "final"):
                h.setdefault("results", []).append(data)
            asyncio.create_task(manager.broadcast(msg))

        def on_task_submit(node_id: str, task_id: str):
            TASK_IDS[pid][node_id] = task_id  # 落库以便重启 reattach

        ctx = ExecutionContext(run_id=pid, creds=creds, emit=emit,
                               existing_task_ids=TASK_IDS[pid], on_task_submit=on_task_submit)
        try:
            g = parse_and_validate(prompt)
            emit("execution_start", {})
            await execute_graph(g, ctx, force_rerun=force)
            h["status"] = "completed"
            emit("execution_done", {})
        except Exception as e:  # noqa: BLE001
            h["status"] = "error"
            h["error"] = str(e)
            emit("execution_error", {"error": str(e)})
        finally:
            QUEUE.task_done()


def start_worker():
    asyncio.create_task(_worker())


@router.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # 心跳/忽略
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ---------------- 素材上传（参考主体）----------------
@router.post("/upload")
async def upload(file: UploadFile = File(...)):
    from app.services.refs import save_reference, save_raw, IMG_EXT
    import os
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext in IMG_EXT:
        paths = save_reference(file.file, file.filename)
    else:
        paths = [save_raw(file.file, file.filename, tag="ref")]
    names = [os.path.basename(p) for p in paths]
    return {"names": names, "urls": ["/uploads/" + n for n in names]}
