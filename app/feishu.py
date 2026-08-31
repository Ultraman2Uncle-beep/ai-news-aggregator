from __future__ import annotations

import json
import time

import httpx

from app.config import settings

_TENANT_ACCESS_TOKEN_URL = (
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
)
_SEND_MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"

_TOKEN_INVALID_CODE = 99991663
_REFRESH_AHEAD_SECONDS = 60

_token_cache: str = ""
_token_expire_at: float = 0.0


def is_configured() -> bool:
    """三项配置齐全才视为已配置，否则静默禁用推送。"""
    return bool(
        settings.feishu_app_id
        and settings.feishu_app_secret
        and settings.feishu_user_open_id
    )


def _invalidate_token() -> None:
    global _token_cache, _token_expire_at
    _token_cache = ""
    _token_expire_at = 0.0


def _get_tenant_access_token() -> str:
    """获取 tenant_access_token，带模块级缓存（过期后自动刷新）。"""
    global _token_cache, _token_expire_at

    now = time.time()
    if _token_cache and now < _token_expire_at:
        return _token_cache

    resp = httpx.post(
        _TENANT_ACCESS_TOKEN_URL,
        headers={"Content-Type": "application/json; charset=utf-8"},
        json={"app_id": settings.feishu_app_id, "app_secret": settings.feishu_app_secret},
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(
            f"飞书获取 tenant_access_token 失败: code={data.get('code')} msg={data.get('msg')}"
        )

    _token_cache = data["tenant_access_token"]
    expire = int(data.get("expire", 7200))
    _token_expire_at = now + expire - _REFRESH_AHEAD_SECONDS
    return _token_cache


def send_interactive_card(title: str, lines: list[str]) -> None:
    """发送飞书交互式卡片消息。失败仅打印日志，绝不抛出异常。"""
    if not is_configured():
        return

    card = {
        "config": {"wide_screen_mode": True},
        "header": {"template": "blue", "title": {"tag": "plain_text", "content": title}},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": line}} for line in lines
        ],
    }
    body = {
        "receive_id": settings.feishu_user_open_id,
        "msg_type": "interactive",
        "content": json.dumps(card, ensure_ascii=False),
    }

    for attempt in (0, 1):
        try:
            token = _get_tenant_access_token()
            resp = httpx.post(
                _SEND_MESSAGE_URL,
                params={"receive_id_type": "open_id"},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                json=body,
                timeout=10.0,
            )
            if resp.status_code == 401 and attempt == 0:
                _invalidate_token()
                continue
            resp.raise_for_status()
            data = resp.json()
            code = data.get("code")
            if code == 0:
                print("[feishu] 推送成功")
                return
            if code == _TOKEN_INVALID_CODE and attempt == 0:
                _invalidate_token()
                continue
            print(f"[feishu] 发送消息失败: code={code} msg={data.get('msg')}")
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[feishu] 发送消息失败: {exc}")
            return


def push_news_digest(articles: list[dict]) -> bool:
    """推送 AI 资讯日报。未配置时静默返回 False，失败仅打印不抛出。"""
    if not is_configured():
        return False

    try:
        lines: list[str] = []
        for i, article in enumerate(articles, start=1):
            title_text = (article.get("title_zh") or "").strip() or article.get("title", "")
            url = article.get("url", "")
            source = article.get("source", "")
            summary = (article.get("summary_zh") or "").strip()
            line = f"**{i}.** [{title_text}]({url})\n来源: {source}"
            if summary:
                line += f"\n{summary}"
            lines.append(line)

        if not lines:
            return False

        send_interactive_card("AI 资讯日报", lines)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"[feishu] 推送日报失败: {exc}")
        return False
