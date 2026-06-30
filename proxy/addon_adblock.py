"""
Netgate mitmproxy addon - Ad/tracker blocking and content filtering.

This addon:
1. Blocks requests to known ad/tracker domains (returns 204 No Content)
2. Strips ad-related HTML elements from responses
3. Removes tracking scripts
4. Logs stats to SQLite for the management UI
"""

import re
import time
import sqlite3
import threading
from pathlib import Path
from mitmproxy import http, ctx
from mitmproxy.addonmanager import Loader

DB_PATH = "/var/lib/netgate/stats.db"
BLOCKLIST_PATH = "/etc/netgate/blocklist-domains.txt"
WHITELIST_PATH = "/etc/netgate/whitelist-domains.txt"

# Pre-compiled patterns for HTML ad removal
AD_ELEMENT_PATTERNS = [
    # Ad containers by class/id
    re.compile(
        r'<(div|section|aside|span)[^>]*\s(class|id)=["\'][^"\']*'
        r'(ad-container|ad-slot|ad-wrapper|adsbygoogle|sponsored-content|'
        r'advertisement|banner-ad|dfp-ad)[^"\']*["\'][^>]*>.*?</\1>',
        re.DOTALL | re.IGNORECASE
    ),
    # Third-party ad scripts
    re.compile(
        r'<script[^>]*src=["\'][^"\']*('
        r'doubleclick\.net|googlesyndication\.com|adservice\.google|'
        r'amazon-adsystem\.com|adnxs\.com|outbrain\.com|taboola\.com|'
        r'criteo\.com|rubiconproject\.com|pubmatic\.com'
        r')[^"\']*["\'][^>]*>.*?</script>',
        re.DOTALL | re.IGNORECASE
    ),
    # Tracking scripts
    re.compile(
        r'<script[^>]*src=["\'][^"\']*('
        r'google-analytics\.com|googletagmanager\.com|'
        r'facebook\.net/en_US/fbevents|hotjar\.com|'
        r'mixpanel\.com|segment\.com/analytics|'
        r'clarity\.ms|newrelic\.com'
        r')[^"\']*["\'][^>]*>.*?</script>',
        re.DOTALL | re.IGNORECASE
    ),
    # Inline tracking pixels
    re.compile(
        r'<img[^>]*src=["\'][^"\']*('
        r'pixel|track|beacon|1x1|spacer'
        r')[^"\']*["\'][^>]*(width=["\']1|height=["\']1)[^>]*/?>',
        re.DOTALL | re.IGNORECASE
    ),
    # Ad iframes
    re.compile(
        r'<iframe[^>]*src=["\'][^"\']*('
        r'doubleclick|googlesyndication|adserver|adframe|'
        r'amazon-adsystem|taboola'
        r')[^"\']*["\'][^>]*>.*?</iframe>',
        re.DOTALL | re.IGNORECASE
    ),
]

# Inline script patterns to remove
INLINE_TRACKING_PATTERNS = [
    re.compile(r"<script[^>]*>[^<]*ga\s*\(\s*['\"]create['\"][^<]*</script>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<script[^>]*>[^<]*gtag\s*\([^<]*</script>", re.DOTALL | re.IGNORECASE),
    re.compile(r"<script[^>]*>[^<]*fbq\s*\([^<]*</script>", re.DOTALL | re.IGNORECASE),
]


class StatsWriter:
    """Thread-safe stats writer to SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS request_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    client_ip TEXT NOT NULL,
                    host TEXT NOT NULL,
                    path TEXT,
                    blocked INTEGER DEFAULT 0,
                    filtered INTEGER DEFAULT 0,
                    bytes_saved INTEGER DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_request_timestamp
                ON request_log(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_request_client
                ON request_log(client_ip)
            """)

    def log_request(self, client_ip: str, host: str, path: str,
                    blocked: bool = False, filtered: bool = False, bytes_saved: int = 0):
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT INTO request_log (timestamp, client_ip, host, path, blocked, filtered, bytes_saved) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (time.time(), client_ip, host, path, int(blocked), int(filtered), bytes_saved)
                    )
            except Exception as e:
                ctx.log.error(f"Stats write failed: {e}")


class NetgateAddon:
    """Main mitmproxy addon for Netgate."""

    def __init__(self):
        self.blocked_domains: set[str] = set()
        self.whitelisted_domains: set[str] = set()
        self.stats = StatsWriter(DB_PATH)
        self._load_lists()

    def _load_lists(self):
        """Load block and whitelist from disk."""
        self.blocked_domains = self._read_domain_file(BLOCKLIST_PATH)
        self.whitelisted_domains = self._read_domain_file(WHITELIST_PATH)
        ctx.log.info(f"[netgate] Loaded {len(self.blocked_domains)} blocked domains, "
                     f"{len(self.whitelisted_domains)} whitelisted")

    @staticmethod
    def _read_domain_file(path: str) -> set[str]:
        """Read a newline-separated domain list file."""
        try:
            with open(path) as f:
                return {
                    line.strip().lower()
                    for line in f
                    if line.strip() and not line.startswith("#")
                }
        except FileNotFoundError:
            return set()

    def _is_blocked(self, host: str) -> bool:
        """Check if a host should be blocked."""
        host = host.lower()

        # Whitelist takes priority
        if host in self.whitelisted_domains:
            return False
        for w in self.whitelisted_domains:
            if host.endswith("." + w):
                return False

        # Check exact match
        if host in self.blocked_domains:
            return True

        # Check parent domain match
        parts = host.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in self.blocked_domains:
                return True

        return False

    def request(self, flow: http.HTTPFlow):
        """Intercept requests - block known ad/tracker domains."""
        host = flow.request.pretty_host
        client_ip = flow.client_conn.peername[0] if flow.client_conn.peername else "unknown"

        if self._is_blocked(host):
            flow.response = http.Response.make(
                204,
                b"",
                {"Content-Type": "text/plain", "X-Netgate": "blocked"}
            )
            self.stats.log_request(client_ip, host, flow.request.path, blocked=True)
            return

    def response(self, flow: http.HTTPFlow):
        """Filter ad content from HTML responses."""
        if flow.response is None:
            return

        content_type = flow.response.headers.get("content-type", "")
        if "text/html" not in content_type:
            # Log non-filtered request
            client_ip = flow.client_conn.peername[0] if flow.client_conn.peername else "unknown"
            self.stats.log_request(client_ip, flow.request.pretty_host, flow.request.path)
            return

        text = flow.response.get_text()
        if not text:
            return

        original_len = len(text)

        # Apply all ad-removal patterns
        for pattern in AD_ELEMENT_PATTERNS:
            text = pattern.sub("<!-- netgate:removed -->", text)

        # Remove inline tracking
        for pattern in INLINE_TRACKING_PATTERNS:
            text = pattern.sub("", text)

        new_len = len(text)
        bytes_saved = original_len - new_len
        filtered = bytes_saved > 0

        if filtered:
            flow.response.set_text(text)

        client_ip = flow.client_conn.peername[0] if flow.client_conn.peername else "unknown"
        self.stats.log_request(
            client_ip, flow.request.pretty_host, flow.request.path,
            filtered=filtered, bytes_saved=max(0, bytes_saved)
        )


addons = [NetgateAddon()]
