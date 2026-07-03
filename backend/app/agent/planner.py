# -*- coding: utf-8 -*-
"""AI 分镜规划器：把「人话需求 + 素材」变成一份结构化「分镜方案」。

关键设计：LLM 只产出抽象的 Plan（镜头类型是固定枚举），**不碰节点/连线**。
连线由前端的确定性编译器按方案拼装，保证图永远合法。
"""
from __future__ import annotations
import json
import re
from typing import List, Literal

from pydantic import BaseModel, Field, ValidationError

from app.providers.registry import get_provider

RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4"]
SHOT_TYPES = ["i2v", "first_last", "r2v", "avatar"]


class Shot(BaseModel):
    type: Literal["i2v", "first_last", "r2v", "avatar"] = "i2v"
    prompt: str = ""            # i2v/r2v 画面，或 first_last 的首帧
    prompt_last: str = ""       # first_last 尾帧画面
    motion: str = ""            # 运动/镜头描述
    duration: int = 5           # 时长（秒）2-15
    portrait_prompt: str = ""   # avatar 人像画面
    script: str = ""            # avatar 口播文案


class Plan(BaseModel):
    title: str = "未命名"
    provider: Literal["aliyun", "volcano"] = "aliyun"
    aspect: str = "9:16"
    shots: List[Shot] = Field(default_factory=list)
    narration_text: str = ""    # 全片旁白（非 avatar 时单独出一条音频）
    voice: str = "longxiaochun_v2"
    use_refs: bool = False      # 是否用用户上传的参考图保持主体一致
    portrait_edit: str = ""     # 对用户照片做图生图加工的指令（换背景/增强），空=原图直用
    summary: str = ""           # 给用户看的一句话说明


SYSTEM = """你是资深短视频导演兼分镜师。用户会用中文描述想要的短视频，你要输出一份**分镜方案**，只输出 JSON，不要解释、不要 markdown 代码块。

可用镜头类型（type）：
- "i2v"：单图生视频。给一句画面描述(prompt)+运动描述(motion)。最常用。
- "first_last"：首尾帧过渡。给首帧画面(prompt)和尾帧画面(prompt_last)+运动(motion)。适合有明显变化的镜头。
- "r2v"：参考生视频，保持主体/角色一致。仅当用户提供了参考图(素材)时用，需要 use_refs=true。
- "avatar"：数字人口播。给人像画面(portrait_prompt)和口播文案(script)。适合真人讲解/口播。

JSON 字段：
{
  "title": "短标题",
  "provider": "aliyun",              // 有 avatar/r2v 必须 aliyun
  "aspect": "9:16",                  // 只能是 16:9 / 9:16 / 1:1 / 4:3 / 3:4，竖屏短视频用 9:16
  "shots": [ {"type":"i2v","prompt":"...","motion":"...","duration":5}, ... ],
  "narration_text": "全片旁白文案（可空）",
  "voice": "longxiaochun_v2",
  "use_refs": false,
  "summary": "一句话说明你的方案思路"
}

要求：
- prompt 要具体：主体+动作+环境+光线+风格，适合 AI 出图。
- 镜头数量按时长合理拆分（每镜通常 3-5 秒），一般 2-5 个镜头。
- 若用户要"口播/讲解/真人出镜"，用 avatar 镜头并写好 script。
- 若素材里有参考图且用户要角色一致，把相关镜头设为 r2v 并 use_refs=true。
- **若用户上传了人物照片且要口播**：avatar 镜头会**直接用用户照片当肖像**，portrait_prompt 留空字符串即可，不要凭空描述新人物。
- **若用户想改照片的背景/风格**（如"背景换成科技感"）：把加工指令写进顶层字段 "portrait_edit"（例如"保持人物完全不变，将背景替换为高科技展厅，专业肖像打光，高清"），系统会先对照片做图生图再用作肖像；不需要改动时留空。
- 若给了「当前方案」，在其基础上按用户新要求修改，保留没被要求改的部分，输出**完整的**新 JSON。
- 严格输出合法 JSON。"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    # 去掉 ```json ... ``` 围栏
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    # 抓第一个 { 到最后一个 }
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("模型没有返回 JSON")
    return json.loads(m.group(0))


def make_plan(message: str, creds: dict, provider: str = "aliyun",
              assets: list = None, prev_plan: dict = None) -> Plan:
    """调用厂商文本模型（如阿里 qwen）产出方案。creds 复用生成用的同一套密钥。
    assets: [{"name": 文件名, "url": 可选URL}]——用户上传的参考图。
    prev_plan: 上一版方案——多轮修改时带上，模型在其基础上改。"""
    prov_creds = (creds or {}).get(provider) or {}
    if not prov_creds.get("api_key"):
        raise RuntimeError(f"缺少 {provider} 的 api_key，请先在「凭据」里填写")

    assets = assets or []
    text_llm = get_provider(provider, "text")
    user = message.strip()
    if prev_plan:
        user = (
            "【当前方案】\n" + json.dumps(prev_plan, ensure_ascii=False)
            + "\n\n【用户新要求】\n" + user
            + "\n\n请在当前方案基础上修改，输出完整新 JSON。"
        )
    if assets:
        names = "、".join(a.get("name", "") for a in assets if a.get("name"))
        user += (
            f"\n\n【素材】用户提供了 {len(assets)} 张参考图（{names}）。"
            "请围绕这些参考主体编排，相关镜头用 r2v（参考生视频）并设 use_refs=true，"
            "以保持主体/角色/产品在整条视频里一致。"
        )
    # 参考图 URL 若可被模型读取，则走多模态让模型"看图"写分镜
    image_urls = [a["url"] for a in assets if a.get("url", "").startswith("http")]

    last_err = None
    for attempt in range(2):
        sys = SYSTEM if attempt == 0 else SYSTEM + "\n\n上次输出无法解析，请**只输出**一个合法 JSON 对象。"
        raw = text_llm.complete(prov_creds, sys, user, images=image_urls or None)
        try:
            data = _extract_json(raw)
            plan = Plan(**data)
            # 收敛非法值
            if plan.aspect not in RATIOS:
                plan.aspect = "9:16"
            if not plan.shots:
                raise ValueError("方案里没有任何镜头")
            for s in plan.shots:
                s.duration = max(2, min(15, int(s.duration or 5)))
                if s.type not in SHOT_TYPES:
                    s.type = "i2v"
            return plan
        except (ValueError, ValidationError, json.JSONDecodeError) as e:
            last_err = e
    raise RuntimeError(f"方案解析失败：{last_err}")
