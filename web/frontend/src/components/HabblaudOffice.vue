<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import api from '../api'

const activeSubTab = ref('habblaud') // 'habblaud', 'paperclip', 'timeline', 'builder'
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

// ── OPENBOT INTEGRATION & PAIRING ──
const showPairModal = ref(false)
const pairLoading = ref(false)
const pairData = ref(null)
const pairCountdown = ref(120)
const pairCopiedKey = ref('')
const currentQrMode = ref('url') // 'url' (câmera) ou 'ticket' (openbot app)
let pairTimer = null

function openOpenBotSite() {
  window.open('https://openbot.run', '_blank')
}

async function openPairModal() {
  showPairModal.value = true
  await fetchPairQr(currentQrMode.value)
}

async function switchQrMode(mode) {
  currentQrMode.value = mode
  await fetchPairQr(mode)
}

async function fetchPairQr(mode = currentQrMode.value) {
  pairLoading.value = true
  try {
    const res = await api.get(`/v1/openbot/pair?qr_mode=${mode}`)
    pairData.value = res.data
    pairCountdown.value = 120
    if (pairTimer) clearInterval(pairTimer)
    pairTimer = setInterval(() => {
      if (pairCountdown.value > 0) pairCountdown.value--
      else clearInterval(pairTimer)
    }, 1000)
  } catch (e) {
    console.error('Erro ao buscar pareamento da API:', e)
    const token = 'openbot_' + Math.random().toString(36).substring(2, 10)
    pairData.value = {
      status: 'ok',
      qr_mode: mode,
      connect_url: `http://${location.hostname || '169.58.27.192'}/api/v1/openbot/connect?token=${token}`,
      pair_payload: {
        v: 1,
        app: 'MKOS Agent Fleet',
        api: `http://${location.hostname || '169.58.27.192'}/api/v1`,
        ws: `ws://${location.hostname || '169.58.27.192'}/ws/operations/live`,
        token: token,
        mcp_endpoint: `http://${location.hostname || '169.58.27.192'}/api/v1/openbot/mcp-config`
      }
    }
  } finally {
    pairLoading.value = false
  }
}

function copyText(val, key = 'token') {
  if (!val) return
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(val).then(() => {
      pairCopiedKey.value = key
      setTimeout(() => { pairCopiedKey.value = '' }, 2500)
    }).catch(() => {
      prompt('Copie o valor:', val)
    })
  } else {
    prompt('Copie o valor:', val)
  }
}

