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



const showPairModal = ref(false)
const pairLoading = ref(false)
const pairData = ref(null)
const pairCountdown = ref(120)
let pairTimer = null

async function openPairModal() {
  showPairModal.value = true
  await fetchPairQr()
}

async function fetchPairQr() {
  pairLoading.value = true
  try {
    const res = await api.get('/v1/openbot/pair')
    pairData.value = res.data
    pairCountdown.value = 120
    if (pairTimer) clearInterval(pairTimer)
    pairTimer = setInterval(() => {
      if (pairCountdown.value > 0) pairCountdown.value--
      else clearInterval(pairTimer)
    }, 1000)
  } catch (e) {
    alert('Erro ao gerar pareamento OpenBot: ' + e.message)
  } finally {
    pairLoading.value = false
  }
}

const showNewAgentModal = ref(false)
const newAgentSaving = ref(false)
const agentForm = ref({
  agent_id: '',
  client_id: 'cli_mkos_saas',
  name: '',
  role: 'support_and_sales',
  system_prompt: '',
  model: 'gemini-2.0-flash',
  tools_allowed_text: 'search_catalog, check_order_status, send_pix_charge',
  monthly_spend_limit_usd: 25.0
})

const presetTemplates = [
  {
    icon: 'VENDAS',
    title: 'Atendimento & Vendas 24/7',
    desc: 'Atendimento humanizado, qualificação de leads, catálogo e links Pix.',
    role: 'support_and_sales',
    defaultName: 'Clara - Vendas WhatsApp',
    model: 'gemini-2.0-flash',
    tools: 'search_catalog, check_order_status, send_pix_charge',
    prompt: 'Você é a Clara, especialista em atendimento e vendas no WhatsApp. Seja acolhedora, recomende produtos e ajude no fechamento de pedidos com pagamento Pix.'
  },
  {
    icon: 'OPS',
    title: 'Operações & No-Show',
    desc: 'Monitora agendamentos, envia lembretes interativos e previne faltas.',
    role: 'operations_mkos',
    defaultName: 'MKOS - Gestor de Presença',
    model: 'gemini-2.0-flash',
    tools: 'sync_mural_n8n, check_no_show, send_whatsapp_reminder',
    prompt: 'Você é o especialista de operações MKOS. Monitore consultas e agendamentos nas próximas 24 horas, confirmando presença e reagendando faltas de forma proativa.'
  },
  {
    icon: 'FIN',
    title: 'Cobrança & Régua Financeira',
    desc: 'Régua preventiva de vencimento, recuperação amigável e 2ª via de boleto/Pix.',
    role: 'billing_finance',
    defaultName: 'May - Cobrança & Finanças',
    model: 'gemini-2.0-flash',
    tools: 'query_due_invoices, generate_pix_qr, send_whatsapp_template',
    prompt: 'Você é a May, responsável pela régua de relacionamento financeiro. Conduza conversas empáticas para regularização de parcelas, emissão de boletos e Pix sem constrangimentos.'
  },
  {
    icon: 'RAG',
    title: 'Suporte Técnico & Base RAG',
    desc: 'Tira dúvidas em manuais técnicos, PDFs de seguradoras ou documentação de sistemas.',
    role: 'technical_support',
    defaultName: 'Sara - Suporte Especializado',
    model: 'claude-3-7-sonnet',
    tools: 'query_knowledge_base, inspect_system_logs, escalate_to_human',
    prompt: 'Você é a Sara, assistente técnica de nível 2. Responda com base estrita na base de conhecimento oficial e manuais, escalando para humanos quando necessário.'
  },
  {
    icon: 'UGC',
    title: 'Conteúdo UGC & Vídeos Cinematográficos',
    desc: 'Roteiros persuasivos, renderização Remotion 9:16 e injeção na galeria.',
    role: 'content_creator',
    defaultName: 'Leo - Produtor UGC',
    model: 'gemini-2.0-flash',
    tools: 'generate_remotion_video, inject_android_gallery, send_whatsapp_media',
    prompt: 'Você cria roteiros e vídeos curtos cinematográficos para Instagram Reels, TikTok e WhatsApp Status.'
  },
  {
    icon: 'MOB',
    title: 'Operador de Celular Android (Anti-Ban)',
    desc: 'Automação mecânica no app nativo: swipes orgânicos, visualização de stories e postagens.',
    role: 'android_operator',
    defaultName: 'Alex - Operador Mobile',
    model: 'gemini-2.0-flash',
    tools: 'android_swipe, android_tap, android_screenshot, rotate_mobile_proxy',
    prompt: 'Você opera o smartphone Android de forma humanizada, simulando rolagem com pausas de leitura e prevenindo bloqueios de algoritmos.'
  }
]

