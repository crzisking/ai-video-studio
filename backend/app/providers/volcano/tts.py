# -*- coding: utf-8 -*-
from app.providers.base import TTSProvider


class VolcanoTTS(TTSProvider):
    """火山 TTS 是独立语音产品(单独 appid/token)，P1 暂留桩。
    v1 火山线的声音走 Seedance 原生 generate_audio；后期接火山语音技术再实现。"""

    def synth(self, creds: dict, text: str, voice: str) -> bytes:
        raise NotImplementedError("火山独立TTS尚未接入；火山线请用 Seedance generate_audio")

    def voices(self):
        return []
