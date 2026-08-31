from __future__ import annotations

from app.collectors.base import RawItem

_AI_KEYWORDS = [
    # 英文
    " ai", "artificial intelligence", " llm", "large language model", " gpt",
    "chatgpt", "claude", "gemini", "llama", "mistral", "deepseek", "qwen",
    "openai", "anthropic", "machine learning", "deep learning", "neural network",
    "transformer", "diffusion", "agent", "multimodal", "reasoning", "rlhf",
    "fine-tun", "inference", "foundation model", "text-to-", "vision model",
    "copilot", "langchain", "hugging face", "rag", "embedding", "tokenizer",
    # 中文
    "大模型", "人工智能", "机器学习", "深度学习", "神经网络", "多模态", "文生图",
    "文生视频", "智能体", "推理模型", "开源模型", "微调", "对齐", "生成式",
    "语言模型", "通用人工智能", "模型发布", "算力", "训练", "算法", "智能",
]

# 这些源本身就是 AI 垂直领域，无需关键词过滤
_AI_ONLY_SOURCES = {
    "r/MachineLearning",
    "r/LocalLLaMA",
    "r/artificial",
    "r/singularity",
    "r/OpenAI",
}


def is_ai_related(title: str, content: str = "", source: str = "") -> bool:
    if source in _AI_ONLY_SOURCES:
        return True
    text = f"{title} {content}".lower()
    return any(kw in text for kw in _AI_KEYWORDS)


def filter_ai_related(items: list[RawItem]) -> list[RawItem]:
    return [i for i in items if is_ai_related(i.title, i.content, i.source)]
