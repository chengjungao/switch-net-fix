"""最小化的 HTTP 报文解析与隧道转发。

只解析代理场景需要的字段：方法、目标主机、端口、路径。
兼容两种请求形态：

* 代理形态：``GET http://host/path HTTP/1.1``（绝对 URI）
* 直连形态：``GET /path HTTP/1.1`` + ``Host: host``（DNS 重定向后出现）
* 隧道：``CONNECT host:443 HTTP/1.1``
"""

from __future__ import annotations

import socket
import threading
from typing import Optional

__all__ = ["Request", "read_head", "parse_request", "wants_keepalive", "tunnel"]

_HEAD_LIMIT = 65536
_CHUNK = 4096


class Request:
    """一条解析后的请求行信息。"""

    __slots__ = ("method", "host", "port", "path", "raw")

    def __init__(self, method: str, host: str, port: int, path: str, raw: bytes) -> None:
        self.method = method
        self.host = host
        self.port = port
        self.path = path
        self.raw = raw

    @property
    def is_connect(self) -> bool:
        return self.method.upper() == "CONNECT"

    @property
    def target(self) -> str:
        return f"{self.host}:{self.port}"

    def __repr__(self) -> str:  # pragma: no cover - 仅调试用
        return f"<Request {self.method} {self.host}:{self.port}{self.path}>"


def read_head(sock: socket.socket, limit: int = _HEAD_LIMIT) -> bytes:
    """读取到 HTTP 头结束（``\\r\\n\\r\\n``）为止。读不到时返回已读部分。"""
    buf = b""
    while b"\r\n\r\n" not in buf and len(buf) < limit:
        try:
            chunk = sock.recv(_CHUNK)
        except (socket.timeout, OSError):
            return buf
        if not chunk:
            return buf
        buf += chunk
    return buf


def _split_host_port(target: str, default_port: int):
    if ":" in target:
        host, _, port_text = target.rpartition(":")
        try:
            return host, int(port_text)
        except ValueError:
            return target, default_port
    return target, default_port


def parse_request(head: bytes, default_port: int = 80) -> Optional[Request]:
    """解析请求头。无法识别返回 ``None``。"""
    try:
        text = head.split(b"\r\n\r\n", 1)[0].decode("latin-1")
    except (UnicodeDecodeError, AttributeError):
        return None

    lines = text.split("\r\n")
    if not lines or not lines[0].strip():
        return None

    parts = lines[0].split()
    if len(parts) < 2:
        return None

    method = parts[0]
    target = parts[1]

    if method.upper() == "CONNECT":
        host, port = _split_host_port(target, 443)
        return Request(method, host, port, "", head)

    # 绝对 URI 形态
    lowered = target.lower()
    if lowered.startswith("http://") or lowered.startswith("https://"):
        is_tls = lowered.startswith("https://")
        rest = target.split("://", 1)[1]
        authority, _, path = rest.partition("/")
        path = "/" + path if path else "/"
        host, port = _split_host_port(authority, 443 if is_tls else 80)
        return Request(method, host, port, path, head)

    # 直连形态：靠 Host 头
    for line in lines[1:]:
        if line.lower().startswith("host:"):
            host, port = _split_host_port(line.split(":", 1)[1].strip(), default_port)
            return Request(method, host, port, target, head)

    return None


def wants_keepalive(head: bytes) -> bool:
    """根据请求头判断客户端是否希望复用连接。"""
    low = head.lower()
    if b"connection: close" in low:
        return False
    if b"connection: keep-alive" in low:
        return True
    # HTTP/1.1 默认长连接
    return head.startswith(b"GET") or head.startswith(b"POST")


def tunnel(a: socket.socket, b: socket.socket) -> None:
    """双向转发直到任一端关闭。"""
    def pump(src: socket.socket, dst: socket.socket) -> None:
        try:
            while True:
                data = src.recv(65536)
                if not data:
                    break
                dst.sendall(data)
        except OSError:
            pass
        finally:
            for s in (src, dst):
                try:
                    s.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    worker = threading.Thread(target=pump, args=(a, b), daemon=True)
    worker.start()
    pump(b, a)
    worker.join(timeout=1)
