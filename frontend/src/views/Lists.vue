<template>
  <div class="lists">
    <h2>Block &amp; Allow Lists</h2>

    <div class="tabs">
      <button :class="{ active: tab === 'block' }" @click="tab = 'block'">
        Blocklist ({{ blocklist.length }})
      </button>
      <button :class="{ active: tab === 'white' }" @click="tab = 'white'">
        Allowlist ({{ whitelist.length }})
      </button>
    </div>

    <!-- Add domain form -->
    <div class="add-form">
      <input
        v-model="newDomain"
        @keyup.enter="addDomain"
        :placeholder="tab === 'block' ? 'Add domain to block...' : 'Add domain to allow...'"
      />
      <button @click="addDomain" class="btn-add">Add</button>
    </div>

    <!-- Blocklist -->
    <div v-if="tab === 'block'">
      <div class="domain-list">
        <div v-for="domain in paginatedBlocklist" :key="domain" class="domain-row">
          <span>{{ domain }}</span>
          <button @click="removeDomain('block', domain)" class="btn-remove">Remove</button>
        </div>
      </div>
      <div class="pagination" v-if="blocklist.length > pageSize">
        <button @click="page = Math.max(0, page - 1)" :disabled="page === 0">Prev</button>
        <span>{{ page + 1 }} / {{ totalPages('block') }}</span>
        <button @click="page = Math.min(totalPages('block') - 1, page + 1)" :disabled="page >= totalPages('block') - 1">Next</button>
      </div>
    </div>

    <!-- Whitelist -->
    <div v-if="tab === 'white'">
      <div class="domain-list">
        <div v-for="domain in paginatedWhitelist" :key="domain" class="domain-row">
          <span>{{ domain }}</span>
          <button @click="removeDomain('white', domain)" class="btn-remove">Remove</button>
        </div>
      </div>
      <div class="pagination" v-if="whitelist.length > pageSize">
        <button @click="page = Math.max(0, page - 1)" :disabled="page === 0">Prev</button>
        <span>{{ page + 1 }} / {{ totalPages('white') }}</span>
        <button @click="page = Math.min(totalPages('white') - 1, page + 1)" :disabled="page >= totalPages('white') - 1">Next</button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      tab: 'block',
      blocklist: [],
      whitelist: [],
      newDomain: '',
      page: 0,
      pageSize: 50,
    }
  },
  computed: {
    paginatedBlocklist() {
      const start = this.page * this.pageSize
      return this.blocklist.slice(start, start + this.pageSize)
    },
    paginatedWhitelist() {
      const start = this.page * this.pageSize
      return this.whitelist.slice(start, start + this.pageSize)
    },
  },
  watch: {
    tab() { this.page = 0 }
  },
  async mounted() {
    await Promise.all([this.loadBlocklist(), this.loadWhitelist()])
  },
  methods: {
    async loadBlocklist() {
      const res = await fetch('/api/blocklist')
      const data = await res.json()
      this.blocklist = data.domains
    },
    async loadWhitelist() {
      const res = await fetch('/api/whitelist')
      const data = await res.json()
      this.whitelist = data.domains
    },
    async addDomain() {
      const domain = this.newDomain.trim().toLowerCase()
      if (!domain) return

      const endpoint = this.tab === 'block' ? '/api/blocklist' : '/api/whitelist'
      await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain }),
      })

      this.newDomain = ''
      if (this.tab === 'block') await this.loadBlocklist()
      else await this.loadWhitelist()
    },
    async removeDomain(list, domain) {
      const endpoint = list === 'block' ? '/api/blocklist' : '/api/whitelist'
      await fetch(`${endpoint}/${encodeURIComponent(domain)}`, { method: 'DELETE' })

      if (list === 'block') await this.loadBlocklist()
      else await this.loadWhitelist()
    },
    totalPages(list) {
      const arr = list === 'block' ? this.blocklist : this.whitelist
      return Math.ceil(arr.length / this.pageSize)
    },
  },
}
</script>

<style scoped>
.lists h2 { margin-bottom: 20px; }

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.tabs button {
  padding: 8px 20px;
  border: 1px solid #2f3336;
  background: #16202a;
  color: #e7e9ea;
  border-radius: 8px;
  cursor: pointer;
}

.tabs button.active {
  background: #1d9bf0;
  border-color: #1d9bf0;
  color: #fff;
}

.add-form {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.add-form input {
  flex: 1;
  padding: 10px 16px;
  background: #16202a;
  border: 1px solid #2f3336;
  border-radius: 8px;
  color: #e7e9ea;
  font-size: 0.95rem;
  outline: none;
}

.add-form input:focus {
  border-color: #1d9bf0;
}

.btn-add {
  padding: 10px 20px;
  background: #1d9bf0;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}

.domain-list {
  background: #16202a;
  border: 1px solid #2f3336;
  border-radius: 12px;
  overflow: hidden;
}

.domain-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  border-bottom: 1px solid #2f3336;
  font-family: monospace;
  font-size: 0.9rem;
}

.domain-row:last-child { border-bottom: none; }

.btn-remove {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #f4212e;
  color: #f4212e;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-remove:hover {
  background: #f4212e;
  color: #fff;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
}

.pagination button {
  padding: 6px 14px;
  background: #16202a;
  border: 1px solid #2f3336;
  color: #e7e9ea;
  border-radius: 6px;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: default;
}

.pagination span {
  color: #71767b;
  font-size: 0.85rem;
}
</style>
