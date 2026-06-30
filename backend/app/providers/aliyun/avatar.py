# -*- coding: utf-8 -*-
import requests
from app.providers.base import AvatarProvider

MODEL = "wan2.2-s2v"
GEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image2video/video-synthesis"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{}"


class AliyunAvatar(AvatarProvider):
    model = MODEL

    def submit(self, creds, portrait_url, audio_url, resolution="720P"):
        api_key = creds["api_key"]
        res = resolution.upper()
        if res not in ("480P", "720P"):
            res = "720P"
        body = {"model": self.model,
                "input": {"image_url": portrait_url, "audio_url": audio_url},
                "parameters": {"resolution": res}}
        headers = {"Authorization": f"Bearer {api_key}", "X-DashScope-Async": "enable",
                   "Content-Type": "application/json"}
        if str(portrait_url).startswith("oss://") or str(audio_url).startswith("oss://"):
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
        if st == "SUCCEEDED":
            url = (out.get("results") or {}).get("video_url") or out.get("video_url")
            return "SUCCEEDED", url, None
        if st in ("FAILED", "CANCELED", "UNKNOWN"):
            return "FAILED", None, f"{out.get('code','')}: {out.get('message','')}"
        return st if st in ("PENDING", "RUNNING") else "RUNNING", None, None
