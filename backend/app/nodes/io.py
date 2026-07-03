# -*- coding: utf-8 -*-
"""IO 与输出节点：加载参考主体 / 预览 / 拼接成片。

OUTPUT_NODE=True 的节点是执行目标，引擎从它们反向求解子图（等价 ComfyUI）。
"""
import os
import asyncio
from app.engine.node import NodeBase
from app.engine.registry import register
from app.engine.types import IMAGE, VIDEO, AUDIO, IMAGE_REF, MediaRef, ReferenceSet
from app.core.config import UPLOAD_DIR
from app.services import ffmpeg as ff
from app.services.storage import unique


@register
class LoadReference(NodeBase):
    """加载参考主体（角色一致性）。paths 每行一个文件名（已通过 /upload 上传到 uploads/）。"""
    CATEGORY = "输入"
    RETURN_TYPES = (IMAGE_REF,)
    RETURN_NAMES = ("refs",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"paths": ("TEXT", {"multiline": True, "default": ""})}}

    async def execute(self, ctx, paths):
        items = []
        for line in (paths or "").splitlines():
            name = line.strip().replace("/uploads/", "")
            if not name:
                continue
            local = os.path.join(UPLOAD_DIR, name)
            if not os.path.exists(local):
                continue
            kind = "video" if os.path.splitext(name)[1].lower() in (".mp4", ".mov", ".webm", ".mkv") else "image"
            items.append(MediaRef(url="/uploads/" + name, kind=kind, local_path=local))
        if not items:
            raise RuntimeError("没有可用参考主体；请先上传素材并把文件名填进来")
        return (ReferenceSet(items=items),)


@register
class LoadImage(NodeBase):
    """加载单张本地图片（已上传到 uploads/），输出 IMAGE。
    与 LoadReference 的区别：这里是普通图像，可直接接 Avatar 肖像、VideoI2V 首帧、GenImage 底图。"""
    CATEGORY = "输入"
    RETURN_TYPES = (IMAGE,)
    RETURN_NAMES = ("image",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"name": ("TEXT", {"default": ""})}}

    async def execute(self, ctx, name):
        name = (name or "").strip().replace("/uploads/", "")
        local = os.path.join(UPLOAD_DIR, name)
        if not name or not os.path.exists(local):
            raise RuntimeError(f"图片不存在：{name or '(空)'}；请先上传素材并填文件名")
        return (MediaRef(url="/uploads/" + name, kind="image", local_path=local),)


@register
class PreviewImage(NodeBase):
    """预览图像（终端节点）。仅用于在画布上看结果，无产物。"""
    CATEGORY = "输出"
    OUTPUT_NODE = True
    RETURN_TYPES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"image": (IMAGE, {})}}

    @classmethod
    def is_cacheable(cls):
        return False

    async def execute(self, ctx, image):
        ctx.emit("preview", {"type": "image", "url": image.url})
        return ()


@register
class Preview(NodeBase):
    """通用预览（终端节点）：图片/视频/音频接哪个就预览哪个。任何工作流都可以拿它当输出终点。"""
    CATEGORY = "输出"
    OUTPUT_NODE = True
    RETURN_TYPES = ()

    @classmethod
    def INPUT_TYPES(cls):
        return {"optional": {"image": (IMAGE, {}), "video": (VIDEO, {}), "audio": (AUDIO, {})}}

    @classmethod
    def is_cacheable(cls):
        return False

    async def execute(self, ctx, image=None, video=None, audio=None):
        for m in (image, video, audio):
            if m is not None and getattr(m, "url", None):
                ctx.emit("preview", {"type": m.kind, "url": m.url})
        return ()


@register
class ConcatVideos(NodeBase):
    """按顺序拼接分镜视频成片（需本机 ffmpeg）。最多 8 段，缺口自动跳过。"""
    CATEGORY = "输出"
    OUTPUT_NODE = True
    RETURN_TYPES = (VIDEO,)
    RETURN_NAMES = ("final",)

    @classmethod
    def INPUT_TYPES(cls):
        opt = {f"video_{i}": (VIDEO, {}) for i in range(1, 9)}
        return {"required": {"video_1": (VIDEO, {})}, "optional": {k: v for k, v in opt.items() if k != "video_1"}}

    @classmethod
    def is_cacheable(cls):
        return False  # 合成依赖本地文件，不缓存

    async def execute(self, ctx, **videos):
        if not ff.has_ffmpeg():
            raise RuntimeError("未检测到 ffmpeg，请先安装：winget install Gyan.FFmpeg")
        ordered = []
        for i in range(1, 9):
            v = videos.get(f"video_{i}")
            if v is not None and getattr(v, "local_path", None):
                ordered.append(v.local_path)
        if not ordered:
            raise RuntimeError("没有可拼接的分镜视频")
        name = unique("final", "mp4")
        out_path = await asyncio.to_thread(ff.concat, ordered, name)
        ref = MediaRef(url="/media/" + os.path.basename(out_path), kind="video", local_path=out_path)
        ctx.emit("final", {"url": ref.url})
        return (ref,)
