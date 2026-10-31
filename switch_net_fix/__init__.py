"""国行 Switch 联网修复服务。

腾讯停止运营国行 Nintendo Switch 后，主机的联网自检被写死在已注销的
``*.nintendoswitch.cn`` 域名上，导致永远显示"互联网：未连接"。

本包在局域网内伪造该自检所需的响应，使主机认为网络可用。
"""

__version__ = "1.0.1"

__all__ = ["__version__"]
