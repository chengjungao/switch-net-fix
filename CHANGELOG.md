# Changelog

本项目的所有重要变更都记录在此文件。
格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [未发布]

### 修复

- CI 中 `ubuntu-latest / py3.8` 组合失败：`ubuntu-latest` 已迁移到 24.04，
  系统库不再提供 Python 3.8，`actions/setup-python` 在装解释器阶段就报错退出，
  尚未执行到本项目代码。改为把 3.8 放到仍提供该版本的 `ubuntu-22.04` 上运行，
  保留 3.8 的覆盖（`requires-python` 仍为 `>=3.8`，Windows 侧 3.8 一直是通过的）。
- CI 增加「入口检查」步骤（`python -m switch_net_fix --version`），
  用于捕获打包与 `__main__` 入口的回归。

### 文档

- `docs/PROTOCOL.md` 新增 **§9「官方口径与常见误传的核对」**：
  - 9.1 腾讯 2026-04-30 公告逐条原文引用（19.0.2 为终点、5/15 后无法更新系统、
    microSD 专属更新独立关闭、禁止初始化、存档转移停用），以及 10-30 维修公告要点
  - 9.2 完整版本谱系 19.0.1 → 23.0.1，标注 20.0 这道门槛的实际后果
  - 9.3 「博主把国行机升到 23」的出处与判据：实为破解 + 改区域标志 + 离线刷固件，
    附「一眼分辨真假教程」的五个特征
  - 9.4 一条未经证实的漏洞说法单独隔离并显式标为不可引用
  - 9.5 四条路径的代价对比
- `docs/PROTOCOL.md` 头部增加**来源等级说明**（实测 / 官方 / 第三方 / 未经证实），
  避免第三方说法与实测结论混写
- §1 时间线补充 2026-04-30（注意事项公告）与 2026-10-30（停止维修公告）两个节点

## [1.0.1] - 2026-10-31

### 修复

- `scripts/*.bat` 在中文 Windows 下无法执行：文件为 UTF-8 且以 LF 结尾，
  开头又执行了 `chcp 65001`，导致 cmd 解析器读指针错位，`rem` / `set` 前缀被吞，
  中文残片被当成命令执行（`'鎵句竴涓彲鐢ㄧ殑' 不是内部或外部命令`）。
  两个脚本已改为**纯 ASCII + CRLF + 不含 `chcp`**，中文提示交由 Python 输出。
- `install_autostart.bat` 的快捷方式 `WorkingDirectory` 改为 `%%~fI` 解析后的
  绝对路径，避免写入含 `..` 的相对路径。

## [1.0.0] - 2026-10-27

### 新增

- 连接自检响应的伪造：`200` + `ok` + `Content-Type: text/plain` + `X-Organization: Nintendo`
- HTTP 代理形态与直连形态（DNS 重定向）双兼容的请求解析
- 已注销国服域名（`*.nintendoswitch.cn`）的识别与拦截，HTTPS 请求明确标记为不可伪造
- 其他目标域名的透明转发与日志记录
- 命令行参数：`--port`、`--bind`、`--only-ctest`、`--quiet`、`--log-dir`、`--no-log`
- Windows 一键启动与开机自启脚本
- systemd unit 与 OpenWrt 一键安装脚本
- 协议分析文档 `docs/PROTOCOL.md`
- 38 个单元与集成测试

### 说明

- 仅能恢复联网自检，无法恢复 eShop、游戏更新、在线联机与云存档；
  认证环节使用腾讯签发的证书，服务端已不存在，原理上不可伪造。

[1.0.0]: https://github.com/chengjungao/switch-net-fix/releases/tag/v1.0.0