// ── AGENT STUDIO ──
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
    code: 'VENDAS',
    title: 'Atendimento & Vendas 24/7',
    desc: 'Atendimento humanizado, qualificação de leads, catálogo e links Pix.',
    role: 'support_and_sales',
    defaultName: 'Clara - Vendas WhatsApp',
    model: 'gemini-2.0-flash',
    tools: 'search_catalog, check_order_status, send_pix_charge',
    prompt: 'Você é a Clara, especialista em atendimento e vendas no WhatsApp. Seja acolhedora, recomende produtos e ajude no fechamento de pedidos com pagamento Pix.'
  },
  {
    code: 'OPS',
    title: 'Operações & No-Show',
    desc: 'Monitora agendamentos, envia lembretes interativos e previne faltas.',
    role: 'operations_mkos',
    defaultName: 'MKOS - Gestor de Presença',
    model: 'gemini-2.0-flash',
    tools: 'sync_mural_n8n, check_no_show, send_whatsapp_reminder',
    prompt: 'Você é o especialista de operações MKOS. Monitore consultas e agendamentos nas próximas 24 horas, confirmando presença e reagendando faltas de forma proativa.'
  },
  {
    code: 'FIN',
    title: 'Cobrança & Régua Financeira',
    desc: 'Régua preventiva de vencimento, recuperação amigável e 2ª via de boleto/Pix.',
    role: 'billing_finance',
    defaultName: 'May - Cobrança & Finanças',
    model: 'gemini-2.0-flash',
    tools: 'query_due_invoices, generate_pix_qr, send_whatsapp_template',
    prompt: 'Você é a May, responsável pela régua de relacionamento financeiro. Conduza conversas empáticas para regularização de parcelas, emissão de boletos e Pix sem constrangimentos.'
  },
  {
    code: 'RAG',
    title: 'Suporte Técnico & Base RAG',
    desc: 'Tira dúvidas em manuais técnicos, PDFs de seguradoras ou documentação de sistemas.',
    role: 'technical_support',
    defaultName: 'Sara - Suporte Especializado',
    model: 'claude-3-7-sonnet',
    tools: 'query_knowledge_base, inspect_system_logs, escalate_to_human',
    prompt: 'Você é a Sara, assistente técnica de nível 2. Responda com base estrita na base de conhecimento oficial e manuais, escalando para humanos quando necessário.'
  },
  {
    code: 'UGC',
    title: 'Conteúdo UGC & Vídeos Cinematográficos',
    desc: 'Roteiros persuasivos, renderização Remotion 9:16 e injeção na galeria.',
    role: 'content_creator',
    defaultName: 'Leo - Produtor UGC',
    model: 'gemini-2.0-flash',
    tools: 'generate_remotion_video, inject_android_gallery, send_whatsapp_media',
    prompt: 'Você cria roteiros e vídeos curtos cinematográficos para Instagram Reels, TikTok e WhatsApp Status.'
  },
  {
    code: 'MOB',
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
  if (pairTimer) clearInterval(pairTimer)
  if (socket) {
    socket.onclose = null
    socket.close()
  }
})

