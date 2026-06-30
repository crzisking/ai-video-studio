# -*- coding: utf-8 -*-
"""数字人形象库：创建(肖像+音色)/列表/删除。"""
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.project import Project
from app.models.persona import Persona
from app.services.refs import save_reference

router = APIRouter(prefix="/projects/{pid}/personas", tags=["personas"])


@router.get("")
def list_personas(pid: int, db: Session = Depends(get_db)):
    rows = db.query(Persona).filter(Persona.project_id == pid).order_by(Persona.id).all()
    return [p.to_dict() for p in rows]


@router.post("")
def create_persona(pid: int, name: str = Form(...), voice: str = Form("longxiaochun_v2"),
                   portrait: UploadFile = File(...), db: Session = Depends(get_db)):
    if not db.get(Project, pid):
        raise HTTPException(404, "项目不存在")
    try:
        paths = save_reference(portrait.file, portrait.filename)  # 肖像存为本地png
    except Exception as e:
        raise HTTPException(400, str(e))
    p = Persona(project_id=pid, name=name, voice=voice, portrait_path=paths[0])
    db.add(p); db.commit(); db.refresh(p)
    return p.to_dict()


@router.delete("/{persona_id}")
def delete_persona(pid: int, persona_id: int, db: Session = Depends(get_db)):
    p = db.get(Persona, persona_id)
    if not p:
        raise HTTPException(404, "形象不存在")
    if p.portrait_path and os.path.exists(p.portrait_path):
        try:
            os.remove(p.portrait_path)
        except OSError:
            pass
    db.delete(p); db.commit()
    return {"ok": True}
