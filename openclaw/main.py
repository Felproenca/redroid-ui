import asyncio
import json
import io
import base64
import uuid
import logging
from datetime import datetime
from typing import List
import qrcode
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import ClientConfig, AgentDef, OperationDispatch
from queue_manager import RedisConcurrencyQueue
from openclaw_runtime import OpenClawRuntime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("openclaw_api")

app = FastAPI(title="OpenClaw Autonomous Agent Runtime", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Active WebSocket connections for live streaming
active_connections: List[WebSocket] = []

def ws_broadcast(data: dict):
    msg = json.dumps(data)
    # Broadcast to all connected clients safely in asyncio loop
    for conn in list(active_connections):
        try:
            asyncio.create_task(conn.send_text(msg))
        except Exception:
            pass

# Initialize Redis Concurrency Queue & OpenClaw Runtime
queue_mgr = RedisConcurrencyQueue(host="127.0.0.1", port=6379)
queue_mgr.start_worker(on_progress_callback=lambda job, msg: ws_broadcast({
    "type": "render_progress",
    "job_id": job.get("job_id"),
    "status": job.get("status"),
    "message": msg
}))

runtime = OpenClawRuntime(queue_manager=queue_mgr, broadcast_callback=ws_broadcast)

# ── REST ENDPOINTS ──

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "openclaw-runtime", "version": "1.0.0"}

@app.post("/api/v1/agents")
def create_or_update_agent(agent: AgentDef):
    runtime.register_agent(agent)
    return {"status": "ok", "agent": agent}

@app.get("/api/v1/agents")
def list_agents():
    return [a.dict() for a in runtime.agents.values()]

@app.get("/api/v1/clients")
def list_clients():
    return [c.dict() for c in runtime.clients.values()]

@app.post("/api/v1/operations/dispatch")
def dispatch_operation(payload: OperationDispatch):
    try:
        op = runtime.dispatch_operation(payload)
        return {
            "status": "queued",
            "task_id": op.task_id,
            "agent_id": op.agent_id,
            "action": op.action
        }
    except PermissionError as e:
        raise HTTPException(status_code=402, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/operations/{task_id}")
def get_operation(task_id: str):
    op = runtime.operations.get(task_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operação não encontrada.")
    return op.dict()

@app.post("/api/v1/operations/{task_id}/approve")
def approve_operation(task_id: str):
    try:
        op = runtime.approve_operation(task_id)
        return {"status": "approved", "task_id": op.task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/habblaud/state")
def get_habblaud_state():
    return {
        "agents": [a.dict() for a in runtime.agents.values()],
        "clients": [c.dict() for c in runtime.clients.values()],
        "active_operations": [op.dict() for op in runtime.operations.values() if op.status not in ["completed", "failed"]]
    }

# ── OPENBOT MOBILE PAIRING & MCP INTEGRATION ──

@app.get("/api/v1/openbot/pair")
def generate_openbot_pairing(host_ip: str = "169.58.27.192"):
    """Generates QR Code and credentials for OpenBot mobile companion (openbot.run)."""
    token = f"openbot_{uuid.uuid4().hex[:12]}"
    pair_payload = {
        "v": 1,
        "app": "MKOS Agent Fleet",
        "api": f"http://{host_ip}/api/v1",
        "ws": f"ws://{host_ip}/ws/operations/live",
        "token": token,
        "paired_phone": "mkos-phone-01",
        "created_at": datetime.now().isoformat()
    }

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(json.dumps(pair_payload))
    qr.make(fit=True)
    img = qr.make_image(fill_color="#10b981", back_color="#09090b")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return {
        "status": "ok",
        "pair_payload": pair_payload,
        "qr_code_base64": f"data:image/png;base64,{qr_b64}",
        "expires_in_seconds": 120,
        "instructions": "Abra o aplicativo OpenBot no seu celular, vá em 'Scan QR code' e aponte para esta tela."
    }

@app.get("/api/v1/openbot/mcp-config")
def get_mcp_config():
    """Returns MCP server configuration for OpenBot Desktop / Claude / Cursor."""
    return {
        "mcpServers": {
            "mkos-openbot": {
                "command": "/opt/mkos-agent/.venv/bin/python3",
                "args": ["/opt/openclaw/mcp_server.py"],
                "env": {
                    "PYTHONUNBUFFERED": "1",
                    "OPENCLAW_HOST": "127.0.0.1",
                    "OPENCLAW_PORT": "8090"
                }
            }
        }
    }

# ── WEBSOCKET LIVE STREAM ──

@app.websocket("/ws/operations/live")
async def websocket_live_stream(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # Send initial full state on connect
        initial_state = {
            "type": "state_update",
            "agents": [a.dict() for a in runtime.agents.values()],
            "clients": [c.dict() for c in runtime.clients.values()],
        }
        await websocket.send_text(json.dumps(initial_state))
        while True:
            # Keep alive and receive client heartbeats/triggers
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception:
        if websocket in active_connections:
            active_connections.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8090, reload=False)
