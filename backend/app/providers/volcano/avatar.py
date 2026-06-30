# -*- coding: utf-8 -*-
from app.providers.base import AvatarProvider


class VolcanoAvatar(AvatarProvider):
    """火山数字人(如 OmniHuman)待接入，P 阶段先留桩。"""
    def submit(self, creds, portrait_url, audio_url, resolution="720P"):
        raise NotImplementedError("火山数字人尚未接入，请用阿里(wan2.2-s2v)")

    def poll(self, creds, task_id):
        raise NotImplementedError
