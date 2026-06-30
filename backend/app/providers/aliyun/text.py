# -*- coding: utf-8 -*-
import requests
from app.providers.base import TextProvider
from app.providers.aliyun import ws_base

MODEL = "qwen3.7-max"        # 纯文本（无参考图时用）
MODEL_VL = "qwen3.7-plus"    # 多模态（有参考图时用，直接读图写分镜）


def _extract_text(content):
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict)).strip()
    return content if isinstance(content, str) else ""


class AliyunText(TextProvider):
    model = MODEL

    def complete(self, creds: dict, system: str, user: str, images: list = None) -> str:
        api_key = creds["api_key"]
        ws = creds.get("workspace_id", "")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        if images:
            # 多模态：qwen3.7-plus 直接看图写分镜
            url = ws_base(ws) + "/services/aigc/multimodal-generation/generation"
            content = [{"text": user}] + [{"image": u} for u in images]
            body = {"model": MODEL_VL, "input": {"messages": [
                {"role": "system", "content": [{"text": system}]},
                {"role": "user", "content": content}]}}
            r = requests.post(url, json=body, timeout=180, headers=headers)
            j = r.json()
            if r.status_code != 200 or "output" not in j:
                raise RuntimeError(f"qwen-plus失败 {j.get('code','?')}: {j.get('message', r.text[:200])}")
            for ch in j["output"].get("choices", []):
                return _extract_text(ch.get("message", {}).get("content", []))
            return _extract_text(j["output"].get("text", ""))

        # 纯文本：qwen3.7-max
        url = ws_base(ws) + "/services/aigc/text-generation/generation"
        body = {"model": self.model, "input": {"messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}]},
            "parameters": {"result_format": "message"}}
        r = requests.post(url, json=body, timeout=180, headers=headers)
        j = r.json()
        if r.status_code != 200 or "output" not in j:
            raise RuntimeError(f"qwen失败 {j.get('code','?')}: {j.get('message', r.text[:200])}")
        out = j["output"]
        if out.get("choices"):
            return out["choices"][0]["message"]["content"]
        return out.get("text", "")
