# -*- coding: utf-8 -*-
"""视频节点：首尾帧生视频(i2v) / 参考生视频(r2v) / 数字人(avatar)。

均为云任务（IS_CLOUD_TASK）：execute 内通过 ctx.run_cloud 接中央轮询器，
异步轮询 + 退避 + 进度 + 断点 reattach，绝不阻塞事件循环。
"""
import os
import asyncio
from app.engine.node import NodeBase
from app.engine.registry import register
from app.engine.types import PROVIDER, TEXT, IMAGE, VIDEO, AUDIO, IMAGE_REF, MediaRef, ReferenceSet
from app.providers.registry import get_provider
from app.services.storage import aliyun_temp_upload, unique

RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4"]
RESOLUTIONS = ["480P", "720P", "1080P"]


@register
class VideoI2V(NodeBase):
    """首/尾帧 + 运动描述 → 视频。可选音频做音画同步（仅阿里）。"""
    CATEGORY = "视频"
    IS_CLOUD_TASK = True
    RETURN_TYPES = (VIDEO,)
    RETURN_NAMES = ("video",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (PROVIDER, {}),
                "first": (IMAGE, {}),
                "motion": (TEXT, {"multiline": True, "default": ""}),
                "duration": ("INT", {"default": 5, "min": 2, "max": 15}),
                "ratio": (RATIOS, {"default": "16:9"}),
                "resolution": (RESOLUTIONS, {"default": "720P"}),
            },
            "optional": {"last": (IMAGE, {}), "audio": (AUDIO, {})},
        }

    async def execute(self, ctx, provider, first, motion, duration, ratio, resolution, last=None, audio=None):
        prov, creds = provider.provider, provider.creds
        vidp = get_provider(prov, "video")
        first_url = first.url
        last_url = last.url if last is not None else None

        audio_oss = None
        if audio is not None and prov == "aliyun" and audio.local_path and os.path.exists(audio.local_path):
            audio_oss = await asyncio.to_thread(aliyun_temp_upload, creds["api_key"], audio.local_path)

        url = await ctx.run_cloud(
            submit=lambda: vidp.submit(creds, first_url, last_url, motion, duration, ratio, resolution, audio_oss),
            poll=lambda tid: vidp.poll(creds, tid),
            label="图生视频",
        )
        out = ctx.download(url, unique("i2v", "mp4").split(os.sep)[-1], kind="video",
                           meta={"motion": motion, "duration": duration, "provider": prov})
        return (out,)


@register
class VideoR2V(NodeBase):
    """参考主体 + 运动描述 → 视频（阿里参考生视频引擎）。"""
    CATEGORY = "视频"
    IS_CLOUD_TASK = True
    RETURN_TYPES = (VIDEO,)
    RETURN_NAMES = ("video",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (PROVIDER, {}),
                "refs": (IMAGE_REF, {}),
                "motion": (TEXT, {"multiline": True, "default": ""}),
                "duration": ("INT", {"default": 5, "min": 2, "max": 15}),
                "ratio": (RATIOS, {"default": "16:9"}),
                "resolution": (RESOLUTIONS, {"default": "720P"}),
            },
        }

    async def execute(self, ctx, provider, refs, motion, duration, ratio, resolution):
        prov, creds = provider.provider, provider.creds
        if prov != "aliyun":
            raise RuntimeError("参考生视频(r2v)目前仅阿里支持")
        r2v = get_provider(prov, "r2v")

        media = []
        for m in (refs.items if isinstance(refs, ReferenceSet) else []):
            if not (m.local_path and os.path.exists(m.local_path)):
                continue
            oss = await asyncio.to_thread(aliyun_temp_upload, creds["api_key"], m.local_path)
            mt = "reference_video" if m.kind == "video" else "reference_image"
            media.append({"type": mt, "url": oss})
        if not media:
            raise RuntimeError("参考主体为空，请先接入「加载参考主体」节点")

        url = await ctx.run_cloud(
            submit=lambda: r2v.submit(creds, motion, media, resolution, ratio, duration),
            poll=lambda tid: r2v.poll(creds, tid),
            label="参考生视频",
        )
        out = ctx.download(url, unique("r2v", "mp4").split(os.sep)[-1], kind="video",
                           meta={"motion": motion, "provider": prov})
        return (out,)


@register
class Avatar(NodeBase):
    """数字人：肖像图 + 音频 → 对口型视频（仅阿里 s2v）。"""
    CATEGORY = "视频"
    IS_CLOUD_TASK = True
    RETURN_TYPES = (VIDEO,)
    RETURN_NAMES = ("video",)

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (PROVIDER, {}),
                "portrait": (IMAGE, {}),
                "audio": (AUDIO, {}),
                "resolution": (RESOLUTIONS, {"default": "720P"}),
            },
        }

    async def execute(self, ctx, provider, portrait, audio, resolution):
        prov, creds = provider.provider, provider.creds
        if prov != "aliyun":
            raise RuntimeError("数字人目前仅阿里支持")
        avp = get_provider(prov, "avatar")
        if not (audio.local_path and os.path.exists(audio.local_path)):
            raise RuntimeError("数字人需要本地音频文件")
        portrait_src = portrait.local_path if portrait.local_path else None
        if not portrait_src:
            raise RuntimeError("数字人需要本地肖像图")
        audio_oss = await asyncio.to_thread(aliyun_temp_upload, creds["api_key"], audio.local_path)
        portrait_oss = await asyncio.to_thread(aliyun_temp_upload, creds["api_key"], portrait_src)
        url = await ctx.run_cloud(
            submit=lambda: avp.submit(creds, portrait_oss, audio_oss, resolution),
            poll=lambda tid: avp.poll(creds, tid),
            label="数字人",
        )
        out = ctx.download(url, unique("avatar", "mp4").split(os.sep)[-1], kind="video",
                           meta={"provider": prov})
        return (out,)
