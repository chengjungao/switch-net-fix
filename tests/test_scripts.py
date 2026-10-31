"""脚本文件的编码与换行约定。

cmd.exe 按当前控制台代码页逐行解析 .bat，且按字节偏移推进读指针。UTF-8
中文或中途的 ``chcp`` 都会让解析错位，把中文残片当成命令执行。这个测试把
约定固化下来，防止有人把中文提示重新写回 .bat。
"""

import pathlib
import unittest

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"


class BatEncodingTest(unittest.TestCase):
    def setUp(self):
        self.bats = sorted(SCRIPTS.glob("*.bat"))
        self.assertTrue(self.bats, "scripts/ 下没有找到 .bat 文件")

    def test_ascii_only(self):
        for path in self.bats:
            with self.subTest(name=path.name):
                raw = path.read_bytes()
                offenders = [(i, b) for i, b in enumerate(raw) if b > 0x7F]
                self.assertEqual(
                    offenders, [],
                    f"{path.name} 含非 ASCII 字节，中文 Windows 下 cmd 会解析错位",
                )

    def test_crlf_only(self):
        for path in self.bats:
            with self.subTest(name=path.name):
                raw = path.read_bytes()
                self.assertGreater(raw.count(b"\r\n"), 0, f"{path.name} 不是 CRLF 换行")
                bare_lf = raw.count(b"\n") - raw.count(b"\r\n")
                self.assertEqual(bare_lf, 0, f"{path.name} 存在 {bare_lf} 处裸 LF")

    def test_no_chcp(self):
        # 注释里允许提到 chcp（用于解释为什么不能这样做），只看真实执行的命令
        for path in self.bats:
            with self.subTest(name=path.name):
                text = path.read_bytes().decode("ascii")
                commands = [
                    ln.strip() for ln in text.splitlines()
                    if ln.strip() and not ln.strip().lower().startswith("rem")
                ]
                hit = [ln for ln in commands if "chcp" in ln.lower()]
                self.assertEqual(
                    hit, [],
                    f"{path.name} 不应调用 chcp，中途切换代码页会让 cmd 读指针错位",
                )


if __name__ == "__main__":
    unittest.main()
