# -*- coding: utf-8 -*-
"""P3 分镜图 / P4 配音 / P5 视频 / P6 后期合成。每个动作=一个异步Job，前端轮询 /shots 看进度。"""
import os
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.core.db import get_db, SessionLocal
from app.core.config import OUTPUT_DIR
from app.core.sizes import size_for
from app.models.project import Project
from app.models.shot import Shot
from app.models.job import Job
from app.providers.registry import get_provider
from app.schemas import Creds
from app.services.refs import load_ref_data_uris
from app.services.storage import aliyun_temp_upload
from app.services import ffmpeg as ff
from app.workers.runner import run_async

router = APIRouter(prefix="/projects/{pid}", tags=["pipeline"])


class ImagesReq(BaseModel):
    creds: Creds
    ratio: str = "16:9"


class RegenReq(BaseModel):
    creds: Creds
    ratio: str = "16:9"
    which: str = "both"  # first | last | both


class AudioReq(BaseModel):
    creds: Creds
    voice: str = "longxiaochun_v2"


class VideoReq(BaseModel):
    creds: Creds
    ratio: str = "16:9"
    resolution: str = "720P"


def _job(db, pid, type_, provider):
    j = Job(project_id=pid, type=type_, provider=provider, status="pending", payload={})
    db.add(j); db.commit(); db.refresh(j)
    return j.id


def _shots(s, pid):
    return s.query(Shot).filter(Shot.project_id == pid).order_by(Shot.idx).all()


