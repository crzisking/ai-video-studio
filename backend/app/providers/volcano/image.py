# -*- coding: utf-8 -*-
import requests
from app.providers.base import ImageProvider
from app.providers.volcano import ARK_BASE

MODEL = "doubao-seedream-4-0-250828"


class VolcanoImage(ImageProvider):
    model = MODEL

    def gen_image(self, creds: dict, prompt: str, ref_images: list, size: str) -> str:
        api_key = creds["api_key"]
        model = creds.get("image_model") or self.model
        body = {"model": model, "prompt": prompt, "size": size,
                "response_format": "url", "watermark": False}
        if ref_images:
            body["image"] = ref_images if len(ref_images) > 1 else ref_images[0]
        r = requests.post(ARK_BASE + "/images/generations", json=body, timeout=300,
                          headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        j = r.json()
        if r.status_code != 200 or not j.get("data"):
            raise RuntimeError(f"出图失败 {j.get('error', r.text[:200])}")
        return j["data"][0]["url"]
