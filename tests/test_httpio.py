"""HTTP 报文解析。"""

import unittest

from switch_net_fix.httpio import parse_request, wants_keepalive


def head(*lines: str) -> bytes:
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1")


class TestParseProxyForm(unittest.TestCase):
    def test_absolute_uri(self):
        raw = head(
            "GET http://ctest.cdn.n.nintendoswitch.cn/ HTTP/1.1",
            "Host: ctest.cdn.n.nintendoswitch.cn",
        )
        req = parse_request(raw)
        self.assertIsNotNone(req)
        self.assertEqual(req.method, "GET")
        self.assertEqual(req.host, "ctest.cdn.n.nintendoswitch.cn")
        self.assertEqual(req.port, 80)
        self.assertEqual(req.path, "/")
        self.assertFalse(req.is_connect)

    def test_absolute_uri_with_port_and_path(self):
        raw = head("GET http://example.com:8080/a/b?c=1 HTTP/1.1")
        req = parse_request(raw)
        self.assertEqual(req.host, "example.com")
        self.assertEqual(req.port, 8080)
        self.assertEqual(req.path, "/a/b?c=1")

    def test_https_absolute_uri_defaults_to_443(self):
        raw = head("GET https://example.com/ HTTP/1.1")
        req = parse_request(raw)
        self.assertEqual(req.port, 443)


class TestParseOriginForm(unittest.TestCase):
    def test_host_header(self):
        raw = head(
            "GET / HTTP/1.1",
            "Host: ctest.cdn.n.nintendoswitch.cn",
            "User-Agent: Nintendo",
        )
        req = parse_request(raw)
        self.assertEqual(req.host, "ctest.cdn.n.nintendoswitch.cn")
        self.assertEqual(req.port, 80)
        self.assertEqual(req.path, "/")

    def test_missing_host_returns_none(self):
        raw = head("GET / HTTP/1.1", "User-Agent: Nintendo")
        self.assertIsNone(parse_request(raw))


class TestParseConnect(unittest.TestCase):
    def test_connect(self):
        raw = head("CONNECT dauth-lp1.ndas.srv.n.nintendoswitch.cn:443 HTTP/1.1")
        req = parse_request(raw)
        self.assertTrue(req.is_connect)
        self.assertEqual(req.host, "dauth-lp1.ndas.srv.n.nintendoswitch.cn")
        self.assertEqual(req.port, 443)

    def test_connect_without_port_defaults_443(self):
        raw = head("CONNECT example.com HTTP/1.1")
        req = parse_request(raw)
        self.assertEqual(req.port, 443)


class TestParseGarbage(unittest.TestCase):
    def test_empty(self):
        self.assertIsNone(parse_request(b""))

    def test_single_token(self):
        self.assertIsNone(parse_request(b"GARBAGE\r\n\r\n"))

    def test_binary(self):
        self.assertIsNone(parse_request(b"\x00\x01\x02\r\n\r\n"))


class TestKeepAlive(unittest.TestCase):
    def test_close_wins(self):
        raw = head("GET / HTTP/1.1", "Connection: close")
        self.assertFalse(wants_keepalive(raw))

    def test_explicit_keepalive(self):
        raw = head("GET / HTTP/1.1", "Connection: keep-alive")
        self.assertTrue(wants_keepalive(raw))

    def test_http11_get_defaults_keepalive(self):
        raw = head("GET / HTTP/1.1", "Host: a")
        self.assertTrue(wants_keepalive(raw))


if __name__ == "__main__":
    unittest.main()
