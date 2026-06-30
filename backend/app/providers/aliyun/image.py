# -*- coding: utf-8 -*-
import requests
from app.providers.base import ImageProvider
from app.providers.aliyun import ws_base

MODEL = "wan2.7-image-pro"


class AliyunImage(ImageProvider):
    model = MODEL

    def gen_image(self, creds: dict, prompt: str, ref_images: list, size: str) -> str:
        api_key = creds["api_key"]
        ws = creds.get("workspace_id", "")
        url = ws_base(ws) + "/services/aigc/multimodal-generation/generation"
        content = [{"text": prompt}] + [{"image": u} for u in (ref_images or [])]
        # 阿里图像用 size 形如 "1664*936"
        size_star = size.replace("x", "*")
        body = {"model": self.model,
                "input": {"messages": [{"role": "user", "content": content}]},
                "parameters": {"size": size_star, "n": 1, "watermark": False}}
        r = requests.post(url, json=body, timeout=300, headers={
            "Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        j = r.json()
        if r.status_code != 200 or "output" not in j:
            raise RuntimeError(f"出图失败 {j.get('code','?')}: {j.get('message', r.text[:200])}")
        for choice in j["output"].get("choices", []):
            for c in choice.get("message", {}).get("content", []):
                if c.get("type") == "image" or "image" in c:
                    return c["image"]
        raise RuntimeError("出图返回中未找到图像URL")
