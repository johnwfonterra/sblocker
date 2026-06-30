<template>
  <div class="dashboard">
    <h2>Dashboard</h2>

    <div class="stats-grid" v-if="stats">
      <div class="stat-card">
        <div class="stat-value">{{ formatNumber(stats.total_requests) }}</div>
        <div class="stat-label">Total Requests (24h)</div>
      </div>
      <div class="stat-card blocked">
        <div class="stat-value">{{ formatNumber(stats.blocked_requests) }}</div>
        <div class="stat-label">Blocked ({{ stats.block_percentage }}%)</div>
      </div>
      <div class="stat-card filtered">
        <div class="stat-value">{{ formatNumber(stats.filtered_requests) }}</div>
        <div class="stat-label">Pages Filtered</div>
      </div>
      <div class="stat-card saved">
        <div class="stat-value">{{ formatBytes(stats.bytes_saved) }}</div>
        <div class="stat-label">Bandwidth Saved</div>
      </div>
    </div>

    <div class="panels">
      <div class="panel">
        <h3>Requests Over Time</h3>
        <div class="chart">
          <div class="chart-bars" v-if="timeline.length">
            <div
              v-for="point in timeline"
              :key="point.hour"
              class="chart-bar-group"
            >
              <div class="chart-bar total" :style="{ height: barHeight(point.total) }"></div>
              <div class="chart-bar blocked" :style="{ height: barHeight(point.blocked) }"></div>
            </div>
          </div>
          <p v-else class="empty">No data yet</p>
        </div>
      </div>

      <div class="panel">
        <h3>Top Blocked Domains</h3>
        <table v-if="topBlocked.length">
          <tr v-for="item in topBlocked" :key="item.host">
            <td class="domain">{{ item.host }}</td>
            <td class="count">{{ item.count }}</td>
          </tr>
        </table>
        <p v-else class="empty">No blocked requests yet</p>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      stats: null,
      timeline: [],
      topBlocked: [],
    }
  },
  async mounted() {
    await Promise.all([
      this.loadStats(),
      this.loadTimeline(),
      this.loadTopBlocked(),
    ])
  },
  methods: {
    async loadStats() {
      const res = await fetch('/api/stats/summary')
      this.stats = await res.json()
    },
    async loadTimeline() {
      const res = await fetch('/api/stats/timeline?hours=24')
      this.timeline = await res.json()
    },
    async loadTopBlocked() {
      const res = await fetch('/api/stats/top-blocked?limit=10')
      this.topBlocked = await res.json()
    },
    formatNumber(n) {
      if (n >= 1000000) return (n / 1000000).toFixed(1) + 'M'
      if (n >= 1000) return (n / 1000).toFixed(1) + 'K'
      return String(n)
    },
    formatBytes(b) {
      if (b >= 1073741824) return (b / 1073741824).toFixed(1) + ' GB'
      if (b >= 1048576) return (b / 1048576).toFixed(1) + ' MB'
      if (b >= 1024) return (b / 1024).toFixed(1) + ' KB'
      return b + ' B'
    },
    barHeight(value) {
      const max = Math.max(...this.timeline.map(p => p.total), 1)
      return Math.max(2, (value / max) * 120) + 'px'
    },
  },
}
</script>

<style scoped>
.dashboard h2 {
  margin-bottom: 24px;
  font-size: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: #16202a;
  border: 1px solid #2f3336;
  border-radius: 12px;
  padding: 20px;
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #e7e9ea;
}

.stat-card.blocked .stat-value { color: #f4212e; }
.stat-card.filtered .stat-value { color: #ffd400; }
.stat-card.saved .stat-value { color: #00ba7c; }

.stat-label {
  font-size: 0.85rem;
  color: #71767b;
  margin-top: 4px;
}

.panels {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
}

.panel {
  background: #16202a;
  border: 1px solid #2f3336;
  border-radius: 12px;
  padding: 20px;
}

.panel h3 {
  font-size: 1rem;
  margin-bottom: 16px;
  color: #71767b;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 120px;
}

.chart-bar-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
  position: relative;
}

.chart-bar {
  width: 100%;
  border-radius: 2px 2px 0 0;
  position: absolute;
  bottom: 0;
}

.chart-bar.total { background: #2f3336; }
.chart-bar.blocked { background: #f4212e; opacity: 0.8; }

table {
  width: 100%;
}

table tr {
  border-bottom: 1px solid #2f3336;
}

table td {
  padding: 8px 0;
  font-size: 0.9rem;
}

.domain {
  color: #e7e9ea;
  word-break: break-all;
}

.count {
  text-align: right;
  color: #71767b;
  white-space: nowrap;
}

.empty {
  color: #71767b;
  font-style: italic;
}

@media (max-width: 768px) {
  .panels { grid-template-columns: 1fr; }
}
</style>
