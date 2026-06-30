#!/bin/bash
# Start mitmproxy in transparent mode with the netgate addon
set -euo pipefail

PROXY_PORT="${PROXY_PORT:-8080}"
CERT_DIR="/var/lib/netgate/certs"

mkdir -p "$CERT_DIR"

exec mitmdump \
    --mode transparent \
    --listen-port "$PROXY_PORT" \
    --set confdir="$CERT_DIR" \
    --set block_global=false \
    --scripts /opt/netgate/proxy/addon_adblock.py \
    --quiet
