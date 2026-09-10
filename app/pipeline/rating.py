from __future__ import annotations

from app.collectors.base import RawItem
from app.pipeline.llm import _call_json, _client

# 主题关键词 + 权重（PRD §1.5）。命中主题即累加权重，封顶 1.0。
_TOPIC_KEYWORDS: list[tuple[float, tuple[str, ...]]] = [
    (1.0, ("agent", "多 agent", "多agent", "multi-agent", "multi agent", "智能体", "多智能体")),
    (1.0, ("ai 硬件", "ai硬件", "ai native", "ai 眼镜", "ai眼镜", "智能眼镜", "智能耳机", "ai 耳机", "ai 芯片", "ai 手机", "ai pc", "aipc", "智能硬件", "机器人", "robot")),
    (1.0, ("端侧", "本地模型", "本地部署", "本地推理", "on-device", "on device", "edge ai", "小模型", "llama.cpp", "ollama", "量化", "蒸馏")),
    (1.0, ("家庭", "家居", "智能家居", "home ai", "家庭 ai", "家庭机器人")),
    (0.9, ("多模态", "multimodal", "文生图", "文生视频", "图像生成", "视频生成", "text-to-image", "text-to-video", "sora", "vision")),
    (0.9, ("语音", "voice", "speech", "asr", "tts", "whisper", "音频", "语音助手", "语音交互", "视觉 agent", "vision agent", "computer use", "computer-use")),
    (0.9, ("memory", "context", "知识库", "knowledge base", "上下文", "长期记忆", "long-term memory", "rag", "向量")),
    (0.9, ("mcp", "skills", "tool use", "tool-use", "工具调用", "function calling", "function call", "插件", "plugin")),
    (0.6, ("ai coding", "ai 编程", "coding", "code assistant", "代码生成", "代码助手", "代码补全", "copilot", "codex", "cursor", "编程助手", "autocomplete")),
    (0.3, ("融资", "投资", "估值", "收购", "并购", "funding", "raise", "valuation", "融资额", "亿美")),
]

# 官方一手博客来源（可信度 1.0）
_OFFICIAL_SOURCES = {
    "openai blog",
    "anthropic news",
    "google deepmind",
    "google ai blog",
    "nvidia ai blog",
    "microsoft ai blog",
    "meta ai blog",
    "xai blog",
}

_CN_MEDIA = {"机器之心", "量子位", "新智元"}


def rate_relevance(title: str, summary: str, content: str, source: str) -> float:
    """规则相关性评分：命中关注主题即累加对应权重，封顶 1.0。"""
    text = f"{title} {summary} {content} {source}".lower()
    score = 0.0
    for weight, keywords in _TOPIC_KEYWORDS:
        if any(kw in text for kw in keywords):
            score += weight
    return round(min(score, 1.0), 4)


def rate_credibility(source: str) -> float:
    """规则可信度评分：来源层级映射（官方 > 学术/媒体 > 社区 > 匿名）。"""
    s = (source or "").strip()
    lower = s.lower()
    if lower.startswith("github") or "hugging" in lower:
        return 0.7
    if lower in _OFFICIAL_SOURCES:
        return 1.0
    if lower == "hackernews":
        return 0.6
    if lower.startswith("r/"):
        return 0.5
    if s in _CN_MEDIA:
        return 0.7
    return 0.5


_RATING_SYSTEM_PROMPT = """你是资深 AI 行业分析师。请对一条资讯在三个维度上打分（均为 0.0~1.0 的小数，精确到 1 位小数即可）。

1. importance（重要性）：能力突破 / 多源确认 / 影响面 / 格局变化。里程碑式突破接近 1.0，普通动态 0.5 左右，琐碎日常接近 0.2。
2. novelty（新颖性）：真新能力 / 小优化 / 重包装 / 宣传 / 重复。全新能力接近 1.0，小幅优化 0.5 左右，重包装或重复 0.3 以下。
3. action_value（行动价值）：立即体验 / 观察 / 精读 / 机会 / 忽略。值得立即动手验证接近 1.0，值得关注 0.5 左右，可忽略 0.2 以下。

严格只输出 JSON：
{"importance": 0.0, "novelty": 0.0, "action_value": 0.0}
"""


def _clamp(value: float) -> float:
    """把分数截断到 [0, 1]。"""
    return max(0.0, min(1.0, float(value)))


def rate_with_llm(item: RawItem, title_zh: str, summary_zh: str) -> dict:
    """一次 LLM 调用合并产出重要性/新颖性/行动价值。失败返回中性 0.5。"""
    content = (item.content or "").strip()[:2000]
    user = (
        f"原文标题：{item.title}\n"
        f"原文正文/简介：{content or '(无)'}\n"
        f"来源：{item.source}\n\n"
        f"中文标题：{title_zh}\n"
        f"中文简介：{summary_zh}"
    )
    try:
        data = _call_json(_client(), _RATING_SYSTEM_PROMPT, user)
        return {
            "importance": _clamp(data.get("importance", 0.5)),
            "novelty": _clamp(data.get("novelty", 0.5)),
            "action_value": _clamp(data.get("action_value", 0.5)),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"[rating] LLM 评分失败: {exc}")
        return {"importance": 0.5, "novelty": 0.5, "action_value": 0.5}


def compute_final(
    relevance: float,
    credibility: float,
    importance: float,
    novelty: float,
    action_value: float,
) -> float:
    """加权综合分：重要性30% + 相关性30% + 可信度20% + 新颖性10% + 行动价值10%。"""
    score = (
        importance * 0.30
        + relevance * 0.30
        + credibility * 0.20
        + novelty * 0.10
        + action_value * 0.10
    )
    return round(score, 4)


def score_item(item: RawItem, title_zh: str, summary_zh: str) -> dict:
    """便捷入口：规则评分（相关性+可信度）+ LLM 评分，返回五维 + 综合分。"""
    relevance = rate_relevance(
        item.title, summary_zh, item.content, item.source
    )
    credibility = rate_credibility(item.source)
    llm = rate_with_llm(item, title_zh, summary_zh)
    importance = llm["importance"]
    novelty = llm["novelty"]
    action_value = llm["action_value"]
    return {
        "relevance_score": relevance,
        "credibility_score": credibility,
        "importance_score": importance,
        "novelty_score": novelty,
        "action_value_score": action_value,
        "final_score": compute_final(
            relevance, credibility, importance, novelty, action_value
        ),
    }
