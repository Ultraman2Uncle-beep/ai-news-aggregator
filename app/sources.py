from __future__ import annotations

from app.collectors.base import BaseCollector
from app.collectors.github import GitHubTrendingCollector
from app.collectors.hackernews import HackerNewsCollector
from app.collectors.reddit import RedditCollector
from app.collectors.rss import RSSCollector
from app.config import settings

# ============================================================
# 信息源配置（初稿）
# 注意：以下 RSS 地址为初稿，联调时逐个验证，失效则移除或替换。
# 所有源均为公开匿名端点，无需登录。若后续某源需登录，会先暂停征求反馈。
# ============================================================

# 官网 / 技术博客 RSS（国内网络已验证可直连）
BLOG_FEEDS: dict[str, str] = {
    "OpenAI Blog": "https://openai.com/news/rss.xml",
    "Anthropic News": "https://openrss.org/feed/www.anthropic.com/news",  # 无官方 RSS，用第三方 mirror
    "Google DeepMind": "https://deepmind.google/blog/rss.xml",
    "Hugging Face Blog": "https://hf-mirror.com/blog/feed.xml",  # 国内镜像
    "NVIDIA AI Blog": "https://blogs.nvidia.com/feed/",
}

# 被墙源（国内无法直连，需本地代理 + enable_blocked_sources=true 才启用）
BLOCKED_FEEDS: dict[str, str] = {
    "Meta AI Blog": "https://ai.meta.com/blog/rss/",
    "Microsoft AI Blog": "https://blogs.microsoft.com/ai/feed/",
    "Google AI Blog": "https://blog.google/innovation-and-ai/technology/ai/rss/",
    "xAI Blog": "https://x.ai/blog/rss.xml",
}

# 国内科技媒体 RSS
CN_FEEDS: dict[str, str] = {
    "机器之心": "https://www.jiqizhixin.com/rss",
    "量子位": "https://www.qbitai.com/feed",
    "新智元": "https://www.aiera.com.cn/feed",
}

# Reddit 子版块（被墙，需代理）
REDDIT_SUBREDDITS: list[str] = [
    "MachineLearning",
    "LocalLLaMA",
    "artificial",
    "singularity",
]

# GitHub 活跃发版项目（releases.atom，头部 + 中腰部）
GITHUB_RELEASES: list[str] = [
    "ggml-org/llama.cpp",
    "vllm-project/vllm",
    "huggingface/transformers",
    "huggingface/diffusers",
    "ollama/ollama",
    "Comfy-Org/ComfyUI",
    "langchain-ai/langchain",
    "microsoft/autogen",
    "langgenius/dify",
    "open-webui/open-webui",
    "sgl-project/sglang",
    "xorbitsai/inference",
    "lm-sys/FastChat",
    "QwenLM/Qwen",
    "THUDM/ChatGLM3",
    "01-ai/Yi",
    "internlm/internlm",
    "deepseek-ai/DeepSeek-V3",
    "meta-llama/llama-models",
    "stability-ai/generative-models",
    "NVIDIA/TensorRT-LLM",
    "microsoft/semantic-kernel",
    "run-llama/llama_index",
    "hiyouga/LLaMA-Factory",
    "modelscope/agentscope",
]


def build_collectors() -> list[BaseCollector]:
    """组装所有采集器实例。"""
    collectors: list[BaseCollector] = []

    for name, feed in BLOG_FEEDS.items():
        collectors.append(RSSCollector(name=name, feed_url=feed))

    if settings.enable_blocked_sources:
        for name, feed in BLOCKED_FEEDS.items():
            collectors.append(RSSCollector(name=name, feed_url=feed))

    for name, feed in CN_FEEDS.items():
        collectors.append(RSSCollector(name=name, feed_url=feed))

    if settings.enable_blocked_sources:
        for sub in REDDIT_SUBREDDITS:
            collectors.append(RedditCollector(subreddit=sub))

    collectors.append(HackerNewsCollector())

    for repo in GITHUB_RELEASES:
        collectors.append(
            RSSCollector(
                name=f"github/{repo}",
                feed_url=f"https://github.com/{repo}/releases.atom",
                max_items=10,
                max_age_hours=168,
            )
        )

    collectors.append(GitHubTrendingCollector(since="daily"))

    return collectors
