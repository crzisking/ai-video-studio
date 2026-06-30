# -*- coding: utf-8 -*-
"""Socket 类型系统。

参考 ComfyUI 的类型槽(IMAGE/LATENT/MODEL...)，但领域化成"做视频"需要的类型。
连线时按 SOCKET_TYPES 校验：只有兼容的类型才能连，这是第一道质量闸——
比如不允许把 AUDIO 接进图像 prompt。

数据传递约定（关键差异）：图里**不传字节/base64**，只传句柄。
- IMAGE / VIDEO / AUDIO 在引擎里都用 MediaRef 表示（url + 元信息 + 可选本地路径）。
- 字节落在资产库，节点之间只搬 MediaRef。
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, Any


# ---- 类型常量（前端画节点 socket 颜色也按这个） ----
TEXT = "TEXT"            # 提示词/脚本/旁白
IMAGE = "IMAGE"          # 单张图（MediaRef）
VIDEO = "VIDEO"          # 单段视频（MediaRef）
AUDIO = "AUDIO"          # 单段音频（MediaRef）
IMAGE_REF = "IMAGE_REF"  # 参考主体/角色形象（MediaRef 列表语义，但单槽传一个 ReferenceSet）
STORYBOARD = "STORYBOARD"  # 分镜表（结构化）
SHOT = "SHOT"            # 单个分镜
PERSONA = "PERSONA"      # 数字人形象（肖像 + 音色）
PROVIDER = "PROVIDER"    # 厂商+凭据句柄
INT = "INT"
FLOAT = "FLOAT"
SEED = "INT"             # 语义别名：种子就是 INT，但 widget 上单列出来
BOOLEAN = "BOOLEAN"
COMBO = "COMBO"          # 下拉枚举（INPUT_TYPES 里用 list 表示选项，等价 ComfyUI）

# 通配：少数节点（如"预览任意"）接受任何类型
ANY = "*"


# 连线兼容矩阵：from_type -> {可接入的 to_type}
# 默认同类型可连；这里登记额外允许的隐式转换。
_COMPAT: dict[str, set] = {
    # SEED 即 INT，已同名
    # 暂不开放隐式转换，保持严格；需要转换请显式放转换节点。
}


def types_compatible(from_type: str, to_type: str) -> bool:
    """from 输出能否接到 to 输入。ANY 任意互通。"""
    if from_type == ANY or to_type == ANY:
        return True
    if from_type == to_type:
        return True
    return to_type in _COMPAT.get(from_type, set())


@dataclass
class MediaRef:
    """IMAGE/VIDEO/AUDIO 在图里的统一句柄。绝不在图里搬字节。

    url        对外可访问地址（/media/xxx 或厂商返回的 http/oss）
    kind       image | video | audio
    local_path 本地落盘路径（合成、上传给厂商时用），可空
    meta       宽高/时长/seed/provider 原始响应等，用于复现与质量追溯
    """
    url: str
    kind: str
    local_path: Optional[str] = None
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "MediaRef":
        return MediaRef(url=d["url"], kind=d.get("kind", "image"),
                        local_path=d.get("local_path"), meta=d.get("meta", {}))


@dataclass
class ReferenceSet:
    """IMAGE_REF 句柄：一组参考主体（角色一致性用）。"""
    items: list = field(default_factory=list)  # list[MediaRef]

    def to_dict(self) -> dict:
        return {"items": [m.to_dict() if isinstance(m, MediaRef) else m for m in self.items]}


@dataclass
class ProviderRef:
    """PROVIDER 句柄：厂商 + 凭据。凭据不入缓存 key（见 cache.py）。"""
    provider: str               # aliyun | volcano
    creds: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        # 注意：对外/缓存时抹掉敏感凭据，只留 provider
        return {"provider": self.provider}
