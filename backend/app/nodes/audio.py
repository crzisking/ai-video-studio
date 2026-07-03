# -*- coding: utf-8 -*-
"""音频节点：文本转语音(TTS) / 声音复刻(CloneVoice)。"""
import asyncio
import os
from app.engine.node import NodeBase
from app.engine.registry import register
from app.engine.types import PROVIDER, TEXT, AUDIO
from app.core.config import UPLOAD_DIR
from app.providers.registry import get_provider
from app.services.storage import unique


@register
class CloneVoice(NodeBase):
    """声音复刻：给一段参考音频（10秒~1分钟、人声清晰），注册出专属音色。
    输出 voice_id，接到 TTS 的 voice 上，之后念任何文本都是这个声音。
    可缓存：同一段音频只注册一次，不重复扣费。"""
    CATEGORY = "音频"
    RETURN_TYPES = (TEXT,)
    RETURN_NAMES = ("voice",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (PROVIDER, {}),
                "name": (TEXT, {"default": ""}),   # 已上传到 uploads/ 的音频文件名
            },
        }

    async def execute(self, ctx, provider, name):
        prov, creds = provider.provider, provider.creds
        fname = (name or "").strip().replace("/uploads/", "")
        local = os.path.join(UPLOAD_DIR, fname)
        if not fname or not os.path.exists(local):
            raise RuntimeError(f"参考音频不存在：{fname or '(空)'}；请先上传音频并填文件名")
        ttsp = get_provider(prov, "tts")
        if not hasattr(ttsp, "clone"):
            raise RuntimeError(f"{prov} 暂不支持声音复刻")
        vid = await asyncio.to_thread(ttsp.clone, creds, local)
        return (vid,)


@register
class TTS(NodeBase):
    """台词/旁白 → 配音。返回音频句柄（落本地，便于后续音画同步/合成）。"""
    CATEGORY = "音频"
    RETURN_TYPES = (AUDIO,)
    RETURN_NAMES = ("audio",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (PROVIDER, {}),
                "text": (TEXT, {"multiline": True}),
                "voice": (TEXT, {"default": "longxiaochun_v2"}),
            },
        }

    async def execute(self, ctx, provider, text, voice):
        prov, creds = provider.provider, provider.creds
        ttsp = get_provider(prov, "tts")
        try:
            data = await asyncio.to_thread(ttsp.synth, creds, text, voice)
        except NotImplementedError:
            raise RuntimeError(f"{prov} 无独立TTS；火山线请用视频阶段的原生配音")
        ref = ctx.save_bytes(data, unique("tts", "mp3"), kind="audio",
                             meta={"voice": voice, "provider": prov})
        return (ref,)
