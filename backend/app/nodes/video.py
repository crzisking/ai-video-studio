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


async def _ensure_local(ctx, ref, kind: str, tag: str, ext: str) -> str:
    """确保媒体有本地文件路径：上游是生成节点(远程URL)时先下载下来。"""
    if ref is None:
        raise RuntimeError(f"{tag}: 缺少输入")
    if ref.local_path and os.path.exists(ref.local_path):
        return ref.local_path
    url = ref.url or ""
    if url.startswith("http"):
        got = await asyncio.to_thread(ctx.download, url, unique(tag, ext).split(os.sep)[-1], kind, {})
        return got.local_path
    if url.startswith("/media/"):
        from app.core.config import OUTPUT_DIR
        p = os.path.join(OUTPUT_DIR, os.path.basename(url))
        if os.path.exists(p):
            return p
    raise RuntimeError(f"{tag}: 拿不到可用的本地文件（url={url or '空'}）")


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
        # 上游若来自生成节点（GenImage/TTS 产出的是远程 URL），先落到本地再上传 OSS
        audio_src = await _ensure_local(ctx, audio, "audio", "avatar_audio", "mp3")
        portrait_src = await _ensure_local(ctx, portrait, "image", "avatar_portrait", "png")
        audio_oss = await asyncio.to_thread(aliyun_temp_upload, creds["api_key"], audio_src)
        portrait_oss = await asyncio.to_thread(aliyun_temp_upload, creds["api_key"], portrait_src)
        url = await ctx.run_cloud(
            submit=lambda: avp.submit(creds, portrait_oss, audio_oss, resolution),
            poll=lambda tid: avp.poll(creds, tid),
            label="数字人",
        )
        out = ctx.download(url, unique("avatar", "mp4").split(os.sep)[-1], kind="video",
                           meta={"provider": prov})
        return (out,)
