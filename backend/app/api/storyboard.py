# -*- coding: utf-8 -*-
"""P2 剧本&分镜：生成(异步Job) + 读取/保存分镜。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.db import get_db, SessionLocal
from app.models.project import Project
from app.models.shot import Shot
from app.models.job import Job
from app.providers.registry import get_provider
from app.schemas import Creds
from app.services import director
from app.workers.runner import run_async

router = APIRouter(prefix="/projects/{pid}", tags=["storyboard"])


class GenStoryboard(BaseModel):
    creds: Creds
    brief: Optional[str] = None      # 不传则用项目已存 brief
    num_shots: int = 5
    ratio: str = "16:9"
    duration: int = 5


class ShotIn(BaseModel):
    idx: int
    scene: str = ""
    first_frame_prompt: str = ""
    last_frame_prompt: str = ""
    motion_prompt: str = ""
    dialogue: str = ""
    duration: int = 5
    kind: str = "i2v"
    persona_id: Optional[int] = None
    first_url: Optional[str] = None
    last_url: Optional[str] = None


class ShotsSave(BaseModel):
    shots: list[ShotIn]
    style: Optional[str] = None


@router.post("/storyboard:generate")
def gen_storyboard(pid: int, body: GenStoryboard, db: Session = Depends(get_db)):
    project = db.get(Project, pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    brief = (body.brief if body.brief is not None else project.brief) or ""
    if not brief.strip():
        raise HTTPException(400, "请先填写需求描述")
    # 持久化 brief
    project.brief = brief
    db.commit()

    creds = body.creds.model_dump()
    provider = project.provider
    ptype = project.type
    engine = project.video_engine or "r2v"
    num, ratio, dur = body.num_shots, body.ratio, body.duration

    job = Job(project_id=pid, type="storyboard", provider=provider, status="pending",
              payload={"num_shots": num, "ratio": ratio})
    db.add(job)
    db.commit()
    db.refresh(job)
    jid = job.id

    def work():
        from app.services.refs import load_ref_data_uris, path_to_data_uri
        from app.api.cast import list_cast as _list_cast  # 复用编号逻辑
        from app.models.cast import CastMember
        tp = get_provider(provider, "text")
        s0 = SessionLocal()
        cast_desc = ""
        try:
            if engine == "r2v":
                # 用主体库：文字清单 + 图片主体喂给 qwen3.7-plus 看
                members = s0.query(CastMember).filter(CastMember.project_id == pid).order_by(CastMember.ord, CastMember.id).all()
                ic = vc = 0
                cast = []
                imgs = []
                for m in members:
                    if m.media_kind == "video":
                        vc += 1; label = f"视频{vc}"
                    else:
                        ic += 1; label = f"图{ic}"
                        try:
                            imgs.append(path_to_data_uri(m.media_path))
                        except Exception:
                            pass
                    cast.append({"label": label, "name": m.name, "media_kind": m.media_kind})
                cast_desc = director.cast_description(cast)
                refs = imgs
            else:
                refs = load_ref_data_uris(s0, pid)
        finally:
            s0.close()
        sb = director.generate(tp, creds, ptype, brief, num, ratio, dur,
                               images=refs, engine=engine, cast_desc=cast_desc)
        # 写入 DB：替换该项目所有分镜
        s = SessionLocal()
        try:
            s.query(Shot).filter(Shot.project_id == pid).delete()
            for sh in sb["shots"]:
                s.add(Shot(project_id=pid, status="draft", **sh))
            p = s.get(Project, pid)
            p.style = sb.get("style", "")
            p.status = "scripting"
            s.commit()
        finally:
            s.close()
        return {"title": sb.get("title", ""), "style": sb.get("style", ""),
                "count": len(sb["shots"])}

    run_async(jid, work)
    return {"job_id": jid}


@router.get("/shots")
def get_shots(pid: int, db: Session = Depends(get_db)):
    project = db.get(Project, pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    shots = db.query(Shot).filter(Shot.project_id == pid).order_by(Shot.idx).all()
    return {"project": project.to_dict(), "shots": [s.to_dict() for s in shots]}


@router.put("/shots")
def save_shots(pid: int, body: ShotsSave, db: Session = Depends(get_db)):
    project = db.get(Project, pid)
    if not project:
        raise HTTPException(404, "项目不存在")
    # 保留已生成的 url：按 idx 映射旧数据
    old = {s.idx: s for s in db.query(Shot).filter(Shot.project_id == pid).all()}
    db.query(Shot).filter(Shot.project_id == pid).delete()
    for i, sh in enumerate(body.shots, start=1):
        prev = old.get(sh.idx)
        db.add(Shot(
            project_id=pid, idx=i, scene=sh.scene,
            first_frame_prompt=sh.first_frame_prompt, last_frame_prompt=sh.last_frame_prompt,
            motion_prompt=sh.motion_prompt, dialogue=sh.dialogue, duration=sh.duration,
            kind=sh.kind or "i2v", persona_id=sh.persona_id,
            first_url=sh.first_url if sh.first_url is not None else (prev.first_url if prev else None),
            last_url=sh.last_url if sh.last_url is not None else (prev.last_url if prev else None),
            audio_url=prev.audio_url if prev else None,
            video_url=prev.video_url if prev else None,
            status=prev.status if prev else "draft",
        ))
    if body.style is not None:
        project.style = body.style
    db.commit()
    return {"ok": True, "count": len(body.shots)}
