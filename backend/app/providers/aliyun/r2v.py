# -*- coding: utf-8 -*-
"""万相参考生视频 wan2.7-r2v：多主体参考(图/视频)+音色 → 一致性视频。异步。"""
import requests

MODEL = "wan2.7-r2v"
GEN_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis"
TASK_URL = "https://dashscope.aliyuncs.com/api/v1/tasks/{}"


class AliyunR2V:
    model = MODEL

    def submit(self, creds, prompt, media, resolution="720P", ratio="16:9", duration=5):
        """media: [{type:'reference_image'|'reference_video', url, reference_voice?}, ...]"""
        api_key = creds["api_key"]
        body = {"model": self.model,
                "input": {"prompt": prompt, "media": media},
                "parameters": {"resolution": str(resolution).upper(), "ratio": ratio,
                               "duration": int(duration), "prompt_extend": False, "watermark": False}}
        headers = {"Authorization": f"Bearer {api_key}", "X-DashScope-Async": "enable",
                   "Content-Type": "application/json"}
        # 任意素材是临时 oss:// 时需开启解析
        def is_oss(m):
            return str(m.get("url", "")).startswith("oss://") or str(m.get("reference_voice", "")).startswith("oss://")
        if any(is_oss(m) for m in media):
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
            return "SUCCEEDED", out.get("video_url"), None
        if st in ("FAILED", "CANCELED", "UNKNOWN"):
            return "FAILED", None, f"{out.get('code','')}: {out.get('message','')}"
        return st if st in ("PENDING", "RUNNING") else "RUNNING", None, None
