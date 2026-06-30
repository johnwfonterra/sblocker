"""
Netgate Management API

Provides REST endpoints for the frontend dashboard:
- Device list and per-device stats
- Blocklist management (add/remove domains)
- Whitelist management
- Live stats (requests blocked, bytes saved)
- System status
- CA certificate download
"""

import time
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

app = FastAPI(title="Netgate", version="1.0.0")

DB_PATH = "/var/lib/netgate/stats.db"
BLOCKLIST_PATH = "/etc/netgate/blocklist-domains.txt"
WHITELIST_PATH = "/etc/netgate/whitelist-domains.txt"
CERT_PATH = "/var/lib/netgate/certs/mitmproxy-ca-cert.pem"
CONFIG_DIR = Path("/etc/netgate")


# --- Database helpers ---

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# --- Models ---

class DomainEntry(BaseModel):
    domain: str


class DeviceAlias(BaseModel):
    ip: str
    name: str


# --- Stats endpoints ---

@app.get("/api/stats/summary")
def get_stats_summary():
    """Get overall stats for the dashboard."""
    with get_db() as conn:
        now = time.time()
        last_24h = now - 86400

        row = conn.execute("""
            SELECT
                COUNT(*) as total_requests,
                SUM(blocked) as blocked_requests,
                SUM(filtered) as filtered_requests,
                SUM(bytes_saved) as total_bytes_saved
            FROM request_log
            WHERE timestamp > ?
        """, (last_24h,)).fetchone()

        return {
            "total_requests": row["total_requests"] or 0,
            "blocked_requests": row["blocked_requests"] or 0,
            "filtered_requests": row["filtered_requests"] or 0,
            "bytes_saved": row["total_bytes_saved"] or 0,
            "block_percentage": round(
                (row["blocked_requests"] or 0) / max(row["total_requests"] or 1, 1) * 100, 1
            ),
        }


@app.get("/api/stats/timeline")
def get_stats_timeline(hours: int = 24):
    """Get hourly request counts for chart."""
    with get_db() as conn:
        now = time.time()
        start = now - (hours * 3600)

        rows = conn.execute("""
            SELECT
                CAST((timestamp - ?) / 3600 AS INTEGER) as hour_bucket,
                COUNT(*) as total,
                SUM(blocked) as blocked,
                SUM(filtered) as filtered
            FROM request_log
            WHERE timestamp > ?
            GROUP BY hour_bucket
            ORDER BY hour_bucket
        """, (start, start)).fetchall()

        return [
            {
                "hour": r["hour_bucket"],
                "total": r["total"],
                "blocked": r["blocked"],
                "filtered": r["filtered"],
            }
            for r in rows
        ]


@app.get("/api/stats/top-blocked")
def get_top_blocked(limit: int = 20):
    """Get most frequently blocked domains."""
    with get_db() as conn:
        now = time.time()
        last_24h = now - 86400

        rows = conn.execute("""
            SELECT host, COUNT(*) as count
            FROM request_log
            WHERE blocked = 1 AND timestamp > ?
            GROUP BY host
            ORDER BY count DESC
            LIMIT ?
        """, (last_24h, limit)).fetchall()

        return [{"host": r["host"], "count": r["count"]} for r in rows]


# --- Device endpoints ---

@app.get("/api/devices")
def get_devices():
    """Get all devices seen on the network with their stats."""
    with get_db() as conn:
        now = time.time()
        last_24h = now - 86400

        rows = conn.execute("""
            SELECT
                client_ip,
                COUNT(*) as total_requests,
                SUM(blocked) as blocked_requests,
                SUM(bytes_saved) as bytes_saved,
                MAX(timestamp) as last_seen
            FROM request_log
            WHERE timestamp > ?
            GROUP BY client_ip
            ORDER BY total_requests DESC
        """, (last_24h,)).fetchall()

        # Load aliases
        aliases = _load_device_aliases()

        return [
            {
                "ip": r["client_ip"],
                "name": aliases.get(r["client_ip"], ""),
                "total_requests": r["total_requests"],
                "blocked_requests": r["blocked_requests"],
                "bytes_saved": r["bytes_saved"],
                "last_seen": r["last_seen"],
            }
            for r in rows
        ]


@app.post("/api/devices/alias")
def set_device_alias(entry: DeviceAlias):
    """Set a friendly name for a device."""
    aliases = _load_device_aliases()
    aliases[entry.ip] = entry.name
    _save_device_aliases(aliases)
    return {"ok": True}