function getAgentByRole(role) {
  return agents.value.find(a => a.role === role) || {
    name: 'Agente',
    status: 'idle',
    current_thought: 'Aguardando tarefas...',
    tools_allowed: []
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
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2"></rect>
              <line x1="3" y1="9" x2="21" y2="9"></line>
              <line x1="9" y1="21" x2="9" y2="9"></line>
            </svg>
            <span>Escritório Virtual</span>
          </button>

          <button class="subtab-btn" :class="{ active: activeSubTab === 'builder' }" @click="activeSubTab = 'builder'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            <span>Equipe Operacional</span>
          </button>

          <button class="subtab-btn" :class="{ active: activeSubTab === 'paperclip' }" @click="activeSubTab = 'paperclip'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
            </svg>
            <span>Hierarquia Paperclip</span>
          </button>

          <button class="subtab-btn" :class="{ active: activeSubTab === 'timeline' }" @click="activeSubTab = 'timeline'">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
            <span>OpenBot Runtime</span>
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
        <!-- Direct OpenBot Web Portal Link -->
        <button class="btn btn--small btn--primary" @click="openOpenBotSite" title="Abrir portal oficial openbot.run em nova aba">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
          <span>Abrir openbot.run</span>
        </button>

        <!-- Pair Mobile App Modal Trigger -->
        <button class="btn btn--small btn--accent" @click="openPairModal()" title="Parear celular Android via QR Code e Gateway MCP">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
          <span>Parear Celular</span>
        </button>

        <button class="btn btn--small btn--accent-outline" @click="openCreateModal()">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          <span>Criar Agente</span>
        </button>

        <button class="btn btn--small btn--accent-outline" :disabled="!!dispatchLoading" @click="dispatchAction('create_and_send_reel')">
          <span v-if="dispatchLoading === 'create_and_send_reel'" class="spinner" />
          <span>Criar Reel (Leo)</span>
        </button>

        <button class="btn btn--small btn--accent-outline" :disabled="!!dispatchLoading" @click="dispatchAction('organic_warmup')">
          <span v-if="dispatchLoading === 'organic_warmup'" class="spinner" />
          <span>Aquecimento Anti-Ban</span>
        </button>

        <button class="btn btn--small" :disabled="!!dispatchLoading" @click="dispatchAction('no_show_reminder')">
          <span v-if="dispatchLoading === 'no_show_reminder'" class="spinner" />
          <span>Checar No-Show</span>
        </button>
      </div>
    </header>

    <!-- CONTENT VIEW 1: HABBLAUD VIRTUAL OFFICE -->
    <div v-if="activeSubTab === 'habblaud'" class="office-container">
      <div class="office-floor">
        <!-- Station 1: Agente Diretor (Supervisor Geral) -->
        <div class="workstation station-director">
          <div class="thought-bubble" :class="{ 'thought-bubble--active': directorAgent.status !== 'idle' }">
            <span class="bubble-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
              {{ directorAgent.name }}
            </span>
            <p class="bubble-text">{{ directorAgent.current_thought }}</p>
          </div>

          <div class="desk-unit">
            <div class="avatar avatar--director" :class="`avatar--${directorAgent.status}`">
              <span class="avatar-face">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle></svg>
              </span>
            </div>
            <div class="desk-furniture">
              <span class="computer-screen">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
              </span>
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
            <span class="bubble-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>
              {{ leoAgent.name }}
            </span>
            <p class="bubble-text">{{ leoAgent.current_thought }}</p>
            <button
              v-if="leoAgent.status === 'waiting_approval' && activeOp"
              class="btn btn--small btn--primary btn-approve"
              :disabled="approveLoading"
              @click="approveCurrentOp(activeOp.task_id)"
            >
              <span v-if="approveLoading" class="spinner" />
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
              Aprovar Postagem
            </button>
          </div>

          <div class="desk-unit">
            <div class="avatar avatar--leo" :class="`avatar--${leoAgent.status}`">
              <span class="avatar-face">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"></polygon><rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect></svg>
              </span>
            </div>
            <div class="desk-furniture">
              <span class="computer-screen">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
              </span>
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
            <span class="bubble-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
              {{ claraAgent.name }}
            </span>
            <p class="bubble-text">{{ claraAgent.current_thought }}</p>
          </div>

          <div class="desk-unit">
            <div class="avatar avatar--clara" :class="`avatar--${claraAgent.status}`">
              <span class="avatar-face">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
              </span>
            </div>
            <div class="desk-furniture">
              <span class="computer-screen">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>
              </span>
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
            <span class="bubble-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
              {{ mkosAgent.name }}
            </span>
            <p class="bubble-text">{{ mkosAgent.current_thought }}</p>
          </div>

          <div class="desk-unit">
            <div class="avatar avatar--mkos" :class="`avatar--${mkosAgent.status}`">
              <span class="avatar-face">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"></path><rect width="16" height="12" x="4" y="8" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path></svg>
              </span>
            </div>
            <div class="desk-furniture">
              <span class="computer-screen">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
              </span>
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
            <span v-for="t in directorAgent.tools_allowed" :key="t" class="tool-tag">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
              {{ t }}
            </span>
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
              <span v-for="t in leoAgent.tools_allowed" :key="t" class="tool-tag">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
                {{ t }}
              </span>
            </div>
            <div class="subagent-tag">↳ Dispara Subagentes Efêmeros (Remotion concurrency=1)</div>
          </div>

          <div class="tree-node node-specialist">
            <div class="node-badge">NÍVEL 2: ATENDIMENTO</div>
            <h4 class="node-title">{{ claraAgent.name }}</h4>
            <p class="node-desc">{{ claraAgent.system_prompt }}</p>
            <div class="node-tools">
              <span v-for="t in claraAgent.tools_allowed" :key="t" class="tool-tag">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
                {{ t }}
              </span>
            </div>
            <div class="subagent-tag">↳ Memória isolada por client_id (LGPD)</div>
          </div>

          <div class="tree-node node-specialist">
            <div class="node-badge">NÍVEL 2: OPERAÇÕES MKOS</div>
            <h4 class="node-title">{{ mkosAgent.name }}</h4>
            <p class="node-desc">{{ mkosAgent.system_prompt }}</p>
            <div class="node-tools">
              <span v-for="t in mkosAgent.tools_allowed" :key="t" class="tool-tag">
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
                {{ t }}
              </span>
            </div>
            <div class="subagent-tag">↳ Conexão direta com Mural n8n da produção</div>
          </div>
        </div>
      </div>
    </div>

    <!-- CONTENT VIEW 3: OPENBOT RUNTIME (MANUS TRACE) -->
    <div v-else-if="activeSubTab === 'timeline'" class="timeline-container">
      <!-- OpenBot Hub Banner -->
      <div class="openbot-banner">
        <div class="openbot-banner-left">
          <div class="openbot-logo-badge">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>
          </div>
          <div>
            <h4>OpenBot Mobile Runtime & MCP Gateway</h4>
            <p>Gerenciamento do runtime autônomo conectando smartphones Android físicos e emulados via Model Context Protocol (MCP) e WebSockets.</p>
          </div>
        </div>
        <div class="openbot-banner-actions">
          <button class="btn btn--small btn--primary" @click="openOpenBotSite">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
            Acessar openbot.run
          </button>
          <button class="btn btn--small btn--accent" @click="openPairModal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect></svg>
            Parear Celular (QR Code)
          </button>
        </div>
      </div>

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
            <span class="event-agent font-mono">{{ ev.agent_id }}</span>
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
          <h3>Studio de Agentes & Equipes Operacionais</h3>
          <p class="builder-desc">Gerencie e crie equipes de funcionários digitais customizados por cliente e operação.</p>
        </div>
        <button class="btn btn--primary" @click="openCreateModal()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          Novo Agente Operacional
        </button>
      </div>

      <!-- Presets Operacionais -->
      <div class="presets-section">
        <h4 class="section-title">Modelos Especialistas Pré-Configurados</h4>
        <div class="presets-grid">
          <div
            v-for="(p, pIdx) in presetTemplates"
            :key="pIdx"
            class="preset-card"
            @click="openCreateModal(p)"
          >
            <div class="preset-card-head">
              <span class="preset-icon font-mono">{{ p.code }}</span>
              <span class="preset-badge">{{ p.role }}</span>
            </div>
            <h5>{{ p.title }}</h5>
            <p>{{ p.desc }}</p>
            <div class="preset-footer">
              <span class="preset-model-tag font-mono">{{ p.model }}</span>
              <button class="btn btn--small btn--primary">Configurar</button>
            </div>
          </div>
        </div>
      </div>

      <!-- Agentes Ativos na Operação -->
      <div class="roster-section">
        <div class="roster-head">
          <h4 class="section-title">Equipe em Operação ({{ agents.length }} Agentes Ativos)</h4>
          <span class="client-scope-tag">Cliente: {{ currentClient.client_name }}</span>
        </div>

        <div class="roster-grid">
          <div v-for="agent in agents" :key="agent.agent_id" class="roster-card">
            <div class="roster-card-header">
              <div class="roster-avatar">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 8V4H8"></path><rect width="16" height="12" x="4" y="8" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 13v2"></path><path d="M9 13v2"></path></svg>
              </div>
              <div class="roster-main-info">
                <h5>{{ agent.name }}</h5>
                <span class="roster-role-badge font-mono">{{ agent.role }}</span>
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
                <span v-for="t in agent.tools_allowed" :key="t" class="tool-chip">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
                  {{ t }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── TELEPORT MODAL: PAREAR OPENBOT MOBILE ── -->
    <Teleport to="body">
      <div v-if="showPairModal" class="modal-overlay" @click.self="showPairModal = false">
        <div class="agent-modal pair-modal">
          <div class="modal-header">
            <div class="modal-header-info">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>
              <div>
                <h4>Conectar Celular ao OpenBot Runtime</h4>
                <span class="modal-sub">Pareamento via QR Code & Gateway Model Context Protocol (MCP)</span>
              </div>
            </div>
            <button class="close-btn" @click="showPairModal = false" aria-label="Fechar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="18" x2="18" y2="18"></line></svg>
            </button>
          </div>

          <div class="modal-body pair-modal-body">
            <!-- Mode Selector Tabs -->
            <div class="pair-mode-selector">
              <button
                class="mode-btn"
                :class="{ active: currentQrMode === 'url' }"
                @click="switchQrMode('url')"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
                <span>Câmera do Celular (Recomendado)</span>
              </button>
              <button
                class="mode-btn"
                :class="{ active: currentQrMode === 'ticket' }"
                @click="switchQrMode('ticket')"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2"></rect><line x1="12" y1="18" x2="12.01" y2="18"></line></svg>
                <span>App Oficial OpenBot (Ticket)</span>
              </button>
            </div>

            <!-- Guide: Mode 1 (Camera) -->
            <div v-if="currentQrMode === 'url'" class="pair-guide">
              <div class="pair-step">
                <span class="step-num">1</span>
                <div class="step-content">
                  <strong>Abra a câmera do seu smartphone</strong>
                  <p>Aponte a câmera normal do seu iPhone ou Android diretamente para o QR Code abaixo.</p>
                </div>
              </div>
              <div class="pair-step">
                <span class="step-num">2</span>
                <div class="step-content">
                  <strong>Toque no link que surgir na tela</strong>
                  <p>Aparecerá a notificação para abrir o endereço <em>169.58.27.192</em> no navegador do smartphone.</p>
                </div>
              </div>
              <div class="pair-step">
                <span class="step-num">3</span>
                <div class="step-content">
                  <strong>Controle dos agentes pronto no celular</strong>
                  <p>O painel móvel abrirá instantaneamente sem precisar instalar aplicativos adicionais.</p>
                </div>
              </div>
            </div>

            <!-- Guide: Mode 2 (OpenBot App) -->
            <div v-else class="pair-guide">
              <div class="pair-step">
                <span class="step-num">1</span>
                <div class="step-content">
                  <strong>Abra o aplicativo OpenBot</strong>
                  <p>Inicie o app instalado pelo <a href="https://openbot.run" target="_blank" class="link-openbot">openbot.run</a>.</p>
                </div>
              </div>
              <div class="pair-step">
                <span class="step-num">2</span>
                <div class="step-content">
                  <strong>Selecione 'Scan QR code' no aplicativo</strong>
                  <p>Aponte a câmera interna do OpenBot para o ticket criptográfico abaixo.</p>
                </div>
              </div>
              <div class="pair-step">
                <span class="step-num">3</span>
                <div class="step-content">
                  <strong>Vinculado ao Gateway MCP</strong>
                  <p>O aplicativo autenticará o handshake direto com o runtime.</p>
                </div>
              </div>
            </div>

            <!-- QR Code Card with High Contrast -->
            <div class="pair-qr-card">
              <div v-if="pairLoading" class="qr-placeholder">
                <span class="spinner" style="width: 32px; height: 32px;" />
                <span>Gerando QR Code de alto contraste...</span>
              </div>
              <div v-else-if="pairData?.qr_code_base64" class="qr-content">
                <div class="qr-optical-box">
                  <img :src="pairData.qr_code_base64" class="qr-img" alt="QR Code OpenBot" />
                </div>
                <div class="qr-countdown">
                  <span class="dot-online" />
                  <span>Token válido por: <strong class="font-mono">{{ Math.floor(pairCountdown / 60) }}:{{ (pairCountdown % 60).toString().padStart(2, '0') }}</strong></span>
                </div>
              </div>
              <div v-else class="qr-placeholder">
                <span>Falha ao renderizar QR Code.</span>
                <button class="btn btn--small btn--primary" @click="fetchPairQr(currentQrMode)">Tentar novamente</button>
              </div>
            </div>

            <!-- Direct URL & Manual Parameters -->
            <div class="pair-manual-info">
              <div class="info-group">
                <label>Link Direto de Conexão Móvel (ou abra pelo celular):</label>
                <div class="copy-input-row">
                  <input readonly :value="pairData?.connect_url || 'http://169.58.27.192/api/v1/openbot/connect'" class="form-input font-mono" />
                  <button class="btn btn--small btn--accent" @click="copyText(pairData?.connect_url, 'url')">
                    {{ pairCopiedKey === 'url' ? 'Copiado!' : 'Copiar Link' }}
                  </button>
                  <a :href="pairData?.connect_url" target="_blank" class="btn btn--small btn--primary" style="text-decoration:none; display:inline-flex; align-items:center;">
                    Abrir no Navegador
                  </a>
                </div>
              </div>

              <div class="info-group">
                <label>Token de Sessão:</label>
                <div class="copy-input-row">
                  <input readonly :value="pairData?.pair_payload?.token || 'Gerando...'" class="form-input font-mono" />
                  <button class="btn btn--small btn--accent" @click="copyText(pairData?.pair_payload?.token, 'token')">
                    {{ pairCopiedKey === 'token' ? 'Copiado!' : 'Copiar Token' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer pair-modal-footer">
            <button class="btn btn--small btn--outline" @click="openOpenBotSite">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
              Abrir openbot.run
            </button>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn--small btn--secondary" @click="fetchPairQr">
                Atualizar QR Code
              </button>
              <button class="btn btn--small btn--primary" @click="showPairModal = false">
                Concluído
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ── TELEPORT MODAL: CRIAR / CONFIGURAR AGENTE OPERACIONAL ── -->
    <Teleport to="body">
      <div v-if="showNewAgentModal" class="modal-overlay" @click.self="showNewAgentModal = false">
        <div class="agent-modal">
          <div class="modal-header">
            <h4>Novo Agente da Equipe Operacional</h4>
            <button class="close-btn" @click="showNewAgentModal = false" aria-label="Fechar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="18" x2="18" y2="18"></line></svg>
            </button>
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
                  <option value="support_and_sales">Atendimento & Vendas (WhatsApp)</option>
                  <option value="operations_mkos">Operações & No-Show</option>
                  <option value="billing_finance">Cobrança & Régua Financeira</option>
                  <option value="technical_support">Suporte Técnico & Base RAG</option>
                  <option value="content_creator">Conteúdo UGC & Vídeos Cinematográficos</option>
                  <option value="android_operator">Operador de Celular Android (Anti-Ban)</option>
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
    </Teleport>

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




/* ── OPENBOT BANNER & PAIR MODAL ── */
.openbot-banner {
  background: #121215;
  border: 1px solid rgba(16, 185, 129, 0.25);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}

.openbot-banner-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.openbot-logo-badge {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #10b981;
  flex-shrink: 0;
}

.openbot-banner-left h4 {
  font-size: 15px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 4px;
}

.openbot-banner-left p {
  font-size: 12px;
  color: #a1a1aa;
  max-width: 600px;
  line-height: 1.4;
}

.openbot-banner-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

/* Pair Modal Specifics */
.pair-modal {
  max-width: 580px;
}

.modal-header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modal-header-info h4 {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.modal-sub {
  font-size: 11px;
  color: #a1a1aa;
  display: block;
}

.pair-modal-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 24px;
  max-height: 75vh;
  overflow-y: auto;
}

.pair-guide {
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: #09090b;
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px;
}

.pair-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.step-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #27272a;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #10b981;
  flex-shrink: 0;
}

.step-content strong {
  font-size: 12px;
  color: #f4f4f5;
  display: block;
}

.step-content p {
  font-size: 11px;
  color: #71717a;
  margin-top: 2px;
}

.link-openbot {
  color: #10b981;
  text-decoration: underline;
}

.pair-qr-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #09090b;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}

.qr-img {
  width: 210px;
  height: 210px;
  background: #fff;
  padding: 8px;
  border-radius: 10px;
  display: block;
  margin: 0 auto;
}

.qr-placeholder {
  min-height: 210px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #a1a1aa;
  font-size: 13px;
}

.qr-countdown {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  font-size: 12px;
  color: #a1a1aa;
}

.dot-online {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
}

.pair-manual-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-group label {
  font-size: 11px;
  font-weight: 600;
  color: #a1a1aa;
  margin-bottom: 4px;
  display: block;
}

.copy-input-row {
  display: flex;
  gap: 8px;
}

.copy-input-row input {
  flex: 1;
  background: #09090b;
  border: 1px solid var(--border);
  color: #10b981;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
}

.pair-modal-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  background: #141417;
}

@media (max-width: 768px) {
  .openbot-banner {
    flex-direction: column;
    align-items: stretch;
  }
  .openbot-banner-actions {
    flex-direction: column;
  }
  .pair-modal {
    max-width: 100%;
    margin: 10px;
    border-radius: 12px;
  }
  .pair-modal-footer {
    flex-direction: column;
    gap: 8px;
  }
  .pair-modal-footer button {
    width: 100%;
    justify-content: center;
  }
}


/* ── MODE SELECTOR IN PAIR MODAL ── */
.pair-mode-selector {
  display: flex !important;
  background: #09090b !important;
  padding: 4px !important;
  border-radius: 10px !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  gap: 4px !important;
}

.mode-btn {
  flex: 1 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
  padding: 8px 12px !important;
  background: transparent !important;
  border: none !important;
  color: #a1a1aa !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  border-radius: 6px !important;
  cursor: pointer !important;
  transition: all 0.2s !important;
}

.mode-btn:hover {
  color: #fff !important;
}

.mode-btn.active {
  background: #27272a !important;
  color: #10b981 !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
}

.qr-optical-box {
  background: #ffffff !important;
  padding: 12px !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5) !important;
  display: inline-block !important;
}

.qr-img {
  width: 180px !important;
  height: 180px !important;
  display: block !important;
  margin: 0 auto !important;
  image-rendering: pixelated !important;
}

</style>


<style>
/* ── GLOBAL TELEPORTED MODAL STYLES (Mount to <body>) ── */
.modal-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  inset: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  background: rgba(0, 0, 0, 0.82) !important;
  backdrop-filter: blur(8px) !important;
  -webkit-backdrop-filter: blur(8px) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  z-index: 99999 !important;
  padding: 16px !important;
  box-sizing: border-box !important;
}

.agent-modal {
  background: #18181b !important;
  border: 1px solid rgba(255, 255, 255, 0.15) !important;
  border-radius: 16px !important;
  width: 100% !important;
  max-width: 600px !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
  box-shadow: 0 25px 70px rgba(0, 0, 0, 0.85) !important;
  position: relative !important;
  z-index: 100000 !important;
  color: #f4f4f5 !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
}

.modal-header {
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
  padding: 18px 24px !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  background: #141417 !important;
}

.modal-header-info {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
}

.modal-header-info h4, .modal-header h4 {
  font-size: 16px !important;
  font-weight: 700 !important;
  color: #fff !important;
  margin: 0 !important;
}

.modal-sub {
  font-size: 11px !important;
  color: #a1a1aa !important;
  display: block !important;
  margin-top: 2px !important;
}

.close-btn {
  background: transparent !important;
  border: none !important;
  color: #71717a !important;
  font-size: 18px !important;
  cursor: pointer !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  padding: 6px !important;
  border-radius: 6px !important;
  transition: all 0.2s !important;
}

.close-btn:hover {
  color: #fff !important;
  background: rgba(255, 255, 255, 0.08) !important;
}

.modal-body {
  padding: 20px 24px !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 14px !important;
  max-height: 75vh !important;
  overflow-y: auto !important;
}

.pair-modal-body {
  display: flex !important;
  flex-direction: column !important;
  gap: 16px !important;
  padding: 16px 20px !important;
  max-height: 78vh !important;
  overflow-y: auto !important;
}

.pair-guide {
  display: flex !important;
  flex-direction: column !important;
  gap: 10px !important;
  background: #09090b !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 10px !important;
  padding: 14px !important;
}

.pair-step {
  display: flex !important;
  align-items: flex-start !important;
  gap: 12px !important;
}

.step-num {
  width: 22px !important;
  height: 22px !important;
  border-radius: 50% !important;
  background: #27272a !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 11px !important;
  font-weight: 700 !important;
  color: #10b981 !important;
  flex-shrink: 0 !important;
}

.step-content strong {
  font-size: 12px !important;
  color: #f4f4f5 !important;
  display: block !important;
}

.step-content p {
  font-size: 11px !important;
  color: #71717a !important;
  margin-top: 2px !important;
}

.link-openbot {
  color: #10b981 !important;
  text-decoration: underline !important;
}

.pair-qr-card {
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  background: #09090b !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 12px !important;
  padding: 20px !important;
}

.qr-img {
  width: 200px !important;
  height: 200px !important;
  background: #fff !important;
  padding: 8px !important;
  border-radius: 10px !important;
  display: block !important;
  margin: 0 auto !important;
}

.qr-placeholder {
  min-height: 200px !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 12px !important;
  color: #a1a1aa !important;
  font-size: 13px !important;
}

.qr-countdown {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  margin-top: 12px !important;
  font-size: 12px !important;
  color: #a1a1aa !important;
}

.dot-online {
  width: 7px !important;
  height: 7px !important;
  border-radius: 50% !important;
  background: #10b981 !important;
  box-shadow: 0 0 8px #10b981 !important;
}

.pair-manual-info {
  display: flex !important;
  flex-direction: column !important;
  gap: 12px !important;
}

.info-group label {
  font-size: 11px !important;
  font-weight: 600 !important;
  color: #a1a1aa !important;
  margin-bottom: 4px !important;
  display: block !important;
}

.copy-input-row {
  display: flex !important;
  gap: 8px !important;
}

.copy-input-row input {
  flex: 1 !important;
  background: #09090b !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  color: #10b981 !important;
  padding: 8px 12px !important;
  border-radius: 8px !important;
  font-size: 12px !important;
}

.modal-footer, .pair-modal-footer {
  display: flex !important;
  justify-content: flex-end !important;
  gap: 10px !important;
  padding: 16px 24px !important;
  border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
  background: #141417 !important;
}

.pair-modal-footer {
  justify-content: space-between !important;
  align-items: center !important;
}

@media (max-width: 768px) {
  .modal-overlay {
    padding: 10px !important;
  }
  .agent-modal, .pair-modal {
    max-width: 100% !important;
    max-height: 95vh !important;
    border-radius: 12px !important;
  }
  .modal-body, .pair-modal-body {
    padding: 16px !important;
    max-height: 70vh !important;
  }
  .pair-modal-footer {
    flex-direction: column !important;
    gap: 8px !important;
  }
  .pair-modal-footer button {
    width: 100% !important;
    justify-content: center !important;
  }
  .qr-img {
    width: 170px !important;
    height: 170px !important;
  }
}

/* ── MODE SELECTOR IN PAIR MODAL ── */
.pair-mode-selector {
  display: flex !important;
  background: #09090b !important;
  padding: 4px !important;
  border-radius: 10px !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  gap: 4px !important;
}

.mode-btn {
  flex: 1 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 8px !important;
  padding: 8px 12px !important;
  background: transparent !important;
  border: none !important;
  color: #a1a1aa !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  border-radius: 6px !important;
  cursor: pointer !important;
  transition: all 0.2s !important;
}

.mode-btn:hover {
  color: #fff !important;
}

.mode-btn.active {
  background: #27272a !important;
  color: #10b981 !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
}

.qr-optical-box {
  background: #ffffff !important;
  padding: 12px !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5) !important;
  display: inline-block !important;
}

.qr-img {
  width: 180px !important;
  height: 180px !important;
  display: block !important;
  margin: 0 auto !important;
  image-rendering: pixelated !important;
}

</style>
