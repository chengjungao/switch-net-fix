"""端到端：真实 socket 打一遍服务。"""

import socket
import threading
import unittest

from switch_net_fix.server import Server

CTEST = "ctest.cdn.n.nintendoswitch.cn"
DAUTH = "dauth-lp1.ndas.srv.n.nintendoswitch.cn"


class ServerHarness:
    """在 127.0.0.1 的随机端口上起一个服务。"""

    def __init__(self, **kwargs):
        self.server = Server(port=0, bind_host="127.0.0.1", **kwargs)

    def __enter__(self):
        self.server.bind()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.stop()
        self.thread.join(timeout=2)

    def request(self, payload: bytes, timeout: float = 5.0) -> bytes:
        with socket.create_connection(("127.0.0.1", self.server.port), timeout=timeout) as sock:
            sock.sendall(payload)
            chunks = []
            while True:
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    break
                if not data:
                    break
                chunks.append(data)
            return b"".join(chunks)


class TestCtestInterception(unittest.TestCase):
    def test_proxy_form_returns_ok(self):
        payload = (
            f"GET http://{CTEST}/ HTTP/1.1\r\n"
            f"Host: {CTEST}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("latin-1")
        with ServerHarness() as harness:
            response = harness.request(payload)
        self.assertIn(b"HTTP/1.1 200 OK", response)
        self.assertIn(b"X-Organization: Nintendo", response)
        self.assertIn(b"Content-Type: text/plain", response)
        self.assertTrue(response.endswith(b"ok"))

    def test_origin_form_also_works(self):
        # DNS 重定向后主机会发这种形态
        payload = (
            f"GET / HTTP/1.1\r\nHost: {CTEST}\r\nConnection: close\r\n\r\n"
        ).encode("latin-1")
        with ServerHarness() as harness:
            response = harness.request(payload)
        self.assertTrue(response.endswith(b"ok"))

    def test_stats_counted(self):
        payload = (
            f"GET http://{CTEST}/ HTTP/1.1\r\n"
            f"Host: {CTEST}\r\nConnection: close\r\n\r\n"
        ).encode("latin-1")
        with ServerHarness() as harness:
            harness.request(payload)
            snap = harness.server.stats.snapshot()
        self.assertEqual(snap["faked"], 1)
        self.assertEqual(snap["total"], 1)


class TestCnHttpsBlocked(unittest.TestCase):
    def test_dauth_connect_is_refused(self):
        payload = (
            f"CONNECT {DAUTH}:443 HTTP/1.1\r\nHost: {DAUTH}:443\r\n\r\n"
        ).encode("latin-1")
        with ServerHarness() as harness:
            response = harness.request(payload)
            snap = harness.server.stats.snapshot()
        self.assertIn(b"502", response)
        self.assertEqual(snap["blocked"], 1)


class TestOnlyCtestMode(unittest.TestCase):
    def test_dauth_not_intercepted_in_only_ctest(self):
        payload = (
            f"GET http://{DAUTH}/ HTTP/1.1\r\n"
            f"Host: {DAUTH}\r\nConnection: close\r\n\r\n"
        ).encode("latin-1")
        with ServerHarness(only_ctest=True) as harness:
            response = harness.request(payload)
            snap = harness.server.stats.snapshot()
        # 域名已注销，上游必然解析失败 -> 502，且不算作伪造
        self.assertIn(b"502", response)
        self.assertEqual(snap["faked"], 0)


class TestForeignHostRelay(unittest.TestCase):
    def test_unresolvable_host_returns_502(self):
        payload = (
            b"GET / HTTP/1.1\r\n"
            b"Host: no-such-host.invalid\r\nConnection: close\r\n\r\n"
        )
        with ServerHarness() as harness:
            response = harness.request(payload)
        self.assertIn(b"502", response)


class TestMalformedInput(unittest.TestCase):
    def test_garbage_does_not_crash_server(self):
        with ServerHarness() as harness:
            harness.request(b"BOGUS\r\n\r\n")
            # 服务仍可正常应答后续请求
            payload = (
                f"GET http://{CTEST}/ HTTP/1.1\r\n"
                f"Host: {CTEST}\r\nConnection: close\r\n\r\n"
            ).encode("latin-1")
            response = harness.request(payload)
        self.assertTrue(response.endswith(b"ok"))


if __name__ == "__main__":
    unittest.main()
