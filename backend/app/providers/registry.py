# -*- coding: utf-8 -*-
"""厂商注册表：按 (provider, kind) 取实例。新增厂商只需在此登记。"""
from app.providers.aliyun.text import AliyunText
from app.providers.aliyun.image import AliyunImage
from app.providers.aliyun.video import AliyunVideo
from app.providers.aliyun.tts import AliyunTTS
from app.providers.aliyun.avatar import AliyunAvatar
from app.providers.aliyun.r2v import AliyunR2V
from app.providers.volcano.text import VolcanoText
from app.providers.volcano.image import VolcanoImage
from app.providers.volcano.video import VolcanoVideo
from app.providers.volcano.tts import VolcanoTTS
from app.providers.volcano.avatar import VolcanoAvatar

_REG = {
    "aliyun": {"text": AliyunText(), "image": AliyunImage(), "video": AliyunVideo(),
               "tts": AliyunTTS(), "avatar": AliyunAvatar(), "r2v": AliyunR2V()},
    "volcano": {"text": VolcanoText(), "image": VolcanoImage(), "video": VolcanoVideo(),
                "tts": VolcanoTTS(), "avatar": VolcanoAvatar()},
}

_META = {
    "aliyun": {"name": "阿里百炼", "needs_workspace": True,
               "models": {"text": AliyunText.model, "image": AliyunImage.model,
                          "video": AliyunVideo.model, "tts": AliyunTTS.model,
                          "avatar": AliyunAvatar.model},
               "lipsync": True, "avatar": True},
    "volcano": {"name": "火山方舟", "needs_workspace": False,
                "models": {"text": VolcanoText.model, "image": VolcanoImage.model,
                           "video": VolcanoVideo.model, "tts": None, "avatar": None},
                "lipsync": False, "avatar": False},
}


def get_provider(provider: str, kind: str):
    if provider not in _REG:
        raise ValueError(f"未知厂商: {provider}")
    if kind not in _REG[provider]:
        raise ValueError(f"厂商 {provider} 不支持 {kind}")
    return _REG[provider][kind]


def list_providers():
    out = []
    for pid, meta in _META.items():
        out.append({"id": pid, **meta})
    return out
