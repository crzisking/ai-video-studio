# -*- coding: utf-8 -*-
"""缓存：按 hash 链复用节点产物。

这是把 ComfyUI 内核搬过来最有价值的部分，但语义针对"花钱的随机生成"做了强化：
- 缓存 key = sha256(class_type + cache_extra + 归一化字面输入 + 各上游的 key)
  上游用它自己的 key 参与哈希 → 改了任一上游，下游 key 变化 → 级联失效（同 ComfyUI）。
- 凭据(PROVIDER.creds)被剔除出 key：换 workspace/账号不应导致重算。
- 种子(seed)在 key 内 → 同种子同输入复用旧结果、**不重复花钱**；"重新生成"= 改 seed 或强制重跑。

缓存是**持久化**的（落 data/cache/*.json），跨重启有效——避免崩溃后重花钱。
产物里只存 MediaRef 这种句柄（url/本地路径/meta），不存字节本身。
"""
from __future__ import annotations
import os
import json
import hashlib
from app.engine.types import MediaRef, ReferenceSet, ProviderRef
from app.core.config import settings

CACHE_DIR = os.path.join(getattr(settings, "DATA_DIR", "data"), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


# ---- 输出 <-> 可存储 JSON 的序列化 ----
def _enc(v):
    if isinstance(v, MediaRef):
        return {"__t": "media", **v.to_dict()}
    if isinstance(v, ReferenceSet):
        return {"__t": "refset", "items": [_enc(m) for m in v.items]}
    if isinstance(v, ProviderRef):
        return {"__t": "provider", "provider": v.provider}  # 不存凭据
    if isinstance(v, (list, tuple)):
        return [_enc(x) for x in v]
    return v


def _dec(v):
    if isinstance(v, dict) and "__t" in v:
        t = v["__t"]
        if t == "media":
            return MediaRef.from_dict(v)
        if t == "refset":
            return ReferenceSet(items=[_dec(x) for x in v["items"]])
        if t == "provider":
            return ProviderRef(provider=v["provider"])
    if isinstance(v, list):
        return [_dec(x) for x in v]
    return v


# ---- 字面输入归一化（剔除凭据、稳定排序）----
def _normalize_input(v):
    if _is_link(v):
        return None  # 连线不进字面哈希，改由上游 key 贡献
    if isinstance(v, ProviderRef):
        return {"provider": v.provider}
    if isinstance(v, dict) and "creds" in v and "provider" in v:
        return {"provider": v["provider"]}
    return v


def _is_link(v) -> bool:
    return isinstance(v, (list, tuple)) and len(v) == 2 and isinstance(v[0], str) and isinstance(v[1], int)


def compute_key(class_type: str, raw_inputs: dict, upstream_keys: dict, cache_extra) -> str:
    """upstream_keys: {输入名: 上游节点的cache_key}（仅连线输入有）。"""
    payload = {
        "ct": class_type,
        "extra": cache_extra,
        "lit": {k: _normalize_input(v) for k, v in sorted(raw_inputs.items()) if not _is_link(v)},
        "up": {k: upstream_keys[k] for k in sorted(upstream_keys)},
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class CacheStore:
    """持久 + 内存两级。key -> outputs(tuple)。"""
    def __init__(self):
        self._mem: dict[str, tuple] = {}

    def _path(self, key: str) -> str:
        return os.path.join(CACHE_DIR, key + ".json")

    def get(self, key: str):
        if key in self._mem:
            return self._mem[key]
        p = self._path(key)
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                outs = tuple(_dec(json.load(f)))
            self._mem[key] = outs
            return outs
        return None

    def put(self, key: str, outputs: tuple):
        self._mem[key] = outputs
        with open(self._path(key), "w", encoding="utf-8") as f:
            json.dump([_enc(o) for o in outputs], f, ensure_ascii=False)


CACHE = CacheStore()
