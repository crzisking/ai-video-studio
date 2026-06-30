# -*- coding: utf-8 -*-
"""厂商抽象层接口。所有厂商(阿里/火山)实现这些接口，业务层只依赖接口、不依赖具体厂商。

凭据约定：creds 为 dict，至少含 {"api_key": "..."}，阿里可含 {"workspace_id": "..."}。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Shot:
    idx: int
    scene: str = ""
    first_frame_prompt: str = ""
    last_frame_prompt: str = ""
    motion_prompt: str = ""
    dialogue: str = ""
    duration: int = 5


@dataclass
class Storyboard:
    title: str = ""
    style: str = ""
    shots: list = field(default_factory=list)  # list[Shot]


class TextProvider(ABC):
    """导演/脚本：文本生成。images 为可选参考图(data URI列表)，支持视觉的模型会据此参考。"""
    @abstractmethod
    def complete(self, creds: dict, system: str, user: str, images: list = None) -> str:
        ...

    def vision_describe(self, creds: dict, images: list) -> str:
        """用视觉模型读图，返回对素材(主体/外观/场景/风格)的文字描述。
        默认不支持视觉返回空串；支持的厂商重写。"""
        return ""


class ImageProvider(ABC):
    """出图：文生图 / 图生图(参考图)。size 形如 '1024x1024'。返回图片URL。"""
    @abstractmethod
    def gen_image(self, creds: dict, prompt: str, ref_images: list, size: str) -> str:
        ...


class VideoProvider(ABC):
    """视频：首尾帧(+音频)生视频。异步：submit→task_id；poll→(status, url, error)。
    status ∈ {PENDING, RUNNING, SUCCEEDED, FAILED}。"""
    @abstractmethod
    def submit(self, creds: dict, first_url: str, last_url: Optional[str], prompt: str,
               duration: int, ratio: str, resolution: str,
               audio_url: Optional[str] = None) -> str:
        ...

    @abstractmethod
    def poll(self, creds: dict, task_id: str):  # -> (status, video_url, error)
        ...


class AvatarProvider(ABC):
    """数字人：肖像图 + 音频 → 对口型视频。异步 submit/poll，同 VideoProvider。"""
    @abstractmethod
    def submit(self, creds: dict, portrait_url: str, audio_url: str, resolution: str) -> str:
        ...

    @abstractmethod
    def poll(self, creds: dict, task_id: str):  # -> (status, video_url, error)
        ...


class TTSProvider(ABC):
    """语音合成。synth 返回音频字节。voices 返回 [(id, 描述)]。"""
    @abstractmethod
    def synth(self, creds: dict, text: str, voice: str) -> bytes:
        ...

    def voices(self) -> list:
        return []

    def supports_lipsync(self) -> bool:
        """该厂商能否把本地音频换成模型可用URL以做音画同步。"""
        return False
