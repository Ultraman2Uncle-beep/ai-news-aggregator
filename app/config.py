import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，从环境变量 / .env 读取。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 阿里百炼 DashScope
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "deepseek-v4-pro"

    # GitHub（可选 token）
    github_token: str = ""

    # 被墙源开关 + 代理（国内访问 Reddit/Meta/Microsoft 等需本地代理）
    enable_blocked_sources: bool = False
    http_proxy: str = ""
    https_proxy: str = ""

    # 每日更新时刻
    update_hour: int = 8
    update_minute: int = 0

    # 数据库
    database_url: str = "sqlite:///data/news.db"

    # 飞书自建应用推送（留空则不推送）
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_user_open_id: str = ""


settings = Settings()

if settings.http_proxy:
    os.environ["HTTP_PROXY"] = settings.http_proxy
    os.environ["HTTPS_PROXY"] = settings.https_proxy or settings.http_proxy
