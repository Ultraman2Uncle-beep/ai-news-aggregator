from __future__ import annotations

# 主题分类关键词（规则匹配，返回首个命中的主主题）。
# 顺序即优先级：越靠前越优先判定。
_CATEGORY_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("论文", ("arxiv", "paper", "论文", "技术报告", "technical report", "research paper")),
    ("开源项目", ("开源", "open source", "open-source", "github", "发版")),
    ("MCP工具", ("mcp", "tool use", "tool-use", "function calling", "function call", "工具调用", "skills", "插件", "plugin")),
    ("Memory", ("memory", "context", "知识库", "knowledge base", "上下文窗口", "长上下文", "long context", "rag", "向量")),
    ("语音", ("语音", "voice", "speech", "asr", "tts", "whisper", "音频", "audio", "语音助手", "语音交互")),
    ("端侧模型", ("端侧", "本地模型", "本地部署", "本地推理", "on-device", "on device", "edge ai", "小模型", "llama.cpp", "ollama", "量化", "蒸馏")),
    ("AI硬件", ("硬件", "芯片", "gpu", "npu", "显卡", "机器人", "眼镜", "耳机", "ai pc", "aipc", "智能硬件")),
    ("多模态", ("多模态", "multimodal", "文生图", "文生视频", "图像生成", "视频生成", "text-to-image", "text-to-video", "sora", "vision", "视觉")),
    ("模型成本", ("价格", "降价", "成本", "定价", "token 价格", "免费", "上下文价格", "price", "cost", "pricing")),
    ("Agent", ("agent", "智能体", "多 agent", "multi-agent", "autonomous")),
    ("产品商业化", ("商业化", "订阅", "企业版", "盈利", "收入", "商业", "产品", "monetiz", "subscription", "enterprise")),
    ("商业政策", ("政策", "监管", "法案", "版权", "合规", "出口管制", "法律", "regulation", "policy", "lawsuit")),
]


def classify(title: str, content: str = "", source: str = "") -> str:
    """规则主题分类：返回一个主主题标签（来源为 GitHub 时优先判为「开源项目」）。"""
    if source and source.lower().startswith("github"):
        return "开源项目"
    text = f"{title} {content}".lower()
    for label, keywords in _CATEGORY_KEYWORDS:
        if any(kw in text for kw in keywords):
            return label
    return "其他"
