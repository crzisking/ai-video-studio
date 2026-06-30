# -*- coding: utf-8 -*-
"""参考主体库（wan2.7-r2v 用）：主体=图/视频 + 可选音色。最多 5 个。"""
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.project import Project
from app.models.cast import CastMember
from app.services.refs import save_reference, save_raw, IMG_EXT, VID_EXT

router = APIRouter(prefix="/projects/{pid}/cast", tags=["cast"])


@router.get("")
def list_cast(pid: int, db: Session = Depends(get_db)):
    rows = db.query(CastMember).filter(CastMember.project_id == pid).order_by(CastMember.ord, CastMember.id).all()
    # 计算 图n/视频n 标签
    ic = vc = 0
    out = []
    for m in rows:
        d = m.to_dict()
        if m.media_kind == "video":
            vc += 1; d["label"] = f"视频{vc}"
        else:
            ic += 1; d["label"] = f"图{ic}"
        out.append(d)
    return out


@router.post("")
def add_cast(pid: int, name: str = Form(""), media: UploadFile = File(...),
             voice: Optional[UploadFile] = File(None), db: Session = Depends(get_db)):
    if not db.get(Project, pid):
        raise HTTPException(404, "项目不存在")
    if db.query(CastMember).filter(CastMember.project_id == pid).count() >= 5:
        raise HTTPException(400, "参考主体最多 5 个（图+视频合计）")
    ext = os.path.splitext(media.filename or "")[1].lower()
    try:
        if ext in IMG_EXT:
            kind = "image"; mpath = save_reference(media.file, media.filename)[0]
        elif ext in VID_EXT:
            kind = "video"; mpath = save_raw(media.file, media.filename, "castvid")
        else:
            raise HTTPException(400, f"主体仅支持图片或视频，收到 {ext}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, str(e))
    vpath = None
    if voice is not None and voice.filename:
        vext = os.path.splitext(voice.filename)[1].lower()
        if vext not in (".mp3", ".wav"):
            raise HTTPException(400, "音色仅支持 mp3/wav")
        vpath = save_raw(voice.file, voice.filename, "castvoice")
    maxord = db.query(CastMember).filter(CastMember.project_id == pid).count()
    m = CastMember(project_id=pid, name=name or "", media_kind=kind, media_path=mpath,
                   voice_path=vpath, ord=maxord)
    db.add(m); db.commit(); db.refresh(m)
    return m.to_dict()


@router.delete("/{mid}")
def del_cast(pid: int, mid: int, db: Session = Depends(get_db)):
    m = db.get(CastMember, mid)
    if not m:
        raise HTTPException(404, "主体不存在")
    for p in (m.media_path, m.voice_path):
        if p and os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass
    db.delete(m); db.commit()
    return {"ok": True}
