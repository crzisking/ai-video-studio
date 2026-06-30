# -*- coding: utf-8 -*-
"""音频节点：文本转语音(TTS)。"""
import asyncio
from app.engine.node import NodeBase
from app.engine.registry import register
from app.engine.types import PROVIDER, TEXT, AUDIO
from app.providers.registry import get_provider
from app.services.storage import unique


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
