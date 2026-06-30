# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.project import Project
from app.schemas import ProjectCreate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
def list_projects(db: Session = Depends(get_db)):
    rows = db.query(Project).order_by(Project.id.desc()).all()
    return [p.to_dict() for p in rows]


@router.post("")
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    if body.type not in ("drama", "promo"):
        raise HTTPException(400, "type 必须是 drama 或 promo")
    if body.provider not in ("aliyun", "volcano"):
        raise HTTPException(400, "provider 必须是 aliyun 或 volcano")
    eng = body.video_engine if body.video_engine in ("r2v", "i2v") else "r2v"
    p = Project(name=body.name, type=body.type, provider=body.provider, brief=body.brief,
                video_engine=eng)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p.to_dict()


@router.patch("/{pid}")
def update_project(pid: int, body: dict, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    if "video_engine" in body and body["video_engine"] in ("r2v", "i2v"):
        p.video_engine = body["video_engine"]
    if "brief" in body:
        p.brief = body["brief"]
    db.commit()
    return p.to_dict()


@router.get("/{pid}")
def get_project(pid: int, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    return p.to_dict()


@router.delete("/{pid}")
def delete_project(pid: int, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    db.delete(p)
    db.commit()
    return {"ok": True}
