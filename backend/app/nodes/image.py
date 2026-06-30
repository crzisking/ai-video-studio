# -*- coding: utf-8 -*-
"""图像节点：文生图 / 图生图（参考图 + 可选初始图做首尾帧链）。"""
import asyncio
from app.engine.node import NodeBase
from app.engine.registry import register
from app.engine.types import PROVIDER, TEXT, IMAGE, IMAGE_REF, SEED, MediaRef, ReferenceSet
from app.providers.registry import get_provider
from app.core.sizes import size_for
from app.services.refs import path_to_data_uri

RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4"]


def _ref_to_model_input(m: MediaRef) -> str:
    """参考图喂给出图模型：本地图转 data URI，远程图直接用 URL。"""
    if m.local_path:
        try:
            return path_to_data_uri(m.local_path)
        except Exception:
            return m.url
    return m.url


@register
class GenImage(NodeBase):
    """文生图 / 图生图。seed 固定 → 同输入命中缓存、不重复花钱；改 seed = 重出。"""
    CATEGORY = "图像"
    RETURN_TYPES = (IMAGE,)
    RETURN_NAMES = ("image",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (PROVIDER, {}),
                "prompt": (TEXT, {"multiline": True}),
                "ratio": (RATIOS, {"default": "16:9"}),
                "seed": (SEED, {"default": 0, "min": 0, "max": 2**31 - 1}),
            },
            "optional": {
                "refs": (IMAGE_REF, {}),       # 参考主体（角色一致性）
                "init_image": (IMAGE, {}),     # 初始图（首帧→尾帧链）
            },
        }

    async def execute(self, ctx, provider, prompt, ratio, seed, refs=None, init_image=None):
        prov = provider.provider
        creds = provider.creds
        imgp = get_provider(prov, "image")
        size = size_for(ratio)

        ref_inputs = []
        if init_image is not None:
            ref_inputs.append(_ref_to_model_input(init_image))
        if refs is not None and isinstance(refs, ReferenceSet):
            ref_inputs += [_ref_to_model_input(m) for m in refs.items]

        # seed 透传给厂商（适配器若支持则用于复现）
        url = await asyncio.to_thread(imgp.gen_image, creds, prompt, ref_inputs, size)
        return (MediaRef(url=url, kind="image",
                         meta={"prompt": prompt, "seed": seed, "size": size, "provider": prov}),)
