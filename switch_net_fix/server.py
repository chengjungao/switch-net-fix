"""并发服务主体。

一个端口上同时承担三种角色：

* 伪造响应器——命中已注销的国服域名时直接回 200
* 透明转发器——其他请求原样转给上游，便于观察主机行为
* 记录器——把主机请求的目标域名写进日志
"""

from __future__ import annotations

import socket
import threading
from typing import Optional

from .httpio import parse_request, read_head, tunnel, wants_keepalive
from .responder import OK_RESPONSE, should_fake

__all__ = ["Stats", "Server", "MAX_REQUESTS_PER_CONN"]

MAX_REQUESTS_PER_CONN = 32
_ACCEPT_TIMEOUT = 0.5
_CONN_TIMEOUT = 30
_UPSTREAM_TIMEOUT = 10


class Stats:
    """请求计数，线程安全。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.total = 0
        self.faked = 0
        self.blocked = 0

    def bump(self, field: str) -> None:
        with self._lock:
            setattr(self, field, getattr(self, field) + 1)

    def snapshot(self) -> dict:
        with self._lock:
            return {"total": self.total, "faked": self.faked, "blocked": self.blocked}


class Server:
    """局域网内的修补服务。"""

    def __init__(
        self,
        port: int = 8080,
        bind_host: str = "0.0.0.0",
        logger=None,
        only_ctest: bool = False,
    ) -> None:
        self.port = port
        self.bind_host = bind_host
        self.logger = logger
        self.only_ctest = only_ctest
        self.stats = Stats()
        self._sock: Optional[socket.socket] = None
        self._stop = threading.Event()

    # ------------------------------------------------------------------ #
    # 生命周期
    # ------------------------------------------------------------------ #
    def bind(self) -> None:
        """绑定端口，失败时抛出 ``OSError``。"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.bind_host, self.port))
        sock.listen(64)
        sock.settimeout(_ACCEPT_TIMEOUT)
        self._sock = sock
        self.port = sock.getsockname()[1]

    def serve_forever(self) -> None:
        if self._sock is None:
            self.bind()
        assert self._sock is not None
        while not self._stop.is_set():
            try:
                client, addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(
                target=self._handle, args=(client, addr), daemon=True
            ).start()

    def stop(self) -> None:
        self._stop.set()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    # ------------------------------------------------------------------ #
    # 请求处理
    # ------------------------------------------------------------------ #
    def _say(self, message: str, quiet_ok: bool = True) -> None:
        if self.logger is not None:
            self.logger.info(message, quiet_ok=quiet_ok)

    def _handle(self, client: socket.socket, addr) -> None:
        client.settimeout(_CONN_TIMEOUT)
        peer = addr[0]
        try:
            for _ in range(MAX_REQUESTS_PER_CONN):
                head = read_head(client)
                if not head:
                    break

                req = parse_request(head, default_port=80)
                if req is None:
                    self._say(f"  {peer:<15} ??  无法解析的请求")
                    break

                self.stats.bump("total")
                tag = "CONNECT" if req.is_connect else (req.method or "HTTP")

                # 国服域名 + 明文 HTTP -> 伪造成功响应
                if not req.is_connect and should_fake(req.host, self.only_ctest):
                    try:
                        client.sendall(OK_RESPONSE)
                    except OSError:
                        break
                    self.stats.bump("faked")
                    self._say(f"  {peer:<15} {tag:<7} {req.host}{req.path}   [伪造成功]")
                    if not wants_keepalive(head):
                        break
                    continue

                # 国服域名 + HTTPS -> 证书与服务端均已消失，无法伪造
                if req.is_connect and should_fake(req.host, self.only_ctest):
                    self.stats.bump("blocked")
                    self._say(f"  {peer:<15} {tag:<7} {req.target}   [国服 HTTPS，无法伪造]")
                    try:
                        client.sendall(
                            b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n"
                        )
                    except OSError:
                        pass
                    break

                # 其他目标：透明转发并记录
                self._say(f"  {peer:<15} {tag:<7} {req.target}{req.path}")
                if not self._relay(client, head, req):
                    break
                return
        except Exception as exc:  # 单连接异常不应拖垮服务
            self._say(f"  {peer:<15} !! 异常: {exc}")
        finally:
            try:
                client.close()
            except OSError:
                pass

    def _relay(self, client: socket.socket, head: bytes, req) -> bool:
        try:
            upstream = socket.create_connection(
                (req.host, req.port), timeout=_UPSTREAM_TIMEOUT
            )
        except OSError as exc:
            self._say(f"  {'':15} {'':7} 转发失败 -> {exc}")
            try:
                client.sendall(
                    b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n"
                    b"Connection: close\r\n\r\n"
                )
            except OSError:
                pass
            return False

        if req.is_connect:
            try:
                client.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            except OSError:
                return False
            tunnel(client, upstream)
            return True

        try:
            upstream.sendall(head)
        except OSError:
            return False
        tunnel(client, upstream)
        return True
