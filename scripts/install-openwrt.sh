#!/bin/sh
# OpenWrt 安装脚本：把自检修补服务装到路由器上，并用 dnsmasq 把
# ctest.cdn.n.nintendoswitch.cn 指向本机，Switch 端只需保持默认网络设置。
#
# 用法（在仓库根目录执行）：
#     sh scripts/install-openwrt.sh
#
# 可覆盖的环境变量：
#     INSTALL_DIR  安装目录，默认 /opt/switch-net-fix
#     HTTP_PORT    服务端口，默认 80
#     MOVE_UHTTPD  1=把 LuCI 管理页面挪到 UHTTPD_PORT，默认 1
#     UHTTPD_PORT  LuCI 新端口，默认 8080
#
# 卸载：
#     /etc/init.d/switch-net-fix stop
#     /etc/init.d/switch-net-fix disable
#     rm -f /etc/init.d/switch-net-fix
#     rm -rf "$INSTALL_DIR"
#     uci del_list dhcp.@dnsmasq[0].address='/ctest.cdn.n.nintendoswitch.cn/<IP>'
#     uci commit dhcp && /etc/init.d/dnsmasq restart

set -eu

INSTALL_DIR="${INSTALL_DIR:-/opt/switch-net-fix}"
HTTP_PORT="${HTTP_PORT:-80}"
MOVE_UHTTPD="${MOVE_UHTTPD:-1}"
UHTTPD_PORT="${UHTTPD_PORT:-8080}"
CTEST_HOST="ctest.cdn.n.nintendoswitch.cn"

log() { printf '[install] %s\n' "$*"; }
die() { printf '[error] %s\n' "$*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "需要 root 权限"
[ -f "switch_net_fix/__init__.py" ] || die "请在仓库根目录执行本脚本"
command -v python3 >/dev/null 2>&1 || die "未找到 python3，请先执行 opkg install python3-light"

LAN_IP="$(uci get network.lan.ipaddr 2>/dev/null || echo 192.168.1.1)"
log "路由器 LAN 地址: ${LAN_IP}"

# ------------------------------------------------------------------ #
# 1. 拷贝代码
# ------------------------------------------------------------------ #
mkdir -p "$INSTALL_DIR"
rm -rf "$INSTALL_DIR/switch_net_fix"
cp -r switch_net_fix "$INSTALL_DIR/"
find "$INSTALL_DIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
log "代码已安装到 ${INSTALL_DIR}"

# ------------------------------------------------------------------ #
# 2. 写 init 脚本
# ------------------------------------------------------------------ #
cat > /etc/init.d/switch-net-fix <<INITEOF
#!/bin/sh /etc/rc.common

USE_PROCD=1
START=99
STOP=10

start_service() {
	procd_open_instance
	procd_set_param command /usr/bin/python3 -m switch_net_fix --port __PORT__ --quiet
	procd_set_param env PYTHONPATH=__INSTALL_DIR__
	procd_set_param env PYTHONUNBUFFERED=1
	procd_set_param respawn 3600 5 5
	procd_set_param stdout 1
	procd_set_param stderr 1
	procd_close_instance
}
INITEOF

sed -i "s|__PORT__|${HTTP_PORT}|g" /etc/init.d/switch-net-fix
sed -i "s|__INSTALL_DIR__|${INSTALL_DIR}|g" /etc/init.d/switch-net-fix
chmod +x /etc/init.d/switch-net-fix
log "init 脚本已写入 /etc/init.d/switch-net-fix"

# ------------------------------------------------------------------ #
# 3. LuCI 让出 80 端口
# ------------------------------------------------------------------ #
if [ "$HTTP_PORT" = "80" ] && [ "$MOVE_UHTTPD" = "1" ]; then
	if uci get uhttpd.main.listen_http 2>/dev/null | grep -q ':80'; then
		uci set uhttpd.main.listen_http="0.0.0.0:${UHTTPD_PORT}"
		uci set uhttpd.main.listen_https="0.0.0.0:$((UHTTPD_PORT + 443 - 80))"
		uci commit uhttpd
		/etc/init.d/uhttpd restart
		log "LuCI 已挪到 ${UHTTPD_PORT}，管理地址变为 http://${LAN_IP}:${UHTTPD_PORT}"
	fi
fi

# ------------------------------------------------------------------ #
# 4. dnsmasq：把自检域名指到本机
# ------------------------------------------------------------------ #
CURRENT="$(uci get dhcp.@dnsmasq[0].address 2>/dev/null || true)"
if printf '%s' "$CURRENT" | grep -q "$CTEST_HOST"; then
	log "dnsmasq 记录已存在，跳过"
else
	uci add_list "dhcp.@dnsmasq[0].address=/${CTEST_HOST}/${LAN_IP}"
	uci commit dhcp
	/etc/init.d/dnsmasq restart
	log "已添加 DNS 记录 ${CTEST_HOST} -> ${LAN_IP}"
fi

# ------------------------------------------------------------------ #
# 5. 启动并自启
# ------------------------------------------------------------------ #
/etc/init.d/switch-net-fix enable
/etc/init.d/switch-net-fix restart

sleep 1
if nslookup "$CTEST_HOST" 127.0.0.1 2>/dev/null | grep -q "$LAN_IP"; then
	log "DNS 解析验证通过"
else
	log "警告：DNS 解析未返回 ${LAN_IP}，请手工检查 dnsmasq 配置"
fi

if wget -q -T 3 -O - "http://${CTEST_HOST}/" 2>/dev/null | grep -q '^ok$'; then
	log "自检响应验证通过"
else
	log "警告：本机自检响应异常，请查看 logread -e switch_net_fix"
fi

cat <<DONE

完成。Switch 端设置：
  设置 -> 互联网 -> 互联网设置 -> 选中 Wi-Fi -> 更改设置
  -> 代理服务器设置 -> 不使用
  -> DNS 设置 -> 自动

即保持默认即可，无需填任何代理。
管理页面：http://${LAN_IP}:${UHTTPD_PORT}
DONE
