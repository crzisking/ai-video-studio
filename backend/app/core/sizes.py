# -*- coding: utf-8 -*-
"""出图尺寸（按宽高比）。格式 'WxH'，阿里适配器会自动转成 W*H。"""
SIZE_BY_RATIO = {
    "16:9": "1664x936",
    "9:16": "936x1664",
    "1:1":  "1280x1280",
    "4:3":  "1440x1080",
    "3:4":  "1080x1440",
}


def size_for(ratio: str) -> str:
    return SIZE_BY_RATIO.get(ratio, SIZE_BY_RATIO["16:9"])
