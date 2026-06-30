# -*- coding: utf-8 -*-
import requests
from app.providers.base import VideoProvider
from app.providers.volcano import ARK_BASE

MODEL = "doubao-seedance-1-0-pro-250528"
TASKS_URL = ARK_BASE + "/contents/generations/tasks"


class VolcanoVideo(VideoProvider):
    model = MODEL

    def submit(self, creds, first_url, last_url, prompt, duration, ratio, resolution, audio_url=None):
        api_key = creds["api_key"]
        model = creds.get("video_model") or self.model
        content = [{"type": "text", "text": prompt},
                   {"type": "image_url", "image_url": {"url": first_url}, "role": "first_frame"}]
        if last_url:
            content.append({"type": "image_url", "image_url": {"url": last_url}, "role": "last_frame"})
        body = {"model": model, "content": content, "ratio": ratio,
                "resolution": str(resolution).lower(), "duration": int(duration),
                "generate_audio": bool(creds.get("generate_audio", True))}
        r = requests.post(TASKS_URL, json=body, timeout=120,
                          headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        j = r.json()
        if r.status_code != 200 or "id" not in j:
            raise RuntimeError(f"{j.get('error', r.text[:200])}")
        return j["id"]

    def poll(self, creds, task_id):
        api_key = creds["api_key"]
        r = requests.get(f"{TASKS_URL}/{task_id}", timeout=30,
                         headers={"Authorization": f"Bearer {api_key}"})
        j = r.json()
        st = (j.get("status") or "").lower()
        if st == "succeeded":
            return "SUCCEEDED", (j.get("content") or {}).get("video_url"), None
        if st in ("failed", "expired", "cancelled", "canceled"):
            return "FAILED", None, str(j.get("error") or st)
        return "RUNNING", None, None
