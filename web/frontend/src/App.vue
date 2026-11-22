<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from './stores/auth'
import { useRouter, useRoute } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const sidebarOpen = ref(true)
const mobileDrawerOpen = ref(false)
const isMobile = ref(false)

function checkMobile() {
  isMobile.value = window.innerWidth <= 768
  if (isMobile.value) {
    sidebarOpen.value = false
  } else {
    sidebarOpen.value = true
    mobileDrawerOpen.value = false
  }
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

const hideSidebar = computed(() => {
  return route.meta?.hideSidebar === true || !auth.isAuthenticated
})

const currentTab = computed(() => {
  if (route.query.tab === 'agents') return 'agents'
  if (route.query.tab === 'images') return 'images'
  return 'instances'
})

function toggleSidebar() {
  if (isMobile.value) {
    mobileDrawerOpen.value = !mobileDrawerOpen.value
  } else {
    sidebarOpen.value = !sidebarOpen.value
  }
}

function navigateTab(tabName) {
  mobileDrawerOpen.value = false
  router.push({ path: '/dashboard', query: tabName === 'instances' ? {} : { tab: tabName } })
}

async function handleLogout() {
  mobileDrawerOpen.value = false
  auth.logout()
  router.push({ name: 'Login' })
}
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--no-sidebar': hideSidebar, 'app-shell--mobile': isMobile }">
    <!-- MOBILE TOP BAR (Only on screen <= 768px) -->
    <header v-if="!hideSidebar && isMobile" class="mobile-header">
      <button class="mobile-burger-btn" @click="toggleSidebar" aria-label="Abrir Menu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
      </button>

      <div class="mobile-brand">
        <span class="brand-logo-text">MKOS</span>
        <span class="brand-sub">Virtuale</span>
        <span class="status-pulse-dot" title="Sistema Online" />
      </div>

      <div class="mobile-header-right">
        <span class="client-badge-pill" v-if="auth.user?.username">
          {{ auth.user.username }}
        </span>
      </div>
    </header>

    <!-- MOBILE BACKDROP OVERLAY -->
    <div
      v-if="isMobile && mobileDrawerOpen"
      class="mobile-backdrop"
      @click="mobileDrawerOpen = false"
    />

    <!-- SIDEBAR (DESKTOP & MOBILE DRAWER) -->
    <aside
      v-if="!hideSidebar"
      class="sidebar"
      :class="{
        'sidebar--collapsed': !sidebarOpen && !isMobile,
        'sidebar--mobile-open': isMobile && mobileDrawerOpen,
        'sidebar--mobile-hidden': isMobile && !mobileDrawerOpen
      }"
    >
      <div class="sidebar__header">
        <button class="sidebar__burger" @click="toggleSidebar" title="Alternar Menu">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
        <div v-if="sidebarOpen || isMobile" class="sidebar__logo-group">
          <span class="sidebar__logo">MKOS</span>
          <span class="sidebar__badge">Enterprise</span>
        </div>
      </div>

      <nav class="sidebar__nav">
        <!-- Tab 1: Dispositivos Móveis -->
        <a
          class="sidebar__link"
          :class="{ 'sidebar__link--active': currentTab === 'instances' }"
          title="Dispositivos Android"
          @click.prevent="navigateTab('instances')"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect>
            <line x1="12" y1="18" x2="12.01" y2="18"></line>
          </svg>
          <span v-if="sidebarOpen || isMobile" class="sidebar__label">Dispositivos</span>
        </a>

        <!-- Tab 2: Equipe de Agentes -->
        <a
          class="sidebar__link"
          :class="{ 'sidebar__link--active': currentTab === 'agents' }"
          title="Equipe de Agentes Operacionais"
          @click.prevent="navigateTab('agents')"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
            <circle cx="9" cy="7" r="4"></circle>
            <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
          </svg>
          <span v-if="sidebarOpen || isMobile" class="sidebar__label">Agentes & Operações</span>
        </a>

        <!-- Tab 3: Imagens Base -->
        <a
          class="sidebar__link"
          :class="{ 'sidebar__link--active': currentTab === 'images' }"
          title="Imagens Base do Sistema"
          @click.prevent="navigateTab('images')"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
            <polyline points="2 17 12 22 22 17"></polyline>
            <polyline points="2 12 12 17 22 12"></polyline>
          </svg>
          <span v-if="sidebarOpen || isMobile" class="sidebar__label">Imagens Base</span>
        </a>
      </nav>

      <div class="sidebar__footer">
        <div class="sidebar__user" v-if="auth.isAuthenticated">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
            <circle cx="12" cy="7" r="4"></circle>
          </svg>
          <span v-if="sidebarOpen || isMobile" class="sidebar__user-email">{{ auth.user?.email || auth.user?.username }}</span>
        </div>
        <button class="sidebar__logout" @click="handleLogout" title="Encerrar Sessão">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          <span v-if="sidebarOpen || isMobile" class="sidebar__label">Encerrar Sessão</span>
        </button>
      </div>
    </aside>

    <!-- MAIN APP CONTENT -->
    <main class="main-content" :class="{ 'main-content--with-mobile-nav': !hideSidebar && isMobile }">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- MOBILE BOTTOM NAVIGATION BAR -->
    <nav v-if="!hideSidebar && isMobile" class="mobile-bottom-nav">
      <button
        class="mobile-bottom-nav__item"
        :class="{ 'mobile-bottom-nav__item--active': currentTab === 'instances' }"
        @click="navigateTab('instances')"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="5" y="2" width="14" height="20" rx="2" ry="2"></rect>
          <line x1="12" y1="18" x2="12.01" y2="18"></line>
        </svg>
        <span>Dispositivos</span>
      </button>

      <button
        class="mobile-bottom-nav__item"
        :class="{ 'mobile-bottom-nav__item--active': currentTab === 'agents' }"
        @click="navigateTab('agents')"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
          <circle cx="9" cy="7" r="4"></circle>
          <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
          <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
        </svg>
        <span>Agentes</span>
      </button>

      <button
        class="mobile-bottom-nav__item"
        :class="{ 'mobile-bottom-nav__item--active': currentTab === 'images' }"
        @click="navigateTab('images')"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
          <polyline points="2 17 12 22 22 17"></polyline>
          <polyline points="2 12 12 17 22 12"></polyline>
        </svg>
        <span>Imagens</span>
      </button>
    </nav>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #09090b;
  color: #f4f4f5;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.app-shell--no-sidebar .main-content {
  width: 100%;
}

