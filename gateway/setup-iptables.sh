#!/bin/bash
# Gateway network configuration
# Configures IP forwarding, NAT, and traffic redirection to mitmproxy

set -euo pipefail

WAN_IF="${WAN_IF:-eth0}"
LAN_IF="${LAN_IF:-eth1}"
LAN_NET="${LAN_NET:-192.168.10.0/24}"
PROXY_PORT="${PROXY_PORT:-8080}"
PROXY_PORT_HTTPS="${PROXY_PORT_HTTPS:-8443}"

echo "[netgate] Configuring gateway: WAN=$WAN_IF LAN=$LAN_IF"

# Enable IP forwarding
sysctl -w net.ipv4.ip_forward=1
sysctl -w net.ipv6.conf.all.forwarding=1

# Flush existing rules
iptables -t nat -F
iptables -t mangle -F
iptables -F FORWARD

# NAT outbound traffic from LAN
iptables -t nat -A POSTROUTING -o "$WAN_IF" -j MASQUERADE

# Allow forwarding between interfaces
iptables -A FORWARD -i "$LAN_IF" -o "$WAN_IF" -j ACCEPT
iptables -A FORWARD -i "$WAN_IF" -o "$LAN_IF" -m state --state RELATED,ESTABLISHED -j ACCEPT

# Redirect HTTP/HTTPS to mitmproxy (transparent mode)
iptables -t nat -A PREROUTING -i "$LAN_IF" -p tcp --dport 80 -j REDIRECT --to-port "$PROXY_PORT"
iptables -t nat -A PREROUTING -i "$LAN_IF" -p tcp --dport 443 -j REDIRECT --to-port "$PROXY_PORT_HTTPS"

# Allow traffic to the management UI (port 8888) without proxying
iptables -t nat -I PREROUTING -i "$LAN_IF" -p tcp --dport 8888 -d 192.168.10.1 -j ACCEPT

echo "[netgate] Gateway configured successfully"