function openCreateModal(preset = null) {
  if (preset) {
    agentForm.value.role = preset.role
    agentForm.value.name = preset.defaultName
    agentForm.value.model = preset.model
    agentForm.value.tools_allowed_text = preset.tools
    agentForm.value.system_prompt = preset.prompt
    agentForm.value.agent_id = 'agt_' + preset.role + '_' + Math.random().toString(36).substring(2, 6)
  } else {
    agentForm.value.role = 'support_and_sales'
    agentForm.value.name = 'Novo Agente Especialista'
    agentForm.value.model = 'gemini-2.0-flash'
    agentForm.value.tools_allowed_text = 'search_catalog, send_pix_charge'
    agentForm.value.system_prompt = 'Você é um assistente operacional autônomo.'
    agentForm.value.agent_id = 'agt_custom_' + Math.random().toString(36).substring(2, 6)
  }
  showNewAgentModal.value = true
}

async function saveAgent() {
  if (!agentForm.value.name || !agentForm.value.agent_id) {
    alert('Preencha o nome e o identificador do agente.')
    return
  }
  newAgentSaving.value = true
  try {
    const tools = agentForm.value.tools_allowed_text
      .split(',')
      .map(t => t.trim())
      .filter(Boolean)

    const payload = {
      agent_id: agentForm.value.agent_id,
      client_id: agentForm.value.client_id,
      name: agentForm.value.name,
      role: agentForm.value.role,
      system_prompt: agentForm.value.system_prompt,
      model: agentForm.value.model,
      tools_allowed: tools,
      memory_namespace: agentForm.value.client_id + '_' + agentForm.value.role,
      status: 'idle',
      current_thought: 'Agente operacional criado e pronto para novas tarefas.'
    }

    await api.post('/v1/agents', payload)
    showNewAgentModal.value = false
    await fetchInitialState()
    alert(`Agente '${agentForm.value.name}' adicionado à equipe com sucesso!`)
  } catch (err) {
    alert('Erro ao salvar agente: ' + (err.response?.data?.detail || err.message))
  } finally {
    newAgentSaving.value = false
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
             Escritório Virtual (Habblaud)
          </button>
          <button class="subtab-btn" :class="{ active: activeSubTab === 'paperclip' }" @click="activeSubTab = 'paperclip'">
            📎 Hierarquia Paperclip
          </button>
          <button class="subtab-btn" :class="{ active: activeSubTab === 'builder' }" @click="activeSubTab = 'builder'">
             Equipe Operacional (Criar Agentes)
          </button>
          <button class="subtab-btn" :class="{ active: activeSubTab === 'timeline' }" @click="activeSubTab = 'timeline'">
            ⚡ OpenBot Runtime (Manus Trace)
          </button>
        </div>

        <div class="engine-pills">
          <span class="engine-badge engine-badge--claw">
            <span class="pulse-dot"></span>
            OpenClaw Engine
          </span>
          <span class="engine-badge engine-badge--bot">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
            OpenBot Gateway
          </span>
          <div class="budget-pill">
            <span class="budget-label">Limite Mensal:</span>
            <span class="budget-val font-mono">US$ {{ currentClient.budget_current_usd?.toFixed(2) }} / {{ currentClient.budget_monthly_usd?.toFixed(2) }}</span>
            <span class="budget-dot" />
          </div>
        </div>
      </div>

      <div class="topbar-right">
        <button class="btn btn--small btn--primary" @click="openPairModal()">
           Parear OpenBot
        </button>
        <button class="btn btn--small btn--accent-outline" @click="openCreateModal()">
          + Criar Agente
        </button>
        <button class="btn btn--small btn--accent-outline" :disabled="!!dispatchLoading" @click="dispatchAction('create_and_send_reel')">
          <span v-if="dispatchLoading === 'create_and_send_reel'" class="spinner" />
           Criar Reel (Leo)
        </button>
        <button class="btn btn--small btn--accent-outline" :disabled="!!dispatchLoading" @click="dispatchAction('organic_warmup')">
          <span v-if="dispatchLoading === 'organic_warmup'" class="spinner" />
           Aquecimento Anti-Ban
        </button>
        <button class="btn btn--small" :disabled="!!dispatchLoading" @click="dispatchAction('no_show_reminder')">
          <span v-if="dispatchLoading === 'no_show_reminder'" class="spinner" />
           Checar No-Show
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
            <span class="bubble-title"> {{ leoAgent.name }}</span>
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
              <span class="avatar-face"></span>
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
              <span class="computer-screen"></span>
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
              <span class="avatar-face"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8V4H8"></path><rect width="16" height="12" x="4" y="8" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path></svg></span>
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
              <span v-for="t in leoAgent.tools_allowed" :key="t" class="tool-tag"> {{ t }}</span>
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
            <span class="event-agent">{{ ev.agent_id }}</span>
            <span class="event-type-badge">{{ ev.type }}</span>
          </div>
          <div class="event-content">{{ ev.content }}</div>
        </div>
      </div>
    </div>

    <!-- CONTENT VIEW 4: AGENT STUDIO / EQUIPE OPERACIONAL -->
    <div v-else-if="activeSubTab === 'builder'" class="builder-container">
      <div class="builder-header">
        <div>
          <h3> Studio de Agentes & Equipes Operacionais</h3>
          <p class="builder-desc">Gerencie e crie equipes de funcionários digitais customizados por cliente e operação.</p>
        </div>
        <button class="btn btn--primary" @click="openCreateModal()">
          + Novo Agente Operacional
        </button>
      </div>

      <!-- Presets Operacionais -->
      <div class="presets-section">
        <h4 class="section-title"> Criar a Partir de um Modelo Especialista</h4>
        <div class="presets-grid">
          <div
            v-for="(p, pIdx) in presetTemplates"
            :key="pIdx"
            class="preset-card"
            @click="openCreateModal(p)"
          >
            <div class="preset-card-head">
              <span class="preset-icon">{{ p.icon }}</span>
              <span class="preset-badge">{{ p.role }}</span>
            </div>
            <h5>{{ p.title }}</h5>
            <p>{{ p.desc }}</p>
            <div class="preset-footer">
              <span class="preset-model-tag"> {{ p.model }}</span>
              <button class="btn btn--small btn--primary">Configurar</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Agentes Ativos na Operação -->
      <div class="roster-section">
        <div class="roster-head">
          <h4 class="section-title"> Equipe em Operação ({{ agents.length }} Agentes Ativos)</h4>
          <span class="client-scope-tag"> Cliente: {{ currentClient.client_name }}</span>
        </div>

        <div class="roster-grid">
          <div v-for="agent in agents" :key="agent.agent_id" class="roster-card">
            <div class="roster-card-header">
              <div class="roster-avatar"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8V4H8"></path><rect width="16" height="12" x="4" y="8" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path></svg></div>
              <div class="roster-main-info">
                <h5>{{ agent.name }}</h5>
                <span class="roster-role-badge">{{ agent.role }}</span>
              </div>
              <span class="roster-status-pill" :class="`roster-status-pill--${agent.status}`">
                {{ agent.status }}
              </span>
            </div>

            <div class="roster-card-body">
              <div class="roster-meta-row">
                <span class="meta-label">Modelo:</span>
                <span class="meta-value font-mono">{{ agent.model }}</span>
              </div>
              <div class="roster-meta-row">
                <span class="meta-label">ID do Agente:</span>
                <span class="meta-value font-mono">{{ agent.agent_id }}</span>
              </div>
              <div class="roster-meta-row">
                <span class="meta-label">Pensamento Atual:</span>
                <span class="meta-value thought-preview">{{ agent.current_thought }}</span>
              </div>
              <div class="roster-tools">
                <span v-for="t in agent.tools_allowed" :key="t" class="tool-chip"> {{ t }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODAL: CRIAR / CONFIGURAR AGENTE OPERACIONAL -->
    <div v-if="showNewAgentModal" class="modal-overlay" @click.self="showNewAgentModal = false">
      <div class="agent-modal">
        <div class="modal-header">
          <h4> Novo Agente da Equipe Operacional</h4>
          <button class="close-btn" @click="showNewAgentModal = false">✕</button>
        </div>

        <div class="modal-body">
          <div class="form-group">
            <label>Cliente / Conta:</label>
            <select v-model="agentForm.client_id" class="form-input">
              <option value="cli_mkos_saas">MKOS SaaS / Operações Globais</option>
              <option value="cli_cosmeticos_natural_01">Loja Cosméticos da Terra</option>
              <option value="cli_clinica_medica">Clínica Médica & Estética</option>
              <option value="cli_corretora_seguros">Corretora de Seguros (MayTech Model)</option>
            </select>
          </div>

          <div class="form-row">
            <div class="form-group flex-1">
              <label>Nome do Agente:</label>
              <input v-model="agentForm.name" class="form-input" placeholder="Ex: Clara - Atendimento & Vendas" />
            </div>
            <div class="form-group flex-1">
              <label>Identificador Único (agent_id):</label>
              <input v-model="agentForm.agent_id" class="form-input font-mono" placeholder="Ex: agt_vendas_01" />
            </div>
          </div>

          <div class="form-row">
            <div class="form-group flex-1">
              <label>Papel Operacional (Role):</label>
              <select v-model="agentForm.role" class="form-input">
                <option value="support_and_sales"> Atendimento & Vendas (WhatsApp)</option>
                <option value="operations_mkos"> Operações & No-Show</option>
                <option value="billing_finance"> Cobrança & Régua Financeira</option>
                <option value="technical_support"> Suporte Técnico & Base RAG</option>
                <option value="content_creator"> Conteúdo UGC & Vídeos Cinematográficos</option>
                <option value="android_operator"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8V4H8"></path><rect width="16" height="12" x="4" y="8" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path></svg> Operador de Celular Android (Anti-Ban)</option>
              </select>
            </div>

            <div class="form-group flex-1">
              <label>Modelo de Inteligência Artificial:</label>
              <select v-model="agentForm.model" class="form-input">
                <option value="gemini-2.0-flash">Gemini 2.0 Flash (Alta Velocidade / Custo Baixo)</option>
                <option value="claude-3-7-sonnet">Claude 3.7 Sonnet (Raciocínio & RAG Profundo)</option>
                <option value="deepseek-chat">DeepSeek-V3 (Econômico & Preciso)</option>
              </select>
            </div>
          </div>

          <div class="form-group">
            <label>Instrução do Sistema (System Prompt / Tom de Voz):</label>
            <textarea
              v-model="agentForm.system_prompt"
              rows="4"
              class="form-input textarea"
              placeholder="Defina a personalidade, as regras de atendimento e os objetivos operacionais..."
            />
          </div>

          <div class="form-group">
            <label>Ferramentas Permitidas (separadas por vírgula):</label>
            <input
              v-model="agentForm.tools_allowed_text"
              class="form-input font-mono"
              placeholder="ex: search_catalog, check_order_status, send_pix_charge"
            />
            <span class="form-hint">O OpenBot Security Gateway bloqueia qualquer ação que não conste nesta lista.</span>
          </div>

          <div class="form-group">
            <label>Teto de Gastos Mensal (Kill-Switch em USD):</label>
            <input
              v-model.number="agentForm.monthly_spend_limit_usd"
              type="number"
              step="5"
              class="form-input"
              style="width: 160px;"
            />
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn btn--muted" @click="showNewAgentModal = false">Cancelar</button>
          <button class="btn btn--primary" :disabled="newAgentSaving" @click="saveAgent">
            <span v-if="newAgentSaving" class="spinner" />
            Adicionar Agente à Equipe
          </button>
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

/* ── Pulse dot for badge ── */
.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 9999px;
  background: #10b981;
  display: inline-block;
  box-shadow: 0 0 6px #10b981;
}

/* ── Mobile Optimization for Habblaud ── */
@media (max-width: 768px) {
  .habblaud-wrapper {
    height: auto;
    min-height: 100%;
    overflow-y: auto;
  }
  .habblaud-topbar {
    padding: 10px 12px;
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .topbar-left {
    width: 100%;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .subtab-pills {
    width: 100%;
    overflow-x: auto;
    white-space: nowrap;
    -webkit-overflow-scrolling: touch;
    padding: 3px;
  }
  .subtab-btn {
    padding: 7px 12px;
    font-size: 11px;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
  .engine-pills {
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .topbar-right {
    width: 100%;
    overflow-x: auto;
    white-space: nowrap;
    -webkit-overflow-scrolling: touch;
    display: flex;
    gap: 6px;
    padding-bottom: 4px;
  }
  .topbar-right .btn {
    white-space: nowrap;
    font-size: 11px;
    padding: 6px 10px;
  }
  .office-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding: 12px 6px;
  }
  .office-floor {
    min-width: 620px;
  }
  .builder-container {
    padding: 12px;
    gap: 16px;
  }
  .presets-grid {
    grid-template-columns: 1fr;
  }
  .roster-grid {
    grid-template-columns: 1fr;
  }
  .agent-modal {
    max-width: 95vw;
    margin: 10px;
  }
  .form-row {
    flex-direction: column;
    gap: 10px;
  }
}

</style>


/* ── AGENT STUDIO / BUILDER ── */
.builder-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px;
  gap: 24px;
  overflow-y: auto;
}

.builder-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid var(--border);
  padding-bottom: 16px;
}

.builder-header h3 {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 4px;
}

.builder-desc {
  font-size: 13px;
  color: var(--fg-muted);
}

.section-title {
  font-size: 14px;
  font-weight: 700;
  color: #a1a1aa;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 12px;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.preset-card {
  background: #141417;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all var(--transition);
  display: flex;
  flex-direction: column;
}

.preset-card:hover {
  border-color: #10b981;
  transform: translateY(-2px);
  background: #18181b;
}

.preset-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.preset-icon {
  font-size: 24px;
}

.preset-badge {
  font-size: 10px;
  background: #27272a;
  color: #a1a1aa;
  padding: 2px 8px;
  border-radius: 9999px;
  font-weight: 600;
}

.preset-card h5 {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 6px;
}

.preset-card p {
  font-size: 12px;
  color: #71717a;
  line-height: 1.4;
  flex: 1;
  margin-bottom: 12px;
}

.preset-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 10px;
}

.preset-model-tag {
  font-size: 11px;
  color: #10b981;
  font-weight: 600;
}

/* Roster Section */
.roster-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.client-scope-tag {
  font-size: 12px;
  background: rgba(16, 185, 129, 0.1);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.25);
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 600;
}

.roster-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.roster-card {
  background: #121215;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.roster-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.roster-avatar {
  width: 38px;
  height: 38px;
  background: #27272a;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.roster-main-info {
  flex: 1;
}

.roster-main-info h5 {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 2px;
}

.roster-role-badge {
  font-size: 11px;
  color: #a1a1aa;
}

.roster-status-pill {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 9999px;
  text-transform: uppercase;
}

.roster-status-pill--idle { background: rgba(16, 185, 129, 0.15); color: #34d399; }
.roster-status-pill--thinking { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.roster-status-pill--executing_tool { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
.roster-status-pill--waiting_approval { background: rgba(239, 68, 68, 0.2); color: #f87171; }

.roster-meta-row {
  display: flex;
  font-size: 12px;
  margin-bottom: 4px;
  gap: 6px;
}

.meta-label {
  color: #71717a;
  min-width: 90px;
}

.meta-value {
  color: #e4e4e7;
}

.thought-preview {
  font-style: italic;
  color: #a1a1aa;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.roster-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 8px;
}

.tool-chip {
  font-size: 10px;
  background: #1e1e24;
  color: #a1a1aa;
  padding: 2px 7px;
  border-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

/* ── MODAL AGENT ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.agent-modal {
  background: #18181b;
  border: 1px solid var(--border);
  border-radius: 16px;
  width: 100%;
  max-width: 620px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
  background: #141417;
}

.modal-header h4 {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}

.close-btn {
  background: transparent;
  border: none;
  color: #71717a;
  font-size: 18px;
  cursor: pointer;
}

.close-btn:hover {
  color: #fff;
}

.modal-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 70vh;
  overflow-y: auto;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: #a1a1aa;
}

.form-input {
  background: #09090b;
  border: 1px solid var(--border);
  color: #fff;
  padding: 9px 12px;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
}

.form-input:focus {
  border-color: #10b981;
}

.form-row {
  display: flex;
  gap: 14px;
}

.flex-1 { flex: 1; }

.textarea {
  resize: vertical;
}

.form-hint {
  font-size: 11px;
  color: #71717a;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid var(--border);
  background: #141417;
}
