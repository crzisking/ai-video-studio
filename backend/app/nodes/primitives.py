# -*- coding: utf-8 -*-
"""基础节点：厂商句柄、文本字面量。"""
from app.engine.node import NodeBase
from app.engine.registry import register
from app.engine.types import PROVIDER, TEXT, ProviderRef


@register
class ProviderNode(NodeBase):
    """厂商选择。图里只存 provider 名；真实凭据运行时由 /prompt 注入（不入图、不入缓存）。"""
    CATEGORY = "基础"
    RETURN_TYPES = (PROVIDER,)
    RETURN_NAMES = ("provider",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"provider": (["aliyun", "volcano"], {"default": "aliyun"})}}

    @classmethod
    def is_cacheable(cls):
        # 凭据从 ctx 注入，缓存会抹掉凭据；故不缓存，保证每次拿到带凭据的句柄
        return False

    async def execute(self, ctx, provider):
        creds = ctx.creds.get(provider) or {}
        return (ProviderRef(provider=provider, creds=creds),)


@register
class TextNode(NodeBase):
    """文本字面量（提示词/旁白/台词）。"""
    CATEGORY = "基础"
    RETURN_TYPES = (TEXT,)
    RETURN_NAMES = ("text",)

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"text": (TEXT, {"multiline": True, "default": ""})}}

    async def execute(self, ctx, text):
        return (text,)
