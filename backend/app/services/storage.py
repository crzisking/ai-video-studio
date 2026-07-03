# -*- coding: utf-8 -*-
"""存储服务：本地保存 + 下载 + （阿里）临时上传换公网URL。
MVP 不依赖对象存储；音画同步靠 DashScope 临时上传(仅阿里)。"""
import os
import time
import urllib.request

from app.core.config import UPLOAD_DIR, OUTPUT_DIR


def save_bytes(data: bytes, name: str, out=True) -> str:
    d = OUTPUT_DIR if out else UPLOAD_DIR
    path = os.path.join(d, name)
    with open(path, "wb") as f:
        f.write(data)
    return path


def download(url: str, name: str) -> str:
    path = os.path.join(OUTPUT_DIR, name)
    urllib.request.urlretrieve(url, path)
    return path


def aliyun_temp_upload(api_key: str, local_path: str, model: str = "wan2.7-i2v-2026-04-25") -> str:
    """把本地文件上传到 DashScope 临时OSS，返回 oss:// 地址（用于 driving_audio 音画同步）。"""
    import dashscope
    from dashscope.utils.oss_utils import check_and_upload_local
    dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"
    # dashscope 1.26 起返回 (ok, url, cert) 三元组；用 * 兼容多出来的值
    ok, url, *_ = check_and_upload_local(model, "file://" + os.path.abspath(local_path), api_key)
    return url


def unique(prefix: str, ext: str) -> str:
    return f"{prefix}_{int(time.time()*1000)}.{ext.lstrip('.')}"
