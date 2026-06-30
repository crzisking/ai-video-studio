# -*- coding: utf-8 -*-
"""执行引擎：缓存驱动 + 异步 + 无依赖分支并行 + 可恢复。

与 ComfyUI 的关键区别：ComfyUI 串行（GPU 是瓶颈），这里**独立分支并行**
（瓶颈是远程延迟，并行是收益）。用"每节点一个 memoized asyncio.Task、
先 await 自己的上游"的写法，独立分支天然并行。

凭据不进图：ProviderNode 只在图里存 provider 名，真实 creds 由 /prompt 请求
注入到 ExecutionContext，运行时取用——保证存下的工作流 JSON 不含密钥。
"""
from __future__ import annotations
import os
import asyncio
import urllib.request
from typing import Callable, Optional

from app.core.config import OUTPUT_DIR
from app.engine.graph import ParsedGraph, prune_to_outputs
from app.engine.registry import get_node_class
from app.engine.cache import CACHE, compute_key
from app.engine import poller
from app.engine.types import MediaRef


def _is_link(v) -> bool:
    return isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], str) and isinstance(v[1], int)


class ExecutionContext:
    """传给每个节点 execute 的运行时上下文。"""

    def __init__(self, run_id: str, creds: dict, emit: Callable[[str, dict], None],
                 existing_task_ids: Optional[dict] = None,
                 on_task_submit: Optional[Callable[[str, str], None]] = None):
        self.run_id = run_id
        self.creds = creds or {}                 # {provider: {api_key:..}}
        self._emit = emit
        self.current_node_id: str = ""
        self._existing = existing_task_ids or {} # node_id -> task_id（重启恢复）
        self._on_task_submit = on_task_submit     # (node_id, task_id) 落库

    def emit(self, event: str, data: dict):
        self._emit(event, {"node": self.current_node_id, **data})

    # ---- 资产落盘：节点产出字节时调用，返回 MediaRef（图里只搬句柄）----
    def save_bytes(self, data: bytes, filename: str, kind: str = "audio", meta: dict = None) -> MediaRef:
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "wb") as f:
            f.write(data)
        return MediaRef(url="/media/" + filename, kind=kind, local_path=path, meta=meta or {})

    def download(self, url: str, filename: str, kind: str = "video", meta: dict = None) -> MediaRef:
        path = os.path.join(OUTPUT_DIR, filename)
        urllib.request.urlretrieve(url, path)
        return MediaRef(url="/media/" + filename, kind=kind, local_path=path, meta=meta or {})

    # ---- 云任务：节点内调用，自动接中央轮询器 + 进度 + reattach + task_id 落库 ----
    async def run_cloud(self, *, submit, poll, label: str) -> str:
        nid = self.current_node_id
        return await poller.run_cloud(
            submit=submit, poll=poll, label=label, emit=self.emit,
            existing_task_id=self._existing.get(nid),
            on_submit=(lambda tid: self._on_task_submit(nid, tid)) if self._on_task_submit else None,
        )


async def execute_graph(g: ParsedGraph, ctx: ExecutionContext,
                        force_rerun: Optional[set] = None) -> dict:
    """执行图，返回 {node_id: outputs(tuple)}。force_rerun 内的节点绕过缓存（重新生成）。"""
    force_rerun = force_rerun or set()
    needed = prune_to_outputs(g)
    results: dict[str, tuple] = {}
    node_keys: dict[str, str] = {}
    tasks: dict[str, asyncio.Task] = {}

    def ensure(nid: str) -> asyncio.Task:
        if nid not in tasks:
            tasks[nid] = asyncio.create_task(run_node(nid))
        return tasks[nid]

    async def run_node(nid: str):
        # 1) 先并行跑完所有上游
        dep_ids = [d for d in g.deps[nid] if d in needed]
        if dep_ids:
            await asyncio.gather(*(ensure(d) for d in dep_ids))

        node = g.nodes[nid]
        ct = node["class_type"]
        cls = get_node_class(ct)
        raw_inputs = node.get("inputs", {})

        # 2) 解析输入值 + 收集上游 cache key
        resolved = {}
        upstream_keys = {}
        for iname, ival in raw_inputs.items():
            if _is_link(ival):
                up_id, slot = ival[0], ival[1]
                resolved[iname] = results[up_id][slot]
                upstream_keys[iname] = node_keys.get(up_id, up_id)
            else:
                resolved[iname] = ival

        # 3) 缓存查询（凭据已在 cache 归一化时剔除）
        key = compute_key(ct, raw_inputs, upstream_keys, cls.cache_extra(raw_inputs))
        node_keys[nid] = key
        if cls.is_cacheable() and nid not in force_rerun:
            cached = CACHE.get(key)
            if cached is not None:
                results[nid] = cached
                ctx.current_node_id = nid
                ctx.emit("cached", {"class_type": ct})
                ctx.emit("executed", {"class_type": ct, "outputs": _preview(cached)})
                return

        # 4) 执行
        inst = cls()
        ctx.current_node_id = nid
        ctx.emit("executing", {"class_type": ct})
        outputs = await inst.execute(ctx, **resolved)
        if not isinstance(outputs, tuple):
            raise TypeError(f"节点 {nid}({ct}) 必须返回 tuple，实际 {type(outputs)}")
        results[nid] = outputs
        if cls.is_cacheable():
            CACHE.put(key, outputs)
        ctx.current_node_id = nid
        ctx.emit("executed", {"class_type": ct, "outputs": _preview(outputs)})

    # 从输出节点反向驱动；多个输出分支并行
    await asyncio.gather(*(ensure(o) for o in g.output_ids if o in needed))
    return results


def _preview(outputs: tuple) -> list:
    """给前端 ws 的轻量预览（只给 url/文本摘要，不传字节）。"""
    out = []
    for o in outputs:
        if isinstance(o, MediaRef):
            out.append({"type": o.kind, "url": o.url})
        elif isinstance(o, str):
            out.append({"type": "text", "value": o[:200]})
        else:
            out.append({"type": "value", "value": str(o)[:120]})
    return out
