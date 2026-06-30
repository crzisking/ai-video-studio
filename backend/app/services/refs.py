# -*- coding: utf-8 -*-
"""参考素材：上传的图片/视频 → 本地文件；读取时转 base64 data URI 喂给模型。
图像与视频抽帧都支持（模型只吃图片，视频抽帧当参考）。"""
import os
import time
import base64

from app.core.config import UPLOAD_DIR

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
VID_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def _pil_to_png_path(img, tag):
    from PIL import Image
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    w, h = img.size
    if min(w, h) < 240:
        s = 240 / min(w, h)
        img = img.resize((max(1, round(w*s)), max(1, round(h*s))), Image.LANCZOS)
    if max(img.size) > 4000:
        s = 4000 / max(img.size)
        img = img.resize((round(img.size[0]*s), round(img.size[1]*s)), Image.LANCZOS)
    path = os.path.join(UPLOAD_DIR, f"{tag}_{int(time.time()*1000)}_{w}.png")
    img.save(path, "PNG")
    return path


def save_reference(fileobj, filename: str) -> list:
    """保存一个上传文件，返回它产生的本地图片路径列表（图片1张；视频抽3帧）。
    fileobj 为二进制文件对象（FastAPI 用 UploadFile.file）。"""
    from PIL import Image
    import shutil
    try:
        fileobj.seek(0)
    except Exception:
        pass
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in IMG_EXT:
        return [_pil_to_png_path(Image.open(fileobj), "ref")]
    if ext in VID_EXT:
        import cv2
        tmp = os.path.join(UPLOAD_DIR, f"refvid_{int(time.time()*1000)}{ext}")
        with open(tmp, "wb") as out:
            shutil.copyfileobj(fileobj, out)
        paths = []
        try:
            cap = cv2.VideoCapture(tmp)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
            idxs = [int(total*p) for p in (0.25, 0.5, 0.75)] if total > 0 else []
            for idx in idxs:
                cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(total-1, idx)))
                ok, frame = cap.read()
                if ok:
                    paths.append(_pil_to_png_path(Image.fromarray(frame[:, :, ::-1]), "reff"))
            cap.release()
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        if not paths:
            raise RuntimeError("无法从视频读取画面")
        return paths
    raise RuntimeError(f"不支持的素材格式：{ext}")


def save_raw(fileobj, filename: str, tag: str = "raw") -> str:
    """原样保存上传文件(视频/音频)到 UPLOAD_DIR，返回本地路径。"""
    import shutil
    try:
        fileobj.seek(0)
    except Exception:
        pass
    ext = os.path.splitext(filename or "")[1].lower() or ".bin"
    path = os.path.join(UPLOAD_DIR, f"{tag}_{int(time.time()*1000)}{ext}")
    with open(path, "wb") as out:
        shutil.copyfileobj(fileobj, out)
    return path


def path_to_data_uri(path: str) -> str:
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def load_ref_data_uris(db, project_id: int) -> list:
    """读取项目所有参考图 → data URI 列表（用于喂出图/导演模型）。"""
    from app.models.asset import Asset
    rows = db.query(Asset).filter(Asset.project_id == project_id, Asset.kind == "ref").all()
    out = []
    for a in rows:
        if a.path and os.path.exists(a.path):
            try:
                out.append(path_to_data_uri(a.path))
            except Exception:
                pass
    return out
