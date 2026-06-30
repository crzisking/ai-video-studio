# -*- coding: utf-8 -*-
from app.providers.base import TTSProvider

MODEL = "cosyvoice-v2"
VOICES = [
    ("longxiaochun_v2", "知性积极女"), ("longxiaoxia_v2", "沉稳权威女"),
    ("loongbella_v2", "精准干练女"), ("longcheng_v2", "智慧青年男"),
    ("longshu_v2", "沉稳青年男"), ("longxiaocheng_v2", "磁性低音男"),
]
VALID = {v for v, _ in VOICES}


class AliyunTTS(TTSProvider):
    model = MODEL

    def synth(self, creds: dict, text: str, voice: str) -> bytes:
        import dashscope
        from dashscope.audio.tts_v2 import SpeechSynthesizer
        dashscope.api_key = creds["api_key"]
        ws = creds.get("workspace_id", "")
        if ws:
            dashscope.base_websocket_api_url = f"wss://{ws}.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference"
        if voice not in VALID:
            voice = "longxiaochun_v2"
        s = SpeechSynthesizer(model=self.model, voice=voice)
        audio = s.call(text)
        if not audio:
            raise RuntimeError("合成返回空音频（检查账户/文本）")
        return audio

    def voices(self):
        return [{"id": v, "name": n} for v, n in VOICES]

    def supports_lipsync(self) -> bool:
        return True  # 阿里可临时上传音频 → driving_audio 音画同步
