from __future__ import annotations

from app.config import settings
from app.pipeline.llm import _client

_BRIEFING_SYSTEM_PROMPT = """你是资深 AI 行业分析师，负责为用户生成「今日 AI Briefing」中文简报。

要求：
1. 开头一句「今日一句话」：用一句话概括今天 AI 领域最重要的变化。
2. 之后逐条输出，每条含：**一句话结论**（这条讲了什么）+ **为什么重要**（对产品/从业者的意义）。
3. 只基于给定的资讯列表，不添加列表之外的事实。
4. 输出 Markdown 文本，不要输出代码块或 JSON。
5. 语言简洁克制，避免夸张营销语气。
"""

_WEEKLY_SYSTEM_PROMPT = """你是资深 AI 行业分析师，请根据过去一周的资讯列表生成中文「每周总结」Markdown。

结构（固定四个小节）：
1. **本周最重要变化**：概括 1-3 个真正重要的变化。
2. **升温趋势**：哪些方向在持续升温、值得关注。
3. **营销噪声判断**：哪些看似热闹实则可能只是营销/重包装。
4. **行动建议**：接下来值得体验、验证或转化为产品机会的 2-3 条建议。

只基于给定资讯列表，不添加外部事实，语言简洁克制。
"""


def _call_text(system: str, user: str, max_tokens: int = 1500) -> str:
    """调用 LLM 生成纯文本（非 JSON）。失败返回空字符串。"""
    if not settings.dashscope_api_key:
        return ""
    try:
        resp = _client().chat.completions.create(
            model=settings.dashscope_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            max_tokens=max_tokens,
            extra_body={"enable_thinking": False},
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        print(f"[briefing] LLM 调用失败: {exc}")
        return ""


def _build_user_msg(articles: list[dict]) -> str:
    lines: list[str] = []
    for i, a in enumerate(articles, start=1):
        title = (a.get("title_zh") or "").strip() or a.get("title", "")
        summary = (a.get("summary_zh") or "").strip()
        source = a.get("source", "")
        score = a.get("final_score")
        score_text = f"{score}" if score is not None else "无"
        line = (
            f"{i}. 标题：{title}\n"
            f"   来源：{source}\n"
            f"   综合分：{score_text}\n"
            f"   简介：{summary or '(无)'}"
        )
        lines.append(line)
    return "\n\n".join(lines)


def generate_briefing(articles: list[dict]) -> str:
    """生成今日 AI Briefing（一句话头条 + 逐条「结论 + 为什么重要」）。"""
    if not articles:
        return ""
    user = (
        "以下为今日按综合分排序的 top 资讯列表，请据此生成今日 AI Briefing：\n\n"
        + _build_user_msg(articles)
    )
    return _call_text(_BRIEFING_SYSTEM_PROMPT, user)


def generate_weekly_summary(articles: list[dict]) -> str:
    """生成每周总结（最重要变化 / 升温趋势 / 营销噪声 / 行动建议）。"""
    if not articles:
        return ""
    user = (
        "以下为过去一周的资讯列表，请据此生成每周总结：\n\n"
        + _build_user_msg(articles)
    )
    return _call_text(_WEEKLY_SYSTEM_PROMPT, user, max_tokens=2000)
