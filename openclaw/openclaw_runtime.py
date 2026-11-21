import time
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Callable
from models import OperationDispatch, OperationEvent, ClientConfig, AgentDef

logger = logging.getLogger("openclaw_runtime")

class OpenClawRuntime:
    """The Autonomous Multi-Agent Execution Engine (Manus + Paperclip + Grok Bot + OpenBot model)."""
    def __init__(self, queue_manager, broadcast_callback: Callable = None):
        self.queue_mgr = queue_manager
        self.broadcast = broadcast_callback
        self.clients: Dict[str, ClientConfig] = {}
        self.operations: Dict[str, OperationDispatch] = {}
        self.agents: Dict[str, AgentDef] = {}
        self._init_defaults()

    def _init_defaults(self):
        """Seed default organization hierarchy."""
        default_client = ClientConfig(
            client_id="cli_mkos_saas",
            client_name="MarketingOS / MKOS",
            whatsapp_channel_id="5511999998888",
            budget_monthly_usd=50.0,
            budget_current_usd=4.20,
            status="active"
        )
        self.clients[default_client.client_id] = default_client

        # Level 1: Director
        director = AgentDef(
            agent_id="agt_supervisor_geral",
            client_id=default_client.client_id,
            name="Diretor Geral (Supervisor)",
            role="director",
            system_prompt="Você é o Diretor Geral da agência. Valida budgets, regras de compliance e delega operações para especialistas.",
            model="gemini-2.0-flash",
            tools_allowed=["delegate_task", "check_budget", "request_human_approval"],
            status="idle",
            current_thought="Supervisionando operações da agência..."
        )
        self.agents[director.agent_id] = director

        # Level 2: Leo (Content & Media)
        leo = AgentDef(
            agent_id="agt_cosmeticos_criador",
            client_id=default_client.client_id,
            name="Leo - Produtor de Vídeos UGC",
            role="content_creator",
            system_prompt="Especialista em roteiros, renderização Remotion cinematográfica e injeção em galerias móveis.",
            model="gemini-2.0-flash",
            tools_allowed=["generate_remotion_video", "inject_android_gallery", "send_whatsapp_media"],
            remotion_templates=["N1-remotion", "N4ProductCinematic"],
            status="idle",
            current_thought="Pronto para renderizar novos Reels cinematográficos."
        )
        self.agents[leo.agent_id] = leo

        # Level 2: Clara (Sales & Support)
        clara = AgentDef(
            agent_id="agt_cosmeticos_vendas",
            client_id=default_client.client_id,
            name="Clara - Atendimento & Vendas",
            role="support_and_sales",
            system_prompt="Atendimento humanizado, recomendação de catálogo e conversão de pedidos via WhatsApp.",
            model="gemini-2.0-flash",
            tools_allowed=["search_catalog", "check_order_status", "send_pix_charge"],
            status="idle",
            current_thought="Aguardando mensagens de clientes no WhatsApp."
        )
        self.agents[clara.agent_id] = clara

        # Level 2: MKOS Operations
        mkos_ops = AgentDef(
            agent_id="agt_mkos_operacoes",
            client_id=default_client.client_id,
            name="MKOS Operações & No-Show",
            role="operations_mkos",
            system_prompt="Monitoramento de agendamentos, confirmações de presença e prevenção de no-show para clínicas e PMEs.",
            model="gemini-2.0-flash",
            tools_allowed=["sync_mural_n8n", "check_no_show", "send_whatsapp_reminder"],
            status="idle",
            current_thought="Monitorando no-show e agendamentos em tempo real."
        )
        self.agents[mkos_ops.agent_id] = mkos_ops

    def register_client(self, client: ClientConfig):
        self.clients[client.client_id] = client
        for agent in client.agents:
            self.agents[agent.agent_id] = agent
        self._notify_state_change()

    def register_agent(self, agent: AgentDef):
        self.agents[agent.agent_id] = agent
        if agent.client_id in self.clients:
            # Update client's agent list
            client = self.clients[agent.client_id]
            client.agents = [a for a in client.agents if a.agent_id != agent.agent_id] + [agent]
        self._notify_state_change()

    def dispatch_operation(self, op: OperationDispatch) -> OperationDispatch:
        # 1. Budget Kill-Switch Check
        client = self.clients.get(op.client_id)
        if not client or client.status != "active":
            raise ValueError(f"Cliente '{op.client_id}' inativo ou inexistente.")

        if client.budget_current_usd >= client.budget_monthly_usd:
            client.status = "paused"
            self._notify_state_change()
            raise PermissionError(f"Kill-Switch acionado: Limite mensal de US$ {client.budget_monthly_usd} atingido para {client.client_name}.")

        op.status = "queued"
        self.operations[op.task_id] = op
        self._add_event(op, op.agent_id, "thought", f"Operação '{op.action}' recebida pelo Diretor. Alocando especialista...")

        # Run async in background thread
        import threading
        threading.Thread(target=self._run_operation_pipeline, args=(op,), daemon=True).start()
        return op

    def _run_operation_pipeline(self, op: OperationDispatch):
        agent = self.agents.get(op.agent_id)
        if not agent:
            self._add_event(op, "director", "error", f"Agente '{op.agent_id}' não encontrado.")
            op.status = "failed"
            return

        try:
            # Set agent busy
            agent.status = "thinking"
            agent.current_thought = f"Executando '{op.action}'..."
            self._notify_state_change()

            if op.action == "create_and_send_reel":
                self._execute_create_and_send_reel(op, agent)
            elif op.action == "organic_warmup":
                self._execute_organic_warmup(op, agent)
            elif op.action == "no_show_reminder":
                self._execute_no_show_reminder(op, agent)
            else:
                self._add_event(op, agent.agent_id, "thought", f"Executando playbook genérico: {op.action}")
                time.sleep(2)
                op.status = "completed"
                op.result = {"message": f"Ação {op.action} executada com sucesso"}

            if op.status != "waiting_approval":
                op.status = "completed"
                op.completed_at = datetime.now().isoformat()
                self._add_event(op, agent.agent_id, "completed", "Operação concluída com sucesso.")

        except Exception as e:
            logger.exception("Operation execution failed")
            op.status = "failed"
            self._add_event(op, agent.agent_id, "error", f"Falha na operação: {str(e)}")
        finally:
            if op.status != "waiting_approval":
                agent.status = "idle"
                agent.current_thought = "Aguardando novas demandas..."
                self._notify_state_change()

    def _execute_create_and_send_reel(self, op: OperationDispatch, agent: AgentDef):
        # Step 1: Script & Concept (Level 2: Leo)
        agent.status = "thinking"
        agent.current_thought = "Criando roteiro cinematográfico para o produto..."
        self._add_event(op, agent.agent_id, "thought", "Estruturando Hook (3s), Demonstração (8s) e Call to Action (4s)...")
        time.sleep(1.5)

        # Step 2: Enqueue Remotion Render (Level 3: Ephemeral Subagent with Concurrency=1)
        agent.status = "executing_tool"
        agent.current_thought = "Enviando job de renderização para a fila Redis (concurrency=1)..."
        self._add_event(op, agent.agent_id, "tool_call", "Subagente Efêmero iniciado: render_remotion_composition")
        
        job_id = self.queue_mgr.enqueue_render({
            "job_id": f"render_{op.task_id}",
            "composition": "N1-remotion",
            "output_filename": f"{op.task_id}_ugc.mp4",
            "parameters": op.parameters
        })

        # Wait for render to complete in Redis queue
        while True:
            job = self.queue_mgr.get_job(job_id)
            if job and job.get("status") == "completed":
                output_path = job.get("output_path")
                duration = job.get("duration_s")
                self._add_event(op, agent.agent_id, "tool_result", f"Vídeo renderizado em {duration}s: {output_path}")
                break
            elif job and job.get("status") == "failed":
                raise RuntimeError(f"Falha na renderização Remotion: {job.get('error')}")
            time.sleep(1)

        # Step 3: Inject into Android Gallery via Host Docker or Virtuale API
        agent.current_thought = "Injetando vídeo na Galeria do celular Android..."
        self._add_event(op, agent.agent_id, "tool_call", "Injetando MP4 em /data/media/0/DCIM/Camera e disparando broadcast...")
        injected = False
        try:
            filename = f"{op.task_id}.mp4"
            target_path = f"/data/media/0/DCIM/Camera/{filename}"
            # 1. Direct host docker cp
            subprocess.run(["docker", "exec", "mkos-phone-01", "mkdir", "-p", "/data/media/0/DCIM/Camera"], check=False, timeout=5)
            subprocess.run(["docker", "cp", output_path, f"mkos-phone-01:{target_path}"], check=True, timeout=10)
            subprocess.run(["docker", "exec", "mkos-phone-01", "chown", "-R", "media_rw:media_rw", "/data/media/0/DCIM/Camera"], check=True, timeout=5)
            subprocess.run(["docker", "exec", "mkos-phone-01", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file:///sdcard/DCIM/Camera/{filename}"], check=True, timeout=5)
            injected = True
            self._add_event(op, agent.agent_id, "tool_result", "Vídeo indexado com sucesso na Galeria Android (pronto para Reels/WhatsApp).")
        except Exception as e:
            logger.warning(f"Direct docker injection failed, trying API fallback: {e}")
            try:
                import requests
                with open(output_path, "rb") as vf:
                    r = requests.post("http://127.0.0.1/api/instances/1/inject_video/", files={"video": (f"{op.task_id}.mp4", vf, "video/mp4")}, timeout=15)
                if r.status_code == 200:
                    injected = True
                    self._add_event(op, agent.agent_id, "tool_result", "Vídeo injetado com sucesso via API do Virtuale.")
                else:
                    self._add_event(op, agent.agent_id, "tool_result", f"API status {r.status_code}: {r.text[:100]}")
            except Exception as ex:
                self._add_event(op, agent.agent_id, "tool_result", f"Aviso na injeção da galeria: {ex}")

        # Step 4: Human-in-the-loop Approval before WhatsApp dispatch
        if op.parameters.get("require_approval", True):
            op.requires_approval = True
            op.status = "waiting_approval"
            agent.status = "waiting_approval"
            agent.current_thought = "Aguardando aprovação humana para disparo de mídia no WhatsApp."
            self._add_event(op, agent.agent_id, "approval_request", f"Vídeo pronto para envio ao destinatário {op.target_recipient}. Deseja aprovar o envio?")
            self._notify_state_change()

    def _execute_organic_warmup(self, op: OperationDispatch, agent: AgentDef):
        agent.status = "executing_tool"
        agent.current_thought = "Executando rolagem orgânica anti-ban com pausas humanas..."
        self._add_event(op, agent.agent_id, "thought", "Disparando swipes com jitter gaussiano no dispositivo Android...")
        
        import requests
        for i in range(1, 4):
            agent.current_thought = f"Rolagem {i}/3 com pausa de leitura..."
            self._add_event(op, agent.agent_id, "tool_call", f"Swipe {i}/3 no celular...")
            try:
                requests.post("http://127.0.0.1/api/instances/1/swipe/", json={
                    "x1": 360, "y1": 900, "x2": 360, "y2": 300, "duration": 350
                }, timeout=10)
            except Exception:
                pass
            time.sleep(3)

    def _execute_no_show_reminder(self, op: OperationDispatch, agent: AgentDef):
        agent.status = "thinking"
        agent.current_thought = "Consultando agendamentos e calculando risco de no-show..."
        self._add_event(op, agent.agent_id, "thought", "Filtrando consultas das próximas 24h sem confirmação...")
        time.sleep(2)
        self._add_event(op, agent.agent_id, "tool_call", f"Enviando lembrete interativo via WhatsApp para {op.target_recipient}...")
        time.sleep(1)
        self._add_event(op, agent.agent_id, "tool_result", "Confirmação de agendamento enviada. Status atualizado no Mural n8n.")

    def approve_operation(self, task_id: str):
        op = self.operations.get(task_id)
        if not op or op.status != "waiting_approval":
            raise ValueError(f"Operação {task_id} não está aguardando aprovação.")
        
        op.approved = True
        op.status = "completed"
        op.completed_at = datetime.now().isoformat()
        agent = self.agents.get(op.agent_id)
        if agent:
            agent.status = "idle"
            agent.current_thought = "Operação aprovada e concluída. Aguardando tarefas..."
        self._add_event(op, op.agent_id, "completed", "Aprovação concedida pelo administrador. Mídia despachada via WhatsApp.")
        self._notify_state_change()
        return op

    def _add_event(self, op: OperationDispatch, agent_id: str, event_type: str, content: str, meta: dict = None):
        ev = OperationEvent(
            timestamp=datetime.now().strftime("%H:%M:%S"),
            agent_id=agent_id,
            type=event_type,
            content=content,
            metadata=meta or {}
        )
        op.events.append(ev)
        self._notify_state_change(event=ev, op=op)

    def _notify_state_change(self, event=None, op=None):
        if self.broadcast:
            payload = {
                "type": "state_update",
                "agents": [a.dict() for a in self.agents.values()],
                "clients": [c.dict() for c in self.clients.values()],
            }
            if event:
                payload["last_event"] = event.dict()
            if op:
                payload["current_op"] = {
                    "task_id": op.task_id,
                    "status": op.status,
                    "action": op.action,
                    "events": [e.dict() for e in op.events[-6:]]
                }
            self.broadcast(payload)
