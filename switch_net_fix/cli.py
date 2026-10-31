"""命令行入口。"""

from __future__ import annotations

import argparse
import os
import socket
import sys
from datetime import datetime
from typing import List, Optional

from . import __version__
from .logsetup import Logger
from .server import Server

__all__ = ["main", "detect_lan_ip", "port_available", "build_parser"]

DEFAULT_PORT = 8080
LOG_DIRNAME = "logs"


def detect_lan_ip() -> str:
    """取本机在局域网中的 IPv4 地址。

    用 UDP ``connect`` 探测（不会真正发包），失败时退化为回环地址。
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("223.5.5.5", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def port_available(port: int, bind_host: str = "0.0.0.0") -> bool:
    """端口是否可绑定。"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((bind_host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="switch-net-fix",
        description="让已停止运营的国行 Nintendo Switch 通过联网自检",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"监听端口，默认 {DEFAULT_PORT}")
    parser.add_argument("--bind", default="0.0.0.0",
                        help="监听地址，默认 0.0.0.0")
    parser.add_argument("--only-ctest", action="store_true",
                        help="只伪造连接自检，其他国服域名照常转发")
    parser.add_argument("--quiet", action="store_true",
                        help="不打印单个请求，仍写日志")
    parser.add_argument("--log-dir", default=LOG_DIRNAME,
                        help=f"日志目录，默认 {LOG_DIRNAME}")
    parser.add_argument("--no-log", action="store_true",
                        help="不写日志文件")
    parser.add_argument("--version", action="version",
                        version=f"switch-net-fix {__version__}")
    return parser


def _banner(ip: str, port: int, log_path: Optional[str]) -> None:
    line = "=" * 62
    print()
    print(line)
    print("  Switch Net Fix  已启动")
    print(line)
    print(f"  监听地址 : 0.0.0.0:{port}")
    print(f"  日志文件 : {log_path or '（未启用）'}")
    print()
    print("  【Switch 端设置（只需一次）】")
    print("    设置 -> 互联网 -> 互联网设置 -> 选中你的 Wi-Fi -> 更改设置")
    print("    -> 代理服务器设置 -> 使用")
    print(f"    -> 服务器 {ip}    端口 {port}")
    print()
    print("  设置完成后回主界面，进 设置 -> 互联网 -> 连接测试")
    print("  三格应全部通过。")
    print()
    print("  按 Ctrl+C 停止服务")
    print(line)
    print(flush=True)


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    log_path = None
    if not args.no_log:
        base = os.path.abspath(args.log_dir)
        log_path = os.path.join(base, f"switch-net-fix-{datetime.now():%Y%m%d}.log")

    if not port_available(args.port, args.bind):
        print(f"\n[错误] 端口 {args.port} 已被占用。")
        print(f"       换个端口：  switch-net-fix --port 8081")
        print(f"       然后 Switch 上的代理端口也要改成同一个。\n", flush=True)
        return 1

    logger = Logger(log_path=log_path, quiet=args.quiet)
    server = Server(port=args.port, bind_host=args.bind,
                    logger=logger, only_ctest=args.only_ctest)

    ip = detect_lan_ip()
    _banner(ip, args.port, log_path)
    logger.info(f"启动 ip={ip} port={args.port}", quiet_ok=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        snap = server.stats.snapshot()
        logger.info(
            f"服务已停止。请求 {snap['total']} 次，"
            f"伪造 {snap['faked']} 次，阻断 {snap['blocked']} 次。",
            quiet_ok=True,
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
