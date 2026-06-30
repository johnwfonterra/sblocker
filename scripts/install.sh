#!/bin/bash
#
# Netgate Installer
# Installs all components on a Debian/Ubuntu x86_64 system
#
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="/opt/netgate"
CONFIG_DIR="/etc/netgate"
DATA_DIR="/var/lib/netgate"
LOG_DIR="/var/log/netgate"

info()  { echo -e "${GREEN}[netgate]${NC} $*"; }
warn()  { echo -e "${YELLOW}[netgate]${NC} $*"; }
error() { echo -e "${RED}[netgate]${NC} $*" >&2; }

# Must be root
if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
    exit 1
fi

echo ""
echo "============================================"
echo "  Netgate - Transparent MITM Gateway"
echo "  Ad removal + tracking protection"
echo "============================================"
echo ""

# Detect network interfaces
info "Detecting network interfaces..."
INTERFACES=$(ip -o link show | awk -F': ' '{print $2}' | grep -v lo)
echo "  Available: $INTERFACES"
echo ""

read -p "  WAN interface (connects to router) [eth0]: " WAN_IF
WAN_IF=${WAN_IF:-eth0}

read -p "  LAN interface (connects to devices) [eth1]: " LAN_IF
LAN_IF=${LAN_IF:-eth1}

read -p "  LAN subnet [192.168.10.0/24]: " LAN_NET
LAN_NET=${LAN_NET:-192.168.10.0/24}

LAN_IP=$(echo "$LAN_NET" | sed 's|0/.*|1|')

echo ""
info "Configuration:"
info "  WAN: $WAN_IF | LAN: $LAN_IF ($LAN_IP)"
echo ""
read -p "Continue? [Y/n] " -n 1 -r
echo
[[ $REPLY =~ ^[Nn]$ ]] && exit 0

# --- Install dependencies ---
info "Installing system dependencies..."
apt-get update -qq
apt-get install -y -qq \
    python3 python3-venv python3-pip \
    dnsmasq \
    iptables \
    curl \
    ca-certificates \
    nodejs npm 2>/dev/null || true

# --- Create directories ---
info "Creating directories..."
mkdir -p "$INSTALL_DIR" "$CONFIG_DIR" "$DATA_DIR/certs" "$LOG_DIR"

# --- Copy files ---
info "Installing Netgate files..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cp -r "$PROJECT_DIR/gateway" "$INSTALL_DIR/"
cp -r "$PROJECT_DIR/proxy" "$INSTALL_DIR/"
cp -r "$PROJECT_DIR/api" "$INSTALL_DIR/"
cp -r "$PROJECT_DIR/lists" "$INSTALL_DIR/"
cp "$PROJECT_DIR/requirements.txt" "$INSTALL_DIR/"

# --- Set environment variables in scripts ---
sed -i "s|WAN_IF=.*|WAN_IF=\"${WAN_IF}\"|" "$INSTALL_DIR/gateway/setup-iptables.sh"
sed -i "s|LAN_IF=.*|LAN_IF=\"${LAN_IF}\"|" "$INSTALL_DIR/gateway/setup-iptables.sh"
sed -i "s|LAN_NET=.*|LAN_NET=\"${LAN_NET}\"|" "$INSTALL_DIR/gateway/setup-iptables.sh"

chmod +x "$INSTALL_DIR/gateway/setup-iptables.sh"
chmod +x "$INSTALL_DIR/proxy/start.sh"

# --- Python venv ---
info "Creating Python virtual environment..."
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
"$INSTALL_DIR/venv/bin/pip" install --quiet -r "$INSTALL_DIR/requirements.txt"

# --- Build frontend ---
info "Building frontend..."
if command -v npm &>/dev/null; then
    cd "$PROJECT_DIR/frontend"
    npm install --silent
    npm run build
    cp -r dist "$INSTALL_DIR/frontend/"
    cd -
else
    warn "npm not found - skipping frontend build"
    warn "Install Node.js and run: cd frontend && npm install && npm run build"
fi

# --- Configure dnsmasq ---
info "Configuring dnsmasq..."
cat > /etc/dnsmasq.d/netgate.conf <<EOF
interface=${LAN_IF}
bind-interfaces
dhcp-range=${LAN_NET%.*}.50,${LAN_NET%.*}.200,24h
dhcp-option=3,${LAN_IP}
dhcp-option=6,${LAN_IP}
server=1.1.1.1
server=9.9.9.9
addn-hosts=/etc/netgate/blocked-hosts
log-queries
log-facility=/var/log/netgate/dns.log
EOF

# --- Configure LAN interface ---
info "Configuring LAN interface ($LAN_IF)..."
cat > /etc/network/interfaces.d/netgate <<EOF
auto ${LAN_IF}
iface ${LAN_IF} inet static
    address ${LAN_IP}
    netmask 255.255.255.0
EOF

# --- IP forwarding (persistent) ---
echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-netgate.conf
sysctl -p /etc/sysctl.d/99-netgate.conf

# --- Install systemd services ---
info "Installing systemd services..."
cp "$PROJECT_DIR/systemd/"*.service /etc/systemd/system/
cp "$PROJECT_DIR/systemd/"*.timer /etc/systemd/system/
systemctl daemon-reload

# --- Download initial blocklists ---
info "Downloading initial blocklists..."
touch "$CONFIG_DIR/blocklist-domains.txt"
touch "$CONFIG_DIR/whitelist-domains.txt"
touch "$CONFIG_DIR/blocked-hosts"
"$INSTALL_DIR/venv/bin/python" "$INSTALL_DIR/lists/update_lists.py" || warn "Blocklist download failed (will retry later)"

# --- Enable and start services ---
info "Starting services..."
systemctl enable --now netgate-gateway
systemctl enable --now netgate-proxy
systemctl enable --now netgate-api
systemctl enable --now netgate-lists-update.timer
systemctl restart dnsmasq

# --- Generate CA cert (first run of mitmproxy creates it) ---
sleep 3
if [[ -f "$DATA_DIR/certs/mitmproxy-ca-cert.pem" ]]; then
    info "CA certificate generated at: $DATA_DIR/certs/mitmproxy-ca-cert.pem"
else
    warn "CA cert not yet generated - it will be created on first proxy connection"
fi

echo ""
echo "============================================"
echo -e "  ${GREEN}Netgate installed successfully!${NC}"
echo "============================================"
echo ""
echo "  Dashboard:   http://${LAN_IP}:8888"
echo "  CA Cert:     http://${LAN_IP}:8888/api/system/cert"
echo ""
echo "  Next steps:"
echo "  1. Connect LAN devices to the $LAN_IF interface"
echo "  2. Download and install the CA cert on each device"
echo "  3. Access the dashboard to verify blocking"
echo ""
echo "  Logs:"
echo "    journalctl -u netgate-proxy -f"
echo "    journalctl -u netgate-api -f"
echo ""
