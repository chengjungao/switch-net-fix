"""自检响应的构造与域名判定。"""

import unittest

from switch_net_fix.responder import (
    OK_RESPONSE,
    build_response,
    is_cn_host,
    is_ctest_host,
    should_fake,
)


class TestBuildResponse(unittest.TestCase):
    def test_status_line(self):
        self.assertTrue(OK_RESPONSE.startswith(b"HTTP/1.1 200 OK\r\n"))

    def test_body_is_exactly_ok(self):
        head, _, body = OK_RESPONSE.partition(b"\r\n\r\n")
        self.assertEqual(body, b"ok")

    def test_content_length_matches_body(self):
        self.assertIn(b"Content-Length: 2\r\n", OK_RESPONSE)

    def test_required_headers(self):
        # 缺任一头主机都会拒绝并每 3 秒重试
        self.assertIn(b"Content-Type: text/plain\r\n", OK_RESPONSE)
        self.assertIn(b"X-Organization: Nintendo\r\n", OK_RESPONSE)

    def test_content_type_has_no_charset_suffix(self):
        # 带 charset 的写法实测会被拒绝
        self.assertNotIn(b"charset", OK_RESPONSE.lower())

    def test_custom_body_recomputes_length(self):
        resp = build_response(b"hello")
        self.assertIn(b"Content-Length: 5\r\n", resp)
        self.assertTrue(resp.endswith(b"hello"))


class TestHostMatching(unittest.TestCase):
    def test_ctest_host(self):
        self.assertTrue(is_cn_host("ctest.cdn.n.nintendoswitch.cn"))
        self.assertTrue(is_ctest_host("ctest.cdn.n.nintendoswitch.cn"))

    def test_dauth_host_is_cn_but_not_ctest(self):
        host = "dauth-lp1.ndas.srv.n.nintendoswitch.cn"
        self.assertTrue(is_cn_host(host))
        self.assertFalse(is_ctest_host(host))

    def test_case_and_trailing_dot_insensitive(self):
        self.assertTrue(is_cn_host("CTEST.CDN.N.NINTENDOSWITCH.CN."))

    def test_bare_domain(self):
        self.assertTrue(is_cn_host("nintendoswitch.cn"))

    def test_foreign_hosts_rejected(self):
        for host in (
            "atum.hac.lp1.d4c.nintendo.net",
            "example.com",
            "notnintendoswitch.cn",
            "",
            None,
        ):
            with self.subTest(host=host):
                self.assertFalse(is_cn_host(host))

    def test_suffix_must_be_label_aligned(self):
        # evilnintendoswitch.cn 不应命中
        self.assertFalse(is_cn_host("evilnintendoswitch.cn"))


class TestShouldFake(unittest.TestCase):
    def test_default_covers_whole_zone(self):
        self.assertTrue(should_fake("ctest.cdn.n.nintendoswitch.cn"))
        self.assertTrue(should_fake("dauth-lp1.ndas.srv.n.nintendoswitch.cn"))

    def test_only_ctest_narrows_scope(self):
        self.assertTrue(should_fake("ctest.cdn.n.nintendoswitch.cn", only_ctest=True))
        self.assertFalse(
            should_fake("dauth-lp1.ndas.srv.n.nintendoswitch.cn", only_ctest=True)
        )

    def test_foreign_host_never_faked(self):
        self.assertFalse(should_fake("atum.hac.lp1.d4c.nintendo.net"))
        self.assertFalse(should_fake("atum.hac.lp1.d4c.nintendo.net", only_ctest=True))


if __name__ == "__main__":
    unittest.main()
