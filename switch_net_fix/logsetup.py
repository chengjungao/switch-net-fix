"""控制台与文件双写日志。"""

from __future__ import annotations

import os
import threading
from datetime import datetime
from typing import Optional

__all__ = ["Logger"]


class Logger:
    """同时输出到控制台和按天滚动的日志文件。

    Args:
        log_path: 日志文件路径，``None`` 表示只打控制台。
        quiet: 为真时单个请求不打印到控制台，仍写文件。
    """

    def __init__(self, log_path: Optional[str] = None, quiet: bool = False) -> None:
        self.log_path = log_path
        self.quiet = quiet
        self._print_lock = threading.Lock()
        self._file_lock = threading.Lock()

    @staticmethod
    def _stamp() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def info(self, message: str, quiet_ok: bool = False) -> None:
        """写一条日志。

        Args:
            message: 内容。
            quiet_ok: 为真时在 quiet 模式下跳过控制台输出（仍然写文件）。
        """
        with self._print_lock:
            if not (self.quiet and quiet_ok):
                print(message, flush=True)
            self._write_file(message)

    def raw(self, message: str) -> None:
        """强制输出到控制台（用于横幅等用户必须看到的内容）。"""
        with self._print_lock:
            print(message, flush=True)
            self._write_file(message)

    def _write_file(self, message: str) -> None:
        if not self.log_path:
            return
        with self._file_lock:
            try:
                parent = os.path.dirname(self.log_path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
                with open(self.log_path, "a", encoding="utf-8") as handle:
                    handle.write(f"[{self._stamp()}] {message}\n")
            except OSError:
                # 日志失败不影响主流程
                pass
