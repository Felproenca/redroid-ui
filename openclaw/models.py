from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

class AgentDef(BaseModel):
    agent_id: str
    client_id: str
    name: str
    role: str # director, content_creator, support_and_sales, operations_mkos
    system_prompt: str
    model: str = "gemini-2.0-flash"
    tools_allowed: List[str] = []
    memory_namespace: str = ""
    remotion_templates: List[str] = []
    status: str = "idle" # idle, thinking, executing_tool, waiting_approval, paused
    current_thought: str = "Aguardando tarefas..."

class ClientConfig(BaseModel):
    client_id: str
    client_name: str
    whatsapp_channel_id: str = ""
    budget_monthly_usd: float = 30.0
    budget_current_usd: float = 0.0
    status: str = "active" # active, paused
    agents: List[AgentDef] = []

class OperationEvent(BaseModel):
    timestamp: str
    agent_id: str
    type: str # thought, tool_call, tool_result, approval_request, completed, error
    content: str
    metadata: Dict[str, Any] = {}

class OperationDispatch(BaseModel):
    task_id: str = Field(default_factory=lambda: f"op_{uuid.uuid4().hex[:10]}")
    client_id: str
    agent_id: str
    action: str # create_and_send_reel, organic_warmup, customer_chat, no_show_reminder
    target_recipient: Optional[str] = ""
    parameters: Dict[str, Any] = {}
    status: str = "queued" # queued, thinking, executing_tool, waiting_approval, completed, failed
    requires_approval: bool = False
    approved: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    result: Dict[str, Any] = {}
    events: List[OperationEvent] = []
