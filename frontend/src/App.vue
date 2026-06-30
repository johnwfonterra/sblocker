<template>
  <div class="app">
    <nav class="sidebar">
      <div class="logo">
        <h1>Netgate</h1>
      </div>
      <ul>
        <li><router-link to="/">Dashboard</router-link></li>
        <li><router-link to="/devices">Devices</router-link></li>
        <li><router-link to="/lists">Block/Allow Lists</router-link></li>
        <li><router-link to="/settings">Settings</router-link></li>
      </ul>
      <div class="status" v-if="status">
        <div class="status-dot" :class="{ active: status.proxy_running }"></div>
        <span>Proxy {{ status.proxy_running ? 'Active' : 'Down' }}</span>
      </div>
    </nav>
    <main class="content">
      <router-view />
    </main>
  </div>
</template>

<script>
export default {
  data() {
    return { status: null }
  },
  async mounted() {
    try {
      const res = await fetch('/api/system/status')
      this.status = await res.json()
    } catch (e) {
      this.status = { proxy_running: false }
    }
  }
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0f1419;
  color: #e7e9ea;
}

.app {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 220px;
  background: #16202a;
  padding: 24px 16px;
  border-right: 1px solid #2f3336;
  display: flex;
  flex-direction: column;
}

.logo h1 {
  font-size: 1.4rem;
  color: #1d9bf0;
  margin-bottom: 32px;
}

.sidebar ul {
  list-style: none;
  flex: 1;
}

.sidebar li {
  margin-bottom: 4px;
}

.sidebar a {
  display: block;
  padding: 10px 16px;
  color: #e7e9ea;
  text-decoration: none;
  border-radius: 8px;
  transition: background 0.15s;
}

.sidebar a:hover,
.sidebar a.router-link-active {
  background: #1d2d3d;
  color: #1d9bf0;
}

.status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  font-size: 0.85rem;
  color: #71767b;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f4212e;
}

.status-dot.active {
  background: #00ba7c;
}

.content {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}
</style>
