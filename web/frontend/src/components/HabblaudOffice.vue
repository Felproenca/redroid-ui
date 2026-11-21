<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import api from '../api'

const activeSubTab = ref('habblaud') // 'habblaud', 'paperclip', 'timeline'
const agents = ref([])
const clients = ref([])
const events = ref([])
const activeOp = ref(null)
const dispatchLoading = ref('')
const approveLoading = ref(false)

let socket = null
let reconnectTimer = null

function wsBase() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}`
}

function connectWs() {
  if (socket && socket.readyState <= WebSocket.OPEN) return
  
  socket = new WebSocket(`${wsBase()}/ws/operations/live`)
  
  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'state_update') {
        if (data.agents) agents.value = data.agents
        if (data.clients) clients.value = data.clients
        if (data.last_event) {
          events.value.unshift(data.last_event)
          if (events.value.length > 50) events.value.pop()
        }
        if (data.current_op) {
          activeOp.value = data.current_op
        }
      } else if (data.type === 'render_progress') {
        events.value.unshift({
          timestamp: new Date().toLocaleTimeString(),
          agent_id: 'agt_cosmeticos_criador',
          type: 'tool_call',
          content: data.message
        })
      }
    } catch (e) {
      console.error('Error parsing WS message:', e)
    }
  }

  socket.onclose = () => {
    reconnectTimer = setTimeout(connectWs, 3000)
  }
}

async function fetchInitialState() {
  try {
    const res = await api.get('/v1/habblaud/state')
    agents.value = res.data.agents || []
    clients.value = res.data.clients || []
  } catch (e) {
    // Fallback defaults if engine starting
    console.warn('Initial state fetch error:', e)
  }
}

async function dispatchAction(actionName) {
  dispatchLoading.value = actionName
  try {
    let payload = {
      client_id: 'cli_mkos_saas',
      agent_id: 'agt_cosmeticos_criador',
      action: actionName,
      target_recipient: '5511999998888',
      parameters: {
        product_name: 'Sérum Hidratante Anti-Idade',
        hook: 'Sua pele renovada em 7 dias com fórmula natural',
        accent_color: '#10b981',
        require_approval: true
      }
    }

    if (actionName === 'organic_warmup') {
      payload.agent_id = 'agt_cosmeticos_criador'
    } else if (actionName === 'no_show_reminder') {
      payload.agent_id = 'agt_mkos_operacoes'
    }

    const { data } = await api.post('/v1/operations/dispatch', payload)
    activeOp.value = data
  } catch (err) {
    alert(err.response?.data?.detail || err.message || 'Erro ao despachar operação')
  } finally {
    dispatchLoading.value = ''
  }
}

async function approveCurrentOp(taskId) {
  approveLoading.value = true
  try {
    await api.post(`/v1/operations/${taskId}/approve`)
    alert('Operação aprovada com sucesso! Mídia despachada via WhatsApp.')
  } catch (err) {
    alert(err.response?.data?.detail || err.message || 'Erro ao aprovar operação')
  } finally {
    approveLoading.value = false
  }
}

onMounted(() => {
  fetchInitialState()
  connectWs()
})

onUnmounted(() => {
  clearTimeout(reconnectTimer)
  if (socket) {
    socket.onclose = null
    socket.close()
  }
})

// Helpers for agents
function getAgentByRole(role) {
  return agents.value.find(a => a.role === role) || {
    name: 'Agente',
    status: 'idle',
    current_thought: 'Aguardando tarefas...'
  }
}

const directorAgent = computed(() => getAgentByRole('director'))
const leoAgent = computed(() => getAgentByRole('content_creator'))
const claraAgent = computed(() => getAgentByRole('support_and_sales'))
const mkosAgent = computed(() => getAgentByRole('operations_mkos'))
const currentClient = computed(() => clients.value[0] || { client_name: 'MarketingOS', budget_current_usd: 4.20, budget_monthly_usd: 50.0 })

function statusBadgeClass(status) {
  if (status === 'thinking') return 'badge--thinking'
  if (status === 'executing_tool') return 'badge--tool'
  if (status === 'waiting_approval') return 'badge--warn'
  return 'badge--idle'
}

function statusLabel(status) {
  if (status === 'thinking') return 'Pensando...'
  if (status === 'executing_tool') return 'Executando'
  if (status === 'waiting_approval') return 'Aprovação'
  return 'Ocioso'
}
</script>

<template>
  <div class="habblaud-wrapper">
    <!-- Top Action & Governance Bar -->
    <header class="habblaud-topbar">
      <div class="topbar-left">
        <div class="subtab-pills">
          <button class="subtab-btn" :class="{ active: activeSubTab === 'habblaud' }" @click="activeSubTab = 'habblaud'">
            🏢 Escritório Virtual (Habblaud)
          </button>
          <button class="subtab-btn" :class="{ active: activeSubTab === 'paperclip' }" @click="activeSubTab = 'paperclip'">
            📎 Hierarquia Paperclip
          </button>
          <button class="subtab-btn" :class="{ active: activeSubTab === 'timeline' }" @click="activeSubTab = 'timeline'">
            ⚡ OpenBot Runtime (Manus Trace)
          </button>
        </div>

        <div class="engine-pills">
          <span class="engine-badge engine-badge--claw">🐾 OpenClaw Runtime</span>
          <span class="engine-badge engine-badge--bot">🛡️ OpenBot Gateway</span>
          <div class="budget-pill">
            <span class="budget-label">Orçamento:</span>
            <span class="budget-val">US$ {{ currentClient.budget_current_usd?.toFixed(2) }} / {{ currentClient.budget_monthly_usd?.toFixed(2) }}</span>
            <span class="budget-dot" />
          </div>
        </div>
      </div>

      <div class="topbar-right">
        <button class="btn btn--small btn--primary" :disabled="!!dispatchLoading" @click="dispatchAction('create_and_send_reel')">
          <span v-if="dispatchLoading === 'create_and_send_reel'" class="spinner" />
          🎬 Criar Reel (Leo)
        </button>
        <button class="btn btn--small btn--accent-outline" :disabled="!!dispatchLoading" @click="dispatchAction('organic_warmup')">
          <span v-if="dispatchLoading === 'organic_warmup'" class="spinner" />
          ☕ Aquecimento Anti-Ban
        </button>
        <button class="btn btn--small" :disabled="!!dispatchLoading" @click="dispatchAction('no_show_reminder')">
          <span v-if="dispatchLoading === 'no_show_reminder'" class="spinner" />
          📅 Checar No-Show
        </button>
      </div>
    </header>

    <!-- CONTENT VIEW 1: HABBLAUD VIRTUAL PIXEL OFFICE -->
    <div v-if="activeSubTab === 'habblaud'" class="office-container">
      <div class="office-floor">
        <!-- Station 1: Agente Diretor (Supervisor Geral) -->
        <div class="workstation station-director">
          <!-- Thought Bubble -->
          <div class="thought-bubble" :class="{ 'thought-bubble--active': directorAgent.status !== 'idle' }">
            <span class="bubble-title">👔 {{ directorAgent.name }}</span>
            <p class="bubble-text">{{ directorAgent.current_thought }}</p>
          </div>

          <!-- Desk & Avatar -->
          <div class="desk-unit">
            <div class="avatar avatar--director" :class="`avatar--${directorAgent.status}`">
              <span class="avatar-face">👨‍💼</span>
            </div>
            <div class="desk-furniture">
              <span class="computer-screen">💻</span>
            </div>
          </div>

          <div class="station-meta">
            <span class="station-role">NÍVEL 1: DIRETOR</span>
            <span class="badge" :class="statusBadgeClass(directorAgent.status)">{{ statusLabel(directorAgent.status) }}</span>
          </div>
        </div>

        <!-- Station 2: Leo (Mídia & Vídeo UGC) -->
        <div class="workstation station-leo">
          <div class="thought-bubble" :class="{ 'thought-bubble--active': leoAgent.status !== 'idle' }">
            <span class="bubble-title">🎬 {{ leoAgent.name }}</span>
            <p class="bubble-text">{{ leoAgent.current_thought }}</p>
            <button
              v-if="leoAgent.status === 'waiting_approval' && activeOp"
              class="btn btn--small btn--primary btn-approve"
              :disabled="approveLoading"
              @click="approveCurrentOp(activeOp.task_id)"
            >
              <span v-if="approveLoading" class="spinner" /> 👍 Aprovar Postagem
            </button>
          </div>

          <div class="desk-unit">
            <div class="avatar avatar--leo" :class="`avatar--${leoAgent.status}`">
              <span class="avatar-face">🎬</span>
            </div>
            <div class="desk-furniture">
              <span class="computer-screen">🖥️</span>
            </div>
          </div>

          <div class="station-meta">
            <span class="station-role">NÍVEL 2: VÍDEO & UGC</span>
            <span class="badge" :class="statusBadgeClass(leoAgent.status)">{{ statusLabel(leoAgent.status) }}</span>
          </div>
        </div>

        <!-- Station 3: Clara (Atendimento & Vendas WhatsApp) -->
        <div class="workstation station-clara">
          <div class="thought-bubble" :class="{ 'thought-bubble--active': claraAgent.status !== 'idle' }">
            <span class="bubble-title">💬 {{ claraAgent.name }}</span>
            <p class="bubble-text">{{ claraAgent.current_thought }}</p>
          </div>

          <div class="desk-unit">
            <div class="avatar avatar--clara" :class="`avatar--${claraAgent.status}`">
              <span class="avatar-face">👩‍💼</span>
            </div>
            <div class="desk-furniture">
              <span class="computer-screen">📱</span>
            </div>
          </div>

          <div class="station-meta">
            <span class="station-role">NÍVEL 2: VENDAS & PIX</span>
            <span class="badge" :class="statusBadgeClass(claraAgent.status)">{{ statusLabel(claraAgent.status) }}</span>
          </div>
        </div>

        <!-- Station 4: MKOS Operações & No-Show -->
        <div class="workstation station-mkos">
          <div class="thought-bubble" :class="{ 'thought-bubble--active': mkosAgent.status !== 'idle' }">
            <span class="bubble-title">⚙️ {{ mkosAgent.name }}</span>
            <p class="bubble-text">{{ mkosAgent.current_thought }}</p>
          </div>

          <div class="desk-unit">
            <div class="avatar avatar--mkos" :class="`avatar--${mkosAgent.status}`">
              <span class="avatar-face">🤖</span>
            </div>
            <div class="desk-furniture">
              <span class="computer-screen">📊</span>
            </div>
          </div>

          <div class="station-meta">
            <span class="station-role">NÍVEL 2: OPERAÇÕES</span>
            <span class="badge" :class="statusBadgeClass(mkosAgent.status)">{{ statusLabel(mkosAgent.status) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- CONTENT VIEW 2: PAPERCLIP ORGANOGRAM HIERARCHY -->
    <div v-else-if="activeSubTab === 'paperclip'" class="paperclip-container">
      <div class="tree-root">
        <!-- Level 1 Node -->
        <div class="tree-node node-director">
          <div class="node-badge">NÍVEL 1: SUPERVISOR GERAL</div>
          <h3 class="node-title">{{ directorAgent.name }}</h3>
          <p class="node-desc">{{ directorAgent.system_prompt }}</p>
          <div class="node-tools">
            <span v-for="t in directorAgent.tools_allowed" :key="t" class="tool-tag">🔧 {{ t }}</span>
          </div>
        </div>

        <div class="tree-line-down" />

        <!-- Level 2 Branch -->
        <div class="tree-branches">
          <div class="tree-node node-specialist">
            <div class="node-badge">NÍVEL 2: CONTEÚDO</div>
            <h4 class="node-title">{{ leoAgent.name }}</h4>
            <p class="node-desc">{{ leoAgent.system_prompt }}</p>
            <div class="node-tools">
              <span v-for="t in leoAgent.tools_allowed" :key="t" class="tool-tag">🎬 {{ t }}</span>
            </div>
            <div class="subagent-tag">↳ Dispara Subagentes Efêmeros (Remotion concurrency=1)</div>
          </div>

          <div class="tree-node node-specialist">
            <div class="node-badge">NÍVEL 2: ATENDIMENTO</div>
            <h4 class="node-title">{{ claraAgent.name }}</h4>
            <p class="node-desc">{{ claraAgent.system_prompt }}</p>
            <div class="node-tools">
              <span v-for="t in claraAgent.tools_allowed" :key="t" class="tool-tag">💬 {{ t }}</span>
            </div>
            <div class="subagent-tag">↳ Memória isolada por client_id (LGPD)</div>
          </div>

          <div class="tree-node node-specialist">
            <div class="node-badge">NÍVEL 2: OPERAÇÕES MKOS</div>
            <h4 class="node-title">{{ mkosAgent.name }}</h4>
            <p class="node-desc">{{ mkosAgent.system_prompt }}</p>
            <div class="node-tools">
              <span v-for="t in mkosAgent.tools_allowed" :key="t" class="tool-tag">⚙️ {{ t }}</span>
            </div>
            <div class="subagent-tag">↳ Conexão direta com Mural n8n da produção</div>
          </div>
        </div>
      </div>
    </div>

    <!-- CONTENT VIEW 3: MANUS / GROK BOT LIVE ACTION TIMELINE -->
    <div v-else-if="activeSubTab === 'timeline'" class="timeline-container">
      <div class="timeline-header">
        <h3>Linha do Tempo de Execução em Tempo Real (OpenBot / Manus Trace)</h3>
        <span class="events-count">{{ events.length }} eventos registrados</span>
      </div>

      <div v-if="!events.length" class="empty-state">
        <p>Nenhuma operação em andamento. Clique em "Criar Reel" ou "Aquecimento" acima para disparar.</p>
      </div>

      <div v-else class="events-list">
        <div
          v-for="(ev, idx) in events"
          :key="idx"
          class="event-card"
          :class="`event-card--${ev.type}`"
        >
          <div class="event-meta">
            <span class="event-time">{{ ev.timestamp }}</span>
            <span class="event-agent">🤖 {{ ev.agent_id }}</span>
            <span class="event-type-badge">{{ ev.type }}</span>
          </div>
          <div class="event-content">{{ ev.content }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.habblaud-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  background: #09090b;
  overflow: hidden;
}

.habblaud-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #121215;
  border-bottom: 1px solid var(--border);
  gap: 16px;
  flex-wrap: wrap;
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.subtab-pills {
  display: flex;
  background: #18181b;
  padding: 3px;
  border-radius: 10px;
  border: 1px solid var(--border);
}

.subtab-btn {
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-muted);
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all var(--transition);
}

.subtab-btn.active {
  background: #27272a;
  color: #10b981;
}

.budget-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.25);
  padding: 5px 12px;
  border-radius: 20px;
  font-size: 12px;
}

.budget-val {
  color: #10b981;
  font-weight: 700;
}

.budget-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 6px #10b981;
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── OFFICE CANVAS ── */
.office-container {
  flex: 1;
  padding: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
  background:
    radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.04) 0%, transparent 60%),
    linear-gradient(#121215 1px, transparent 1px),
    linear-gradient(90deg, #121215 1px, transparent 1px);
  background-size: 100% 100%, 32px 32px, 32px 32px;
}

.office-floor {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 40px;
  max-width: 900px;
  width: 100%;
}

.workstation {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  background: rgba(18, 18, 21, 0.6);
  border: 1px solid var(--border);
  border-radius: 24px;
  padding: 24px;
  backdrop-filter: blur(8px);
  transition: all var(--transition);
}

.workstation:hover {
  border-color: rgba(16, 185, 129, 0.3);
}

.thought-bubble {
  position: relative;
  background: #18181b;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 10px 14px;
  min-height: 56px;
  width: 100%;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
}

.thought-bubble::after {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 8px 8px 0;
  border-style: solid;
  border-color: #18181b transparent;
  display: block;
  width: 0;
}

.thought-bubble--active {
  border-color: #10b981;
  box-shadow: 0 0 16px rgba(16, 185, 129, 0.2);
}

.bubble-title {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
}

.bubble-text {
  font-size: 12px;
  color: #a1a1aa;
  line-height: 1.4;
}

.btn-approve {
  margin-top: 8px;
  align-self: flex-start;
  animation: pulse 1.5s infinite;
}

.desk-unit {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-bottom: 12px;
}

.avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #27272a;
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  transition: all var(--transition);
}

.avatar--thinking {
  border-color: #f59e0b;
  box-shadow: 0 0 12px rgba(245, 158, 11, 0.4);
  animation: bounce 1s infinite alternate;
}

.avatar--executing_tool {
  border-color: #3b82f6;
  box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
  animation: shake 0.5s infinite;
}

.avatar--waiting_approval {
  border-color: #ef4444;
  box-shadow: 0 0 16px rgba(239, 68, 68, 0.5);
}

@keyframes bounce {
  from { transform: translateY(0); }
  to { transform: translateY(-4px); }
}

@keyframes shake {
  0% { transform: rotate(-3deg); }
  50% { transform: rotate(3deg); }
  100% { transform: rotate(-3deg); }
}

.desk-furniture {
  font-size: 24px;
}

.station-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.station-role {
  font-size: 11px;
  font-weight: 700;
  color: #71717a;
  letter-spacing: 0.5px;
}

.badge--thinking {
  background: rgba(245, 158, 11, 0.12);
  color: #f59e0b;
  border-color: rgba(245, 158, 11, 0.3);
}

.badge--tool {
  background: rgba(59, 130, 246, 0.12);
  color: #60a5fa;
  border-color: rgba(59, 130, 246, 0.3);
}

.badge--warn {
  background: rgba(239, 68, 68, 0.14);
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.4);
}

.badge--idle {
  background: rgba(161, 161, 170, 0.1);
  color: #a1a1aa;
}

/* ── PAPERCLIP TREE ── */
.paperclip-container {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
  display: flex;
  justify-content: center;
}

.tree-root {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 900px;
  width: 100%;
}

.tree-node {
  background: #141417;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 18px 22px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: all var(--transition);
}

.node-director {
  width: 380px;
  border-color: rgba(16, 185, 129, 0.4);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.tree-line-down {
  width: 2px;
  height: 36px;
  background: #27272a;
}

.tree-branches {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  width: 100%;
}

.node-specialist {
  border-color: var(--border);
}

.node-badge {
  font-size: 10px;
  font-weight: 700;
  color: #10b981;
  text-transform: uppercase;
}

.node-title {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}

.node-desc {
  font-size: 12px;
  color: #a1a1aa;
  line-height: 1.4;
}

.node-tools {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.tool-tag {
  font-size: 10px;
  background: #1f1f23;
  padding: 2px 6px;
  border-radius: 4px;
  color: #d4d4d8;
}

.subagent-tag {
  font-size: 11px;
  color: #a855f7;
  margin-top: 8px;
  font-weight: 600;
}

/* ── TIMELINE ── */
.timeline-container {
  flex: 1;
  padding: 24px 32px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 860px;
  margin: 0 auto;
  width: 100%;
}

.timeline-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.timeline-header h3 {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}

.events-count {
  font-size: 12px;
  color: #71717a;
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.event-card {
  background: #121215;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-family: 'Inter', sans-serif;
}

.event-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 11px;
}

.event-time { color: #71717a; }
.event-agent { font-weight: 600; color: #fff; }

.event-type-badge {
  text-transform: uppercase;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 700;
}

.event-card--thought { border-left: 3px solid #f59e0b; }
.event-card--thought .event-type-badge { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }

.event-card--tool_call { border-left: 3px solid #3b82f6; }
.event-card--tool_call .event-type-badge { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }

.event-card--tool_result { border-left: 3px solid #10b981; }
.event-card--tool_result .event-type-badge { background: rgba(16, 185, 129, 0.15); color: #34d399; }

.event-card--approval_request { border-left: 3px solid #ef4444; background: rgba(239, 68, 68, 0.05); }
.event-card--approval_request .event-type-badge { background: #ef4444; color: #fff; }

.event-content {
  font-size: 13px;
  color: #e4e4e7;
  line-height: 1.45;
}

.engine-pills {
  display: flex;
  align-items: center;
  gap: 8px;
}

.engine-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 9999px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.engine-badge--claw {
  background: rgba(16, 185, 129, 0.12);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.engine-badge--bot {
  background: rgba(168, 85, 247, 0.12);
  color: #c084fc;
  border: 1px solid rgba(168, 85, 247, 0.3);
}
</style>
