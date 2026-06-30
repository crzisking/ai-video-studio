# -*- coding: utf-8 -*-
"""节点基类。约定照搬 ComfyUI（INPUT_TYPES / RETURN_TYPES / 一个执行函数），
但执行函数是 async，且区分"瞬时节点"和"云任务节点"。

子类只需声明：
    class GenImage(NodeBase):
        CATEGORY = "图像"
        @classmethod
        def INPUT_TYPES(cls):
            return {
                "required": {
                    "provider": (PROVIDER, {}),
                    "prompt":   (TEXT, {}),
                    "seed":     (SEED, {"default": 0, "min": 0, "max": 2**31}),
                },
                "optional": {"refs": (IMAGE_REF, {})},
            }
        RETURN_TYPES = (IMAGE,)
        RETURN_NAMES = ("image",)
        async def execute(self, ctx, provider, prompt, seed, refs=None):
            ...
            return (media_ref,)

INPUT_TYPES 里每个输入是 (类型, 选项dict)。选项常见键：
    default / min / max / step / multiline(文本) / 或直接给 list 表示 COMBO 下拉。
若类型位置传 list（如 ["16:9","9:16"]），表示这是个枚举 widget。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class NodeBase(ABC):
    CATEGORY: str = "其它"
    # OUTPUT_NODE: 终端节点（如"输出视频""最终合成"）。执行从这些往回求解，等价 ComfyUI。
    OUTPUT_NODE: bool = False
    # IS_CLOUD_TASK: True 表示 execute 内部会发起远程长任务，执行器据此放宽超时、纳入并发统计。
    IS_CLOUD_TASK: bool = False

    RETURN_TYPES: tuple = ()
    RETURN_NAMES: tuple = ()

    @classmethod
    @abstractmethod
    def INPUT_TYPES(cls) -> dict:
        ...

    @abstractmethod
    async def execute(self, ctx, **inputs) -> tuple:
        """返回 tuple，元素顺序对应 RETURN_TYPES。"""
        ...

    # ---- 缓存控制（可选重写）----
    @classmethod
    def is_cacheable(cls) -> bool:
        """大多数生成节点可缓存（种子固定→结果可复用，省钱）。
        纯随机/纯副作用节点（如"立即上传当前时间戳"）可返回 False。"""
        return True

    @classmethod
    def cache_extra(cls, inputs: dict) -> Any:
        """除常规输入外，额外纳入缓存哈希的因素。默认无。
        注意：凭据(PROVIDER.creds)绝不进哈希——见 cache.py 的归一化。"""
        return None

    @classmethod
    def type_name(cls) -> str:
        return cls.__name__

    @classmethod
    def describe(cls) -> dict:
        """导出给前端画节点用（等价 ComfyUI 的 /object_info 单项）。"""
        return {
            "name": cls.type_name(),
            "category": cls.CATEGORY,
            "input": cls.INPUT_TYPES(),
            "output": list(cls.RETURN_TYPES),
            "output_name": list(cls.RETURN_NAMES) or list(cls.RETURN_TYPES),
            "output_node": cls.OUTPUT_NODE,
            "is_cloud_task": cls.IS_CLOUD_TASK,
        }
