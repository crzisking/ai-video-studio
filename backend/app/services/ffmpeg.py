# -*- coding: utf-8 -*-
"""ffmpeg 后期：把多段分镜视频按顺序拼接成成片。需本机安装 ffmpeg。"""
import os
import shutil
import subprocess

from app.core.config import OUTPUT_DIR


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def concat(video_paths: list, out_name: str) -> str:
    """按顺序拼接（重新编码，兼容不同尺寸/编码），返回成片路径。"""
    if not has_ffmpeg():
        raise RuntimeError("未检测到 ffmpeg，请先安装：winget install Gyan.FFmpeg（装完重开终端）")
    video_paths = [p for p in video_paths if p and os.path.exists(p)]
    if not video_paths:
        raise RuntimeError("没有可用的分镜视频")
    out_path = os.path.join(OUTPUT_DIR, out_name)
    if len(video_paths) == 1:
        shutil.copy(video_paths[0], out_path)
        return out_path
    # 用 concat 协议 + 重编码统一参数（不同分镜分辨率可能不一致）
    list_file = os.path.join(OUTPUT_DIR, "_concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for p in video_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")
    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
           "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        os.remove(list_file)
    except OSError:
        pass
    if r.returncode != 0:
        raise RuntimeError("ffmpeg 拼接失败：" + (r.stderr or "")[-400:])
    return out_path
