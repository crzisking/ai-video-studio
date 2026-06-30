# -*- coding: utf-8 -*-
"""导演服务：调 TextProvider 生成结构化分镜表。短剧/企业宣传两套模板。"""
import re
import json

_COMMON = """严格只输出一个 JSON 对象，不要解释、不要markdown代码块。结构：
{
  "title": "短标题",
  "style": "贯穿全片的统一视觉风格（画风/色调/光线/镜头质感），会拼到每个分镜的出图提示词",
  "shots": [
    {
      "scene": "中文画面说明（给人看）",
      "first_frame_prompt": "该镜【起始画面】详细出图提示词（主体/动作/构图/环境）",
      "last_frame_prompt": "该镜【结束画面】详细出图提示词，应自然过渡到下一镜起始",
      "motion_prompt": "镜头运动+主体运动，用于由首帧到尾帧生成视频",
      "duration": 5,
      "dialogue": "台词/旁白，没有就空字符串"
    }
  ]
}
要求：shots 数量严格等于指定镜头数；角色/场景/风格前后一致，相邻分镜画面顺承；duration 取2-12整数；提示词画面化、具体。"""

SYSTEM_PROMO = "你是专业的企业宣传片导演。把企业/产品需求拆成有节奏的分镜：开场吸睛→卖点展示→场景应用→信任背书→结尾CTA。旁白(dialogue)用简洁有力的解说词。\n" + _COMMON

SYSTEM_DRAMA = "你是专业的短剧编剧+导演。把需求拆成有戏剧冲突的连贯分镜，注意人物设定一致、情绪递进、留钩子。台词(dialogue)写成角色对白。\n" + _COMMON

# 参考生视频(r2v)模式：每段是一句可直接喂给视频模型的提示词，用"图n/视频n"指代参考主体
SYSTEM_R2V = """你是参考生视频(wan2.7-r2v)导演。已知一组参考主体（用"图1/图2…"指代参考图片、"视频1/视频2…"指代参考视频）。
把用户需求拆成若干连贯分段，每段生成一段视频。严格只输出一个 JSON：
{
  "title": "短标题",
  "style": "统一风格描述",
  "shots": [
    {
      "scene": "中文画面说明(给人看)",
      "motion_prompt": "可直接喂给视频模型的完整中文提示词：用'图n/视频n'指代主体，描述谁做什么、运镜、以及对白（如 图1说道：“…”）",
      "dialogue": "本段对白文本(纯文本，用于展示)，没有就空",
      "duration": 5
    }
  ]
}
要求：shots 数量等于指定段数；务必用"图n/视频n"准确指代主体，保持角色/场景一致；含参考视频时每段 duration 取2-10，否则2-15；不要凭空引入参考素材里没有的新角色。"""


def cast_description(cast: list) -> str:
    """cast: [{label, name, media_kind}] → 文字清单，告诉导演有哪些主体。"""
    parts = []
    for c in cast:
        nm = c.get("name") or ""
        parts.append(f"{c['label']}={nm}（{'视频' if c['media_kind']=='video' else '图片'}主体）")
    return "；".join(parts)


def _parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        a, b = text.find("{"), text.rfind("}")
        if a != -1 and b != -1:
            return json.loads(text[a:b + 1])
        raise


def generate(text_provider, creds: dict, project_type: str, brief: str,
             num_shots: int, ratio: str, default_dur: int, images: list = None,
             engine: str = "i2v", cast_desc: str = "") -> dict:
    if engine == "r2v":
        system = SYSTEM_R2V
        user = (f"需求：{brief}\n\n参考主体：{cast_desc or '（无，纯按需求创作）'}\n"
                f"分段数量：{num_shots}\n每段时长：{default_dur}秒\n宽高比：{ratio}。"
                f"请输出 {num_shots} 段的 JSON。")
    else:
        system = SYSTEM_DRAMA if project_type == "drama" else SYSTEM_PROMO
        user = (f"需求：{brief}\n\n镜头数量：{num_shots}\n默认每镜时长：{default_dur}秒\n"
                f"宽高比：{ratio}。请输出 {num_shots} 个分镜的 JSON。")
    raw = text_provider.complete(creds, system, user, images=images)
    sb = _parse_json(raw)
    shots = sb.get("shots", [])
    if not shots:
        raise RuntimeError("分镜解析为空，请重试或调整需求描述")
    norm = []
    for i, s in enumerate(shots):
        norm.append({
            "idx": i + 1,
            "scene": s.get("scene", ""),
            "first_frame_prompt": s.get("first_frame_prompt", ""),
            "last_frame_prompt": s.get("last_frame_prompt", ""),
            "motion_prompt": s.get("motion_prompt", ""),
            "dialogue": s.get("dialogue", ""),
            "duration": int(s.get("duration", default_dur) or default_dur),
        })
    return {"title": sb.get("title", ""), "style": sb.get("style", ""), "shots": norm}