# ---------------- P3 分镜图 ----------------
@router.post("/images:generate")
def gen_images(pid: int, body: ImagesReq, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    if (p.video_engine or "r2v") == "r2v":
        raise HTTPException(400, "当前是『参考生视频』引擎，无需出分镜图；请直接到「⑤视频」生成。")
    creds = body.creds.model_dump(); provider = p.provider; ratio = body.ratio

    jid = _job(db, pid, "images", provider)

    def work():
        imgp = get_provider(provider, "image")
        s = SessionLocal()
        try:
            refs = load_ref_data_uris(s, pid)
            proj = s.get(Project, pid); style = proj.style or ""
            suf = f"。整体风格：{style}" if style else ""
            size = size_for(ratio)
            prev_last = None
            shots = _shots(s, pid)
            for sh in shots:
                if sh.kind == "avatar":
                    continue  # 数字人镜不需要首尾帧（用肖像+音频）
                first = prev_last if prev_last else imgp.gen_image(creds, sh.first_frame_prompt + suf, refs, size)
                last = imgp.gen_image(creds, sh.last_frame_prompt + suf, [first] + refs, size)
                prev_last = last
                sh.first_url = first; sh.last_url = last; sh.status = "imaged"
                s.commit()
            proj.status = "imaging"; s.commit()
            return {"count": len(shots)}
        finally:
            s.close()

    run_async(jid, work)
    return {"job_id": jid}


@router.post("/shots/{sid}/regen-image")
def regen_image(pid: int, sid: int, body: RegenReq, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    sh = db.get(Shot, sid)
    if not p or not sh:
        raise HTTPException(404, "不存在")
    creds = body.creds.model_dump(); provider = p.provider; ratio = body.ratio; which = body.which
    style = p.style or ""
    jid = _job(db, pid, "regen-image", provider)

    def work():
        imgp = get_provider(provider, "image")
        s = SessionLocal()
        try:
            refs = load_ref_data_uris(s, pid)
            suf = f"。整体风格：{style}" if style else ""
            size = size_for(ratio)
            shot = s.get(Shot, sid)
            if which in ("first", "both"):
                shot.first_url = imgp.gen_image(creds, shot.first_frame_prompt + suf, refs, size)
            base = shot.first_url
            if which in ("last", "both"):
                shot.last_url = imgp.gen_image(creds, shot.last_frame_prompt + suf,
                                               ([base] if base else []) + refs, size)
            s.commit()
            return {"first_url": shot.first_url, "last_url": shot.last_url}
        finally:
            s.close()

    run_async(jid, work)
    return {"job_id": jid}


# ---------------- P4 配音 ----------------
@router.post("/audio:generate")
def gen_audio(pid: int, body: AudioReq, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    creds = body.creds.model_dump(); provider = p.provider; voice = body.voice
    jid = _job(db, pid, "audio", provider)

    def work():
        ttsp = get_provider(provider, "tts")
        s = SessionLocal()
        try:
            done = 0
            for sh in _shots(s, pid):
                txt = (sh.dialogue or "").strip()
                if not txt:
                    continue
                try:
                    audio = ttsp.synth(creds, txt, voice)
                except NotImplementedError:
                    raise RuntimeError("当前厂商无独立TTS；火山线的声音请用 Seedance 原生配音（视频阶段）")
                name = f"shot_{sh.idx:02d}_voice.mp3"
                with open(os.path.join(OUTPUT_DIR, name), "wb") as f:
                    f.write(audio)
                sh.audio_url = "/media/" + name
                s.commit(); done += 1
            s.get(Project, pid).status = "audio"; s.commit()
            return {"voiced": done}
        finally:
            s.close()

    run_async(jid, work)
    return {"job_id": jid}


# ---------------- P5 视频 ----------------
@router.post("/video:generate")
def gen_video(pid: int, body: VideoReq, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    creds = body.creds.model_dump(); provider = p.provider
    ratio = body.ratio; resolution = body.resolution
    jid = _job(db, pid, "video", provider)

    engine = p.video_engine or "r2v"

    def work():
        import urllib.request
        from app.models.persona import Persona
        s = SessionLocal()
        try:
            shots = _shots(s, pid)

            # ===== r2v 参考生视频引擎 =====
            if engine == "r2v":
                media, has_video = _build_cast_media(s, creds, pid)
                if not media:
                    raise RuntimeError("请先在「参考主体库」上传至少 1 个主体（图片或视频）")
                r2v = get_provider(provider, "r2v")
                done = 0
                for sh in shots:
                    prompt = sh.motion_prompt or sh.scene or ""
                    dur = max(2, min(10 if has_video else 15, sh.duration or 5))
                    tid = r2v.submit(creds, prompt, media, resolution, ratio, dur)
                    url = None
                    for _ in range(200):
                        st, vu, err = r2v.poll(creds, tid)
                        if st == "SUCCEEDED":
                            url = vu; break
                        if st == "FAILED":
                            raise RuntimeError(f"第{sh.idx}段失败：{err}")
                        time.sleep(8)
                    if not url:
                        raise RuntimeError(f"第{sh.idx}段轮询超时")
                    name = f"shot_{sh.idx:02d}.mp4"
                    urllib.request.urlretrieve(url, os.path.join(OUTPUT_DIR, name))
                    sh.video_url = "/media/" + name; sh.status = "video"; s.commit(); done += 1
                s.get(Project, pid).status = "rendering"; s.commit()
                return {"count": done}

            # ===== i2v / avatar 引擎（原逻辑）=====
            vidp = get_provider(provider, "video")
            done = 0
            for sh in shots:
                if sh.kind == "avatar":
                    url = _make_avatar(s, provider, creds, sh, resolution)
                else:
                    if not sh.first_url:
                        continue
                    audio_oss = None
                    if provider == "aliyun" and sh.audio_url:
                        local = os.path.join(OUTPUT_DIR, os.path.basename(sh.audio_url))
                        if os.path.exists(local):
                            audio_oss = aliyun_temp_upload(creds["api_key"], local)
                    tid = vidp.submit(creds, sh.first_url, sh.last_url, sh.motion_prompt,
                                      sh.duration, ratio, resolution, audio_oss)
                    url = None
                    for _ in range(150):
                        st, vu, err = vidp.poll(creds, tid)
                        if st == "SUCCEEDED":
                            url = vu; break
                        if st == "FAILED":
                            raise RuntimeError(f"第{sh.idx}镜视频失败：{err}")
                        time.sleep(8)
                    if not url:
                        raise RuntimeError(f"第{sh.idx}镜轮询超时")
                name = f"shot_{sh.idx:02d}.mp4"
                urllib.request.urlretrieve(url, os.path.join(OUTPUT_DIR, name))
                sh.video_url = "/media/" + name; sh.status = "video"
                s.commit(); done += 1
            s.get(Project, pid).status = "rendering"; s.commit()
            return {"count": done}
        finally:
            s.close()

    run_async(jid, work)
    return {"job_id": jid}


def _build_cast_media(s, creds, pid):
    """参考主体库 → r2v 的 media[]：每个主体临时上传成 oss://，附音色。返回 (media, has_video)。"""
    from app.models.cast import CastMember
    members = s.query(CastMember).filter(CastMember.project_id == pid).order_by(CastMember.ord, CastMember.id).all()
    media = []
    has_video = False
    for m in members:
        url = aliyun_temp_upload(creds["api_key"], m.media_path)
        mt = "reference_video" if m.media_kind == "video" else "reference_image"
        if m.media_kind == "video":
            has_video = True
        item = {"type": mt, "url": url}
        if m.voice_path and os.path.exists(m.voice_path):
            item["reference_voice"] = aliyun_temp_upload(creds["api_key"], m.voice_path)
        media.append(item)
    return media, has_video


def _make_avatar(s, provider, creds, sh, resolution):
    """数字人单镜：肖像 + TTS(台词) → wan2.2-s2v → 返回视频URL。仅阿里支持。"""
    from app.models.persona import Persona
    if provider != "aliyun":
        raise RuntimeError(f"第{sh.idx}镜是数字人，目前仅阿里支持；请把项目厂商设为阿里")
    persona = s.get(Persona, sh.persona_id) if sh.persona_id else None
    if not persona:
        raise RuntimeError(f"第{sh.idx}镜未指定数字人形象")
    txt = (sh.dialogue or "").strip()
    if not txt:
        raise RuntimeError(f"第{sh.idx}镜是数字人但没有台词")
    # 1) 配音
    ttsp = get_provider(provider, "tts")
    audio = ttsp.synth(creds, txt, persona.voice)
    apath = os.path.join(OUTPUT_DIR, f"shot_{sh.idx:02d}_voice.mp3")
    with open(apath, "wb") as f:
        f.write(audio)
    sh.audio_url = "/media/" + os.path.basename(apath)
    # 2) 肖像+音频 上传临时OSS
    audio_oss = aliyun_temp_upload(creds["api_key"], apath)
    portrait_oss = aliyun_temp_upload(creds["api_key"], persona.portrait_path)
    # 3) s2v
    avp = get_provider(provider, "avatar")
    tid = avp.submit(creds, portrait_oss, audio_oss, resolution)
    for _ in range(200):
        st, vu, err = avp.poll(creds, tid)
        if st == "SUCCEEDED":
            return vu
        if st == "FAILED":
            raise RuntimeError(f"第{sh.idx}镜数字人失败：{err}")
        time.sleep(8)
    raise RuntimeError(f"第{sh.idx}镜数字人轮询超时")


# ---------------- P6 后期合成 ----------------
@router.post("/render")
def render_final(pid: int, db: Session = Depends(get_db)):
    p = db.get(Project, pid)
    if not p:
        raise HTTPException(404, "项目不存在")
    if not ff.has_ffmpeg():
        raise HTTPException(400, "未检测到 ffmpeg，请先安装：winget install Gyan.FFmpeg（装完重开终端）")
    jid = _job(db, pid, "render", p.provider)

    def work():
        s = SessionLocal()
        try:
            shots = _shots(s, pid)
            paths = [os.path.join(OUTPUT_DIR, os.path.basename(sh.video_url))
                     for sh in shots if sh.video_url]
            if not paths:
                raise RuntimeError("还没有分镜视频，请先在⑤生成视频")
            out = ff.concat(paths, f"final_p{pid}_{int(time.time())}.mp4")
            s.get(Project, pid).status = "done"; s.commit()
            return {"final_url": "/media/" + os.path.basename(out)}
        finally:
            s.close()

    run_async(jid, work)
    return {"job_id": jid}