def _load_device_aliases() -> dict:
    path = CONFIG_DIR / "device-aliases.txt"
    if not path.exists():
        return {}
    aliases = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            ip, name = line.split("=", 1)
            aliases[ip.strip()] = name.strip()
    return aliases


def _save_device_aliases(aliases: dict):
    path = CONFIG_DIR / "device-aliases.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{ip}={name}" for ip, name in aliases.items()]
    path.write_text("\n".join(lines) + "\n")


# --- Blocklist endpoints ---

@app.get("/api/blocklist")
def get_blocklist():
    """Get current blocked domains."""
    return {"domains": _read_domain_list(BLOCKLIST_PATH)}


@app.post("/api/blocklist")
def add_to_blocklist(entry: DomainEntry):
    """Add a domain to the blocklist."""
    domains = _read_domain_list(BLOCKLIST_PATH)
    domain = entry.domain.lower().strip()
    if domain not in domains:
        domains.append(domain)
        _write_domain_list(BLOCKLIST_PATH, domains)
    return {"ok": True, "count": len(domains)}


@app.delete("/api/blocklist/{domain}")
def remove_from_blocklist(domain: str):
    """Remove a domain from the blocklist."""
    domains = _read_domain_list(BLOCKLIST_PATH)
    domain = domain.lower().strip()
    domains = [d for d in domains if d != domain]
    _write_domain_list(BLOCKLIST_PATH, domains)
    return {"ok": True, "count": len(domains)}


# --- Whitelist endpoints ---

@app.get("/api/whitelist")
def get_whitelist():
    """Get current whitelisted domains."""
    return {"domains": _read_domain_list(WHITELIST_PATH)}


@app.post("/api/whitelist")
def add_to_whitelist(entry: DomainEntry):
    """Add a domain to the whitelist."""
    domains = _read_domain_list(WHITELIST_PATH)
    domain = entry.domain.lower().strip()
    if domain not in domains:
        domains.append(domain)
        _write_domain_list(WHITELIST_PATH, domains)
    return {"ok": True, "count": len(domains)}


@app.delete("/api/whitelist/{domain}")
def remove_from_whitelist(domain: str):
    """Remove a domain from the whitelist."""
    domains = _read_domain_list(WHITELIST_PATH)
    domain = domain.lower().strip()
    domains = [d for d in domains if d != domain]
    _write_domain_list(WHITELIST_PATH, domains)
    return {"ok": True, "count": len(domains)}


# --- System endpoints ---

@app.get("/api/system/status")
def get_system_status():
    """Get system health info."""
    import subprocess
    import os

    def service_active(name: str) -> bool:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", name],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() == "active"
        except Exception:
            return False

    cert_exists = Path(CERT_PATH).exists()

    return {
        "proxy_running": service_active("netgate-proxy"),
        "dns_running": service_active("dnsmasq"),
        "cert_installed": cert_exists,
        "blocklist_count": len(_read_domain_list(BLOCKLIST_PATH)),
        "whitelist_count": len(_read_domain_list(WHITELIST_PATH)),
        "uptime": _get_uptime(),
    }


@app.get("/api/system/cert")
def download_cert():
    """Download the CA certificate for installation on devices."""
    if not Path(CERT_PATH).exists():
        raise HTTPException(404, "CA certificate not generated yet. Start the proxy first.")
    return FileResponse(
        CERT_PATH,
        media_type="application/x-pem-file",
        filename="netgate-ca.pem"
    )


def _get_uptime() -> str:
    try:
        with open("/proc/uptime") as f:
            seconds = float(f.read().split()[0])
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"
    except Exception:
        return "unknown"


# --- Helpers ---

def _read_domain_list(path: str) -> list[str]:
    try:
        with open(path) as f:
            return [
                line.strip().lower()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        return []


def _write_domain_list(path: str, domains: list[str]):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write("# Netgate domain list\n")
        for d in sorted(set(domains)):
            f.write(d + "\n")


# --- List update endpoint ---

@app.post("/api/lists/update")
def update_lists():
    """Trigger a blocklist update."""
    import subprocess
    try:
        result = subprocess.run(
            ["python3", "/opt/netgate/lists/update_lists.py"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise HTTPException(500, f"Update failed: {result.stderr}")
        # Parse count from output
        count = len(_read_domain_list(BLOCKLIST_PATH))
        return {"ok": True, "count": count}
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Update timed out")


# --- Serve frontend static files ---

frontend_dir = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
