# -*- coding: utf-8 -*-
"""参考素材上传/列表/删除。图片直存，视频自动抽帧。"""
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.project import Project
from app.models.asset import Asset
from app.services.refs import save_reference

router = APIRouter(prefix="/projects/{pid}/assets", tags=["assets"])


@router.get("")
def list_assets(pid: int, db: Session = Depends(get_db)):
    rows = db.query(Asset).filter(Asset.project_id == pid, Asset.kind == "ref").all()
    return [a.to_dict() for a in rows]


@router.post("")
async def upload_assets(pid: int, files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    if not db.get(Project, pid):
        raise HTTPException(404, "项目不存在")
    created = []
    for f in files:
        try:
            paths = save_reference(f.file, f.filename)
        except Exception as e:
            raise HTTPException(400, str(e))
        for p in paths:
            a = Asset(project_id=pid, kind="ref", path=p, meta={"name": f.filename})
            db.add(a)
            db.flush()
            created.append(a.to_dict())
    db.commit()
    return created


@router.delete("/{aid}")
def delete_asset(pid: int, aid: int, db: Session = Depends(get_db)):
    a = db.get(Asset, aid)
    if not a:
        raise HTTPException(404, "素材不存在")
    if a.path and os.path.exists(a.path):
        try:
            os.remove(a.path)
        except OSError:
            pass
    db.delete(a)
    db.commit()
    return {"ok": True}