/* ── Mobile Top Header ── */
.mobile-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 54px;
  background: rgba(18, 18, 21, 0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  z-index: 90;
}

.mobile-burger-btn {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #18181b;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #a1a1aa;
  border-radius: 8px;
  cursor: pointer;
}

.mobile-brand {
  display: flex;
  align-items: center;
  gap: 6px;
}

.brand-logo-text {
  font-size: 15px;
  font-weight: 800;
  color: #10b981;
  letter-spacing: -0.02em;
}

.brand-sub {
  font-size: 13px;
  font-weight: 600;
  color: #71717a;
}

.status-pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 9999px;
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.8);
  margin-left: 2px;
}

.client-badge-pill {
  font-size: 11px;
  font-weight: 600;
  color: #a1a1aa;
  background: #18181b;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 4px 10px;
  border-radius: 9999px;
}

/* ── Mobile Backdrop ── */
.mobile-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(6px);
  z-index: 95;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ── Sidebar (Desktop & Mobile Drawer) ── */
.sidebar {
  display: flex;
  flex-direction: column;
  width: 240px;
  min-width: 240px;
  background: #121215;
  border-right: 1px solid rgba(255, 255, 255, 0.08);
  padding: 16px 12px;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  overflow: hidden;
  z-index: 100;
}

.sidebar--collapsed {
  width: 68px;
  min-width: 68px;
}

.sidebar__header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 6px;
  margin-bottom: 24px;
}

.sidebar__burger {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.06);
  color: #a1a1aa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.sidebar__burger:hover {
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.4);
  background: rgba(16, 185, 129, 0.08);
}

.sidebar__logo-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sidebar__logo {
  font-size: 16px;
  font-weight: 800;
  color: #10b981;
  letter-spacing: -0.02em;
}

.sidebar__badge {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  color: #71717a;
  background: #18181b;
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}

/* ── Nav links ── */
.sidebar__nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sidebar__link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  color: #a1a1aa;
  text-decoration: none;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s ease;
  white-space: nowrap;
  cursor: pointer;
}

.sidebar__link:hover {
  color: #f4f4f5;
  background: rgba(255, 255, 255, 0.04);
}

.sidebar__link--active {
  color: #10b981;
  background: rgba(16, 185, 129, 0.1);
  font-weight: 600;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.sidebar__link svg {
  flex-shrink: 0;
}

.sidebar__label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ── Footer ── */
.sidebar__footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.sidebar__user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  color: #71717a;
  font-size: 12px;
}

.sidebar__user svg {
  flex-shrink: 0;
}

.sidebar__user-email {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar__logout {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #71717a;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.sidebar__logout:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}

/* ── Main Content Area ── */
.main-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  position: relative;
}

.main-content--with-mobile-nav {
  padding-top: 54px;
  padding-bottom: 64px;
}

/* ── Mobile Bottom Navigation Bar ── */
.mobile-bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: rgba(18, 18, 21, 0.98);
  backdrop-filter: blur(12px);
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 90;
  padding-bottom: env(safe-area-inset-bottom, 0px);
}

.mobile-bottom-nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex: 1;
  height: 100%;
  background: transparent;
  border: none;
  color: #71717a;
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.15s ease;
}

.mobile-bottom-nav__item--active {
  color: #10b981;
  font-weight: 700;
}

/* ── Responsive Adaptations ── */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    width: 270px;
    min-width: 270px;
    z-index: 100;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.8);
    transform: translateX(-100%);
    transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .sidebar--mobile-open {
    transform: translateX(0);
  }

  .sidebar--mobile-hidden {
    transform: translateX(-100%);
  }
}
</style>
