from __future__ import annotations

import json

from openai import OpenAI

from app.collectors.base import RawItem
from app.config import settings

_SYSTEM_PROMPT = """你是一个严格的信息提炼助手。你的任务是把一条资讯的原文（标题+正文/简介）提炼成中文标题和中文简介。

【绝对硬性要求】
1. 只能基于"原文"里出现的信息提炼，绝不添加原文中不存在的事实、数字、人名、机构名、日期或评价。
2. 不做任何推测、联想或补充背景知识。
3. 若原文信息不足以形成简介，就如实写"原文信息有限"，绝不编造。
4. 中文标题忠实概括原文标题核心，中文简介忠实概括正文核心，语言简洁。
5. is_ai_related 判断该条是否与 AI/大模型/人工智能相关，无关则为 false。
6. 严格只输出 JSON，不要输出任何其他文字、解释或 markdown 代码块。

输出格式：
{"title_zh": "...", "summary_zh": "...", "is_ai_related": true/false}
"""

_SELFCHECK_PROMPT = """你是严格的事实核查员。请判断下面"中文摘要"里的每一个事实性陈述（数字、人名、机构、事件、日期、产品名）是否都能在"原文"中找到依据。

【规则】
- 摘要中若有任何原文里不存在的具体事实、数字、人名、机构、日期、评价 → 判定不通过（pass=false）。
- 摘要只是忠实压缩原文 → 通过（pass=true）。
- 若摘要写的是"原文信息有限"这类如实说明原文信息不足的表述，属于没有杜撰的正确行为，判定通过（pass=true）。

严格只输出 JSON：
{"pass": true/false, "reason": "若不通过，简述哪条不实"}
"""


def _client() -> OpenAI:
    return OpenAI(
        api_key=settings.dashscope_api_key,
        base_url=settings.dashscope_base_url,
    )


def _build_user_msg(item: RawItem) -> str:
    content = (item.content or "").strip()[:2000]
    return (
        f"标题：{item.title}\n"
        f"正文/简介：{content or '(无)'}\n"
        f"来源：{item.source}"
    )


def _call_json(client: OpenAI, system: str, user: str) -> dict:
    resp = client.chat.completions.create(
        model=settings.dashscope_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
        max_tokens=600,
        response_format={"type": "json_object"},
        # 关闭思考模式以节省 token（如当前模型版本不支持该参数可删除此行）
        extra_body={"enable_thinking": False},
    )
    raw_text = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return {}


def refine(item: RawItem) -> dict:
    """单条提炼+翻译。"""
    data = _call_json(_client(), _SYSTEM_PROMPT, _build_user_msg(item))
    if not data:
        return {"title_zh": item.title, "summary_zh": "", "is_ai_related": True}
    return data


def self_check(item: RawItem, title_zh: str, summary_zh: str) -> dict:
    """事实核查：摘要是否忠于原文。"""
    content = (item.content or "").strip()[:2000]
    user = (
        f"原文标题：{item.title}\n原文正文：{content or '(无)'}\n\n"
        f"中文标题：{title_zh}\n中文简介：{summary_zh}"
    )
    data = _call_json(_client(), _SELFCHECK_PROMPT, user)
    if not data:
        return {"pass": True, "reason": ""}
    return data


def refine_with_check(item: RawItem) -> dict | None:
    """提炼 + 自检。返回 None 表示丢弃（非 AI 相关或自检不通过）。"""
    data = refine(item)
    if not data.get("is_ai_related", True):
        return None
    check = self_check(item, data.get("title_zh", ""), data.get("summary_zh", ""))
    if not check.get("pass", True):
        return None
    return data
