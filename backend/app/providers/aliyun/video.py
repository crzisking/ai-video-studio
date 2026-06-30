# -*- coding: utf-8 -*-
import requests
from app.providers.base import VideoProvider

MODEL = "wan2.7-i2v-2026-04-25"
GEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{}"


class AliyunVideo(VideoProvider):
    model = MODEL

    def submit(self, creds, first_url, last_url, prompt, duration, ratio, resolution, audio_url=None):
        api_key = creds["api_key"]
        media = [{"type": "first_frame", "url": first_url}]
        if last_url:
            media.append({"type": "last_frame", "url": last_url})
        if audio_url:
            media.append({"type": "driving_audio", "url": audio_url})
        body = {"model": self.model, "input": {"prompt": prompt, "media": media},
                "parameters": {"resolution": str(resolution).upper(), "duration": int(duration),
                               "prompt_extend": True, "watermark": False}}
        headers = {"Authorization": f"Bearer {api_key}", "X-DashScope-Async": "enable",
                   "Content-Type": "application/json"}
        if any(str(m["url"]).startswith("oss://") for m in media):
            headers["X-DashScope-OssResourceResolve"] = "enable"
        r = requests.post(GEN_URL, json=body, timeout=120, headers=headers)
        j = r.json()
        if r.status_code != 200 or "output" not in j:
            raise RuntimeError(f"{j.get('code','?')}: {j.get('message', r.text[:200])}")
        return j["output"]["task_id"]

    def poll(self, creds, task_id):
        api_key = creds["api_key"]
        r = requests.get(TASK_URL.format(task_id), timeout=30,
                         headers={"Authorization": f"Bearer {api_key}"})
        out = r.json().get("output", {})
        st = out.get("task_status", "UNKNOWN")
        norm = {"PENDING": "PENDING", "RUNNING": "RUNNING", "SUCCEEDED": "SUCCEEDED"}.get(st, "FAILED" if st in ("FAILED", "CANCELED", "UNKNOWN") else "RUNNING")
        return norm, out.get("video_url"), (f"{out.get('code','')}: {out.get('message','')}" if norm == "FAILED" else None)
