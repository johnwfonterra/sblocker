# Netgate - Transparent MITM Gateway with Ad Removal

A self-hosted transparent network gateway that intercepts HTTP/HTTPS traffic,
removes ads and trackers from web content, and re-encrypts before delivery.

## Architecture

```
[Devices] → [eth1: LAN] → [Netgate] → [eth0: WAN] → [Internet]
                              │
                    ┌─────────┼─────────┐
                    │         │         │
                 dnsmasq  mitmproxy  FastAPI
                 (DHCP/DNS) (proxy)   (mgmt UI)
```

## Components

| Component | Path | Purpose |
|-----------|------|---------|
| Gateway | `gateway/` | IP forwarding, iptables, DHCP |
| Proxy | `proxy/` | mitmproxy addons for filtering |
| API | `api/` | FastAPI management backend |
| Frontend | `frontend/` | Vue 3 admin dashboard |
| Lists | `lists/` | Blocklist management |
| Scripts | `scripts/` | Install, update, maintenance |
| Systemd | `systemd/` | Service unit files |

## Requirements

- Debian/Ubuntu x86_64 Linux
- 2 NICs (WAN + LAN)
- Python 3.11+
- Node.js 18+ (build only, not runtime)

## Quick Start

```bash
sudo ./scripts/install.sh
```

## Security Note

This system performs SSL/TLS interception. The CA private key is stored locally
and never leaves the device. You control all filtering logic.
# sblocker
