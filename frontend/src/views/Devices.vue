<template>
  <div class="devices">
    <h2>Devices</h2>
    <p class="subtitle">All devices seen on your network in the last 24 hours</p>

    <table v-if="devices.length">
      <thead>
        <tr>
          <th>Device</th>
          <th>IP Address</th>
          <th>Requests</th>
          <th>Blocked</th>
          <th>Saved</th>
          <th>Last Seen</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="device in devices" :key="device.ip">
          <td>
            <span v-if="editingIp !== device.ip" @dblclick="startEdit(device)" class="device-name">
              {{ device.name || 'Unknown Device' }}
            </span>
            <input
              v-else
              v-model="editName"
              @keyup.enter="saveAlias(device)"
              @blur="saveAlias(device)"
              class="name-input"
              autofocus
            />
          </td>
          <td class="ip">{{ device.ip }}</td>
          <td>{{ device.total_requests }}</td>
          <td class="blocked">{{ device.blocked_requests }}</td>
          <td class="saved">{{ formatBytes(device.bytes_saved) }}</td>
          <td class="time">{{ timeAgo(device.last_seen) }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">No devices detected yet</p>
  </div>
</template>

<script>
export default {
  data() {
    return {
      devices: [],
      editingIp: null,
      editName: '',
    }
  },
  async mounted() {
    const res = await fetch('/api/devices')
    this.devices = await res.json()
  },
  methods: {
    startEdit(device) {
      this.editingIp = device.ip
      this.editName = device.name
    },
    async saveAlias(device) {
      if (this.editingIp) {
        await fetch('/api/devices/alias', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ ip: device.ip, name: this.editName }),
        })
        device.name = this.editName
        this.editingIp = null
      }
    },
    formatBytes(b) {
      if (b >= 1048576) return (b / 1048576).toFixed(1) + ' MB'
      if (b >= 1024) return (b / 1024).toFixed(1) + ' KB'
      return (b || 0) + ' B'
    },
    timeAgo(timestamp) {
      const diff = Date.now() / 1000 - timestamp
      if (diff < 60) return 'just now'
      if (diff < 3600) return Math.floor(diff / 60) + 'm ago'
      return Math.floor(diff / 3600) + 'h ago'
    },
  },
}
</script>

<style scoped>
.devices h2 { margin-bottom: 4px; }
.subtitle { color: #71767b; margin-bottom: 24px; font-size: 0.9rem; }

table {
  width: 100%;
  border-collapse: collapse;
  background: #16202a;
  border-radius: 12px;
  overflow: hidden;
}

thead {
  background: #1d2d3d;
}

th {
  text-align: left;
  padding: 12px 16px;
  font-size: 0.8rem;
  text-transform: uppercase;
  color: #71767b;
}

td {
  padding: 12px 16px;
  border-top: 1px solid #2f3336;
}

.device-name {
  cursor: pointer;
  border-bottom: 1px dashed #2f3336;
}

.name-input {
  background: #0f1419;
  border: 1px solid #1d9bf0;
  color: #e7e9ea;
  padding: 4px 8px;
  border-radius: 4px;
  outline: none;
  width: 140px;
}

.ip { font-family: monospace; color: #71767b; }
.blocked { color: #f4212e; }
.saved { color: #00ba7c; }
.time { color: #71767b; }
.empty { color: #71767b; font-style: italic; }
</style>
