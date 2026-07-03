# -*- coding: utf-8 -*-
"""ffmpeg 后期：把多段分镜视频按顺序拼接成成片。

查找 ffmpeg 的优先级（任一命中即可，免管理员）：
  1) 环境变量 FFMPEG_PATH 指定的 exe（推荐：解压版直接指过去）
  2) 系统 PATH 里的 ffmpeg
  3) 常见安装位置（winget Links / Gyan 包目录 / C:\\ffmpeg）
"""
import os
import glob
import shutil
import subprocess

from app.core.config import OUTPUT_DIR


def ffmpeg_bin() -> str | None:
    # 0) 项目内置（backend/tools/ffmpeg/ffmpeg.exe）——随项目携带，免安装免管理员
    local = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "ffmpeg", "ffmpeg.exe")
    if os.path.exists(local):
        return os.path.abspath(local)
    p = os.environ.get("FFMPEG_PATH")
    if p and os.path.exists(p):
        return p
    w = shutil.which("ffmpeg")
    if w:
        return w
    patterns = [
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe"),
        r"C:\ffmpeg\**\ffmpeg.exe",
    ]
    for pat in patterns:
        for c in glob.glob(pat, recursive=True):
            if os.path.exists(c):
                return c
    return None


def has_ffmpeg() -> bool:
    return ffmpeg_bin() is not None


def concat(video_paths: list, out_name: str) -> str:
    """按顺序拼接（重新编码，兼容不同尺寸/编码），返回成片路径。"""
    exe = ffmpeg_bin()
    if not exe:
        raise RuntimeError("未检测到 ffmpeg：装好后可设环境变量 FFMPEG_PATH 指向 ffmpeg.exe，或把其 bin 目录加入 PATH")
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
    cmd = [exe, "-y", "-f", "concat", "-safe", "0", "-i", list_file,
           "-c:v", "libx264", "-c:a", "aac", "-pix_fmt", "yuv420p", out_path]
    r = subprocess.run(cmd, capture_output=True, text=True)
    try:
        os.remove(list_file)
    except OSError:
        pass
    if r.returncode != 0:
        raise RuntimeError("ffmpeg 拼接失败：" + (r.stderr or "")[-400:])
    return out_path
