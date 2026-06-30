# -*- coding: utf-8 -*-
import requests
from app.providers.base import TextProvider
from app.providers.volcano import ARK_BASE

MODEL = "doubao-seed-1-6-251015"


class VolcanoText(TextProvider):
    model = MODEL

    def complete(self, creds: dict, system: str, user: str, images: list = None) -> str:
        api_key = creds["api_key"]
        model = creds.get("text_model") or self.model
        # 豆包多模态：有参考图则用 content 数组（text + image_url），模型据图参考
        if images:
            uc = [{"type": "text", "text": user}] + [
                {"type": "image_url", "image_url": {"url": u}} for u in images]
            user_msg = {"role": "user", "content": uc}
        else:
            user_msg = {"role": "user", "content": user}
        body = {"model": model, "messages": [
            {"role": "system", "content": system}, user_msg]}
        r = requests.post(ARK_BASE + "/chat/completions", json=body, timeout=180,
                          headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        j = r.json()
        if r.status_code != 200 or "choices" not in j:
            raise RuntimeError(f"导演失败 {j.get('error', r.text[:200])}")
        return j["choices"][0]["message"]["content"]

    def vision_describe(self, creds: dict, images: list) -> str:
        if not images:
            return ""
        try:
            return self.complete(
                creds, "你是图像分析助手。",
                "请详细描述这些图片中的主体(人物/产品/物体)外观特征、场景与整体风格，用于创作视频分镜。直接给出描述。",
                images=images)
        except Exception:
            return ""
