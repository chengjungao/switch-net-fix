"""构造主机期望的连接自检响应。

协议要点见 ``docs/PROTOCOL.md``。核心事实：主机向
``http://ctest.cdn.n.nintendoswitch.cn/`` 发起明文 HTTP 请求，
只有当响应同时满足下列四项时才判定成功，缺任何一项都会被拒绝并每 3 秒重试：

1. 状态码 200
2. 响应体恰好是 ``ok``（2 字节）
3. ``Content-Type: text/plain``
4. ``X-Organization: Nintendo``
"""

from __future__ import annotations

from typing import Sequence

# 腾讯国服专属域名（2026-05-15 后整段注销）
CN_SUFFIXES: Sequence[str] = ("nintendoswitch.cn", "nintendoswitch.com.cn")

# 连接自检的期望响应体
CTEST_BODY: bytes = b"ok"

# 连接自检主机名前缀
CTEST_PREFIX: str = "ctest."

_RESPONSE_TEMPLATE = (
    b"HTTP/1.1 200 OK\r\n"
    b"Content-Type: text/plain\r\n"
    b"X-Organization: Nintendo\r\n"
    b"Content-Length: {length}\r\n"
    b"Connection: keep-alive\r\n"
    b"\r\n"
)


def build_response(body: bytes = CTEST_BODY) -> bytes:
    """生成完整的自检响应字节串。"""
    length = str(len(body)).encode("ascii")
    return _RESPONSE_TEMPLATE.replace(b"{length}", length) + body


# 预构建，处理请求时直接复用
OK_RESPONSE: bytes = build_response()


def is_cn_host(host: str) -> bool:
    """是否为已停止运营的腾讯国服域名。"""
    h = (host or "").strip().lower().rstrip(".")
    if not h:
        return False
    return any(h == suffix or h.endswith("." + suffix) for suffix in CN_SUFFIXES)


def is_ctest_host(host: str) -> bool:
    """是否为连接自检域名。"""
    return is_cn_host(host) and (host or "").lower().startswith(CTEST_PREFIX)


def should_fake(host: str, only_ctest: bool = False) -> bool:
    """该请求是否应被本地伪造响应拦截。

    Args:
        host: 请求的目标主机名。
        only_ctest: 为真时只拦截连接自检，其余国服域名照常转发。
    """
    if only_ctest:
        return is_ctest_host(host)
    return is_cn_host(host)
