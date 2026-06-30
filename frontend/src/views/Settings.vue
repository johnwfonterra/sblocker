<template>
  <div class="settings">
    <h2>Settings</h2>

    <div class="section">
      <h3>CA Certificate</h3>
      <p class="desc">
        Install this certificate on your devices to enable HTTPS filtering.
        Without it, devices will show SSL errors.
      </p>
      <a href="/api/system/cert" download class="btn">Download CA Certificate</a>

      <details class="install-guide">
        <summary>Installation instructions</summary>
        <div class="guide-content">
          <h4>Windows</h4>
          <ol>
            <li>Double-click the .pem file</li>
            <li>Click "Install Certificate"</li>
            <li>Select "Local Machine" → "Trusted Root Certification Authorities"</li>
          </ol>

          <h4>macOS</h4>
          <ol>
            <li>Double-click to add to Keychain</li>
            <li>Find it in Keychain Access → System</li>
            <li>Double-click → Trust → "Always Trust"</li>
          </ol>

          <h4>Linux</h4>
          <pre>sudo cp netgate-ca.pem /usr/local/share/ca-certificates/netgate.crt
sudo update-ca-certificates</pre>

          <h4>iOS</h4>
          <ol>
            <li>Email/AirDrop the cert to the device</li>
            <li>Settings → General → VPN & Device Mgmt → Install</li>
            <li>Settings → General → About → Certificate Trust → Enable</li>
          </ol>

          <h4>Android</h4>
          <ol>
            <li>Copy cert to device</li>
            <li>Settings → Security → Install from storage</li>
          </ol>
        </div>
      </details>
    </div>

    <div class="section">
      <h3>System Status</h3>
      <div class="status-grid" v-if="status">
        <div class="status-item">
          <span class="label">Proxy</span>
          <span class="value" :class="{ ok: status.proxy_running }">
            {{ status.proxy_running ? 'Running' : 'Stopped' }}
          </span>
        </div>
        <div class="status-item">
          <span class="label">DNS</span>
          <span class="value" :class="{ ok: status.dns_running }">
            {{ status.dns_running ? 'Running' : 'Stopped' }}
          </span>
        </div>
        <div class="status-item">
          <span class="label">CA Certificate</span>
          <span class="value" :class="{ ok: status.cert_installed }">
            {{ status.cert_installed ? 'Generated' : 'Not found' }}
          </span>
        </div>
        <div class="status-item">
          <span class="label">Blocked Domains</span>
          <span class="value">{{ status.blocklist_count }}</span>
        </div>
        <div class="status-item">
          <span class="label">Whitelisted Domains</span>
          <span class="value">{{ status.whitelist_count }}</span>
        </div>
        <div class="status-item">
          <span class="label">Uptime</span>
          <span class="value">{{ status.uptime }}</span>
        </div>
      </div>
    </div>

    <div class="section">
      <h3>Update Blocklists</h3>
      <p class="desc">Download the latest community blocklists.</p>
      <button @click="updateLists" class="btn" :disabled="updating">
        {{ updating ? 'Updating...' : 'Update Now' }}
      </button>
      <p v-if="updateResult" class="result">{{ updateResult }}</p>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      status: null,
      updating: false,
      updateResult: '',
    }
  },
  async mounted() {
    const res = await fetch('/api/system/status')
    this.status = await res.json()
  },
  methods: {
    async updateLists() {
      this.updating = true
      this.updateResult = ''
      try {
        const res = await fetch('/api/lists/update', { method: 'POST' })
        const data = await res.json()
        this.updateResult = `Updated: ${data.count} domains loaded`
      } catch (e) {
        this.updateResult = 'Update failed'
      }
      this.updating = false
    },
  },
}
</script>

<style scoped>
.settings h2 { margin-bottom: 24px; }

.section {
  background: #16202a;
  border: 1px solid #2f3336;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.section h3 {
  font-size: 1.1rem;
  margin-bottom: 8px;
}

.desc {
  color: #71767b;
  font-size: 0.9rem;
  margin-bottom: 16px;
}

.btn {
  display: inline-block;
  padding: 10px 20px;
  background: #1d9bf0;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  text-decoration: none;
}

.btn:disabled {
  opacity: 0.5;
  cursor: default;
}

.install-guide {
  margin-top: 16px;
  color: #71767b;
}

.install-guide summary {
  cursor: pointer;
  color: #1d9bf0;
}

.guide-content {
  margin-top: 12px;
  padding: 16px;
  background: #0f1419;
  border-radius: 8px;
}

.guide-content h4 {
  margin-top: 12px;
  margin-bottom: 6px;
  color: #e7e9ea;
}

.guide-content h4:first-child { margin-top: 0; }

.guide-content ol {
  margin-left: 20px;
  margin-bottom: 8px;
}

.guide-content pre {
  background: #16202a;
  padding: 8px 12px;
  border-radius: 4px;
  font-size: 0.85rem;
  overflow-x: auto;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 14px;
  background: #0f1419;
  border-radius: 8px;
}

.label { color: #71767b; }
.value { color: #e7e9ea; font-weight: 600; }
.value.ok { color: #00ba7c; }

.result {
  margin-top: 12px;
  color: #00ba7c;
  font-size: 0.9rem;
}
</style>
