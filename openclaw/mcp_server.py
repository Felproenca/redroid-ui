#!/usr/bin/env python3
"""
OpenBot MCP (Model Context Protocol) Server
Bridges OpenBot (openbot.run) directly with the Virtuale Android Fleet & Multi-Agent Engine.
"""
import sys
import json
import subprocess
import urllib.request
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", stream=sys.stderr)

OPENCLAW_URL = "http://127.0.0.1:8090/api/v1"

TOOLS = [
    {
        "name": "android_screenshot",
        "description": "Capture the current live screen of the Android smartphone (mkos-phone-01). Returns base64 PNG data.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "container_name": {"type": "string", "default": "mkos-phone-01", "description": "Target Android container name."}
            }
        }
    },
    {
        "name": "android_tap",
        "description": "Tap at specific (x, y) coordinates on the Android smartphone screen.",
        "inputSchema": {
            "type": "object",
            "required": ["x", "y"],
            "properties": {
                "x": {"type": "integer", "description": "X coordinate in pixels (e.g. 540)"},
                "y": {"type": "integer", "description": "Y coordinate in pixels (e.g. 960)"},
                "container_name": {"type": "string", "default": "mkos-phone-01"}
            }
        }
    },
    {
        "name": "android_swipe",
        "description": "Perform an organic swipe or scroll gesture on the Android smartphone screen.",
        "inputSchema": {
            "type": "object",
            "required": ["x1", "y1", "x2", "y2"],
            "properties": {
                "x1": {"type": "integer", "description": "Start X coordinate"},
                "y1": {"type": "integer", "description": "Start Y coordinate"},
                "x2": {"type": "integer", "description": "End X coordinate"},
                "y2": {"type": "integer", "description": "End Y coordinate"},
                "duration": {"type": "integer", "default": 350, "description": "Duration in milliseconds"},
                "container_name": {"type": "string", "default": "mkos-phone-01"}
            }
        }
    },
    {
        "name": "android_keyevent",
        "description": "Send a hardware key event (e.g. 3 for Home, 4 for Back) to the smartphone.",
        "inputSchema": {
            "type": "object",
            "required": ["keycode"],
            "properties": {
                "keycode": {"type": "string", "description": "Android keycode (3 for HOME, 4 for BACK)"},
                "container_name": {"type": "string", "default": "mkos-phone-01"}
            }
        }
    },
    {
        "name": "android_open_app",
        "description": "Launch an Android app package on the smartphone (e.g. com.instagram.android).",
        "inputSchema": {
            "type": "object",
            "required": ["package"],
            "properties": {
                "package": {"type": "string", "description": "Android package name (e.g. com.instagram.android, com.whatsapp)"},
                "container_name": {"type": "string", "default": "mkos-phone-01"}
            }
        }
    },
    {
        "name": "generate_and_inject_reel",
        "description": "Use Leo (UGC Media Worker) to render a 9:16 vertical video with Remotion and inject directly into Android Camera Gallery.",
        "inputSchema": {
            "type": "object",
            "required": ["product_name", "hook"],
            "properties": {
                "product_name": {"type": "string", "description": "Product or feature name"},
                "hook": {"type": "string", "description": "Visual hook / first 3 seconds headline"},
                "require_approval": {"type": "boolean", "default": True, "description": "Require human confirmation before WhatsApp dispatch"}
            }
        }
    },
    {
        "name": "dispatch_agent_mission",
        "description": "Dispatch an autonomous mission to a specialized agent (Clara Vendas, May Cobrança, MKOS No-Show, Leo UGC, Alex Mobile).",
        "inputSchema": {
            "type": "object",
            "required": ["agent_id", "action"],
            "properties": {
                "client_id": {"type": "string", "default": "cli_mkos_saas"},
                "agent_id": {"type": "string", "description": "Agent ID (agt_cosmeticos_vendas, agt_cobranca_may, agt_mkos_operacoes, agt_cosmeticos_criador, agt_mobile_alex)"},
                "action": {"type": "string", "description": "Action name (e.g. create_and_send_reel, organic_warmup, no_show_reminder)"},
                "target_recipient": {"type": "string", "default": "5511999998888"},
                "parameters": {"type": "object", "default": {}}
            }
        }
    },
    {
        "name": "get_fleet_status",
        "description": "Get real-time status of all active agents in the Habblaud virtual office, current thoughts, and pending approvals.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "approve_operation",
        "description": "Approve a held operation awaiting Human-in-the-Loop confirmation.",
        "inputSchema": {
            "type": "object",
            "required": ["task_id"],
            "properties": {
                "task_id": {"type": "string", "description": "Task ID awaiting approval"}
            }
        }
    }
]

def handle_call_tool(name: str, arguments: dict) -> dict:
    cname = arguments.get("container_name", "mkos-phone-01")

    if name == "android_screenshot":
        p = subprocess.run(["docker", "exec", cname, "screencap", "-p"], capture_output=True, timeout=10)
        import base64
        b64 = base64.b64encode(p.stdout).decode("utf-8")
        return {"content": [{"type": "text", "text": f"Screenshot captured ({len(p.stdout)} bytes)."}, {"type": "image", "data": b64, "mimeType": "image/png"}]}

    elif name == "android_tap":
        x, y = arguments["x"], arguments["y"]
        subprocess.run(["docker", "exec", cname, "input", "tap", str(x), str(y)], check=False, timeout=5)
        return {"content": [{"type": "text", "text": f"Tapped at ({x}, {y}) on {cname}"}]}

    elif name == "android_swipe":
        x1, y1 = arguments["x1"], arguments["y1"]
        x2, y2 = arguments["x2"], arguments["y2"]
        duration = arguments.get("duration", 350)
        subprocess.run(["docker", "exec", cname, "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)], check=False, timeout=5)
        return {"content": [{"type": "text", "text": f"Swiped ({x1}, {y1}) -> ({x2}, {y2}) [{duration}ms] on {cname}"}]}

    elif name == "android_keyevent":
        k = arguments["keycode"]
        subprocess.run(["docker", "exec", cname, "input", "keyevent", str(k)], check=False, timeout=5)
        return {"content": [{"type": "text", "text": f"Keyevent {k} sent to {cname}"}]}

    elif name == "android_open_app":
        pkg = arguments["package"]
        subprocess.run(["docker", "exec", cname, "monkey", "-p", pkg, "-c", "android.intent.category.LAUNCHER", "1"], check=False, timeout=5)
        return {"content": [{"type": "text", "text": f"Launched package {pkg} on {cname}"}]}

    elif name in ["generate_and_inject_reel", "dispatch_agent_mission"]:
        payload = {
            "client_id": arguments.get("client_id", "cli_mkos_saas"),
            "agent_id": arguments.get("agent_id", "agt_cosmeticos_criador"),
            "action": arguments.get("action", "create_and_send_reel"),
            "target_recipient": arguments.get("target_recipient", "5511999998888"),
            "parameters": arguments.get("parameters", {
                "product_name": arguments.get("product_name", "Produto"),
                "hook": arguments.get("hook", "Destaque do Produto"),
                "require_approval": arguments.get("require_approval", True)
            })
        }
        req = urllib.request.Request(f"{OPENCLAW_URL}/operations/dispatch", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        return {"content": [{"type": "text", "text": f"Operation queued with Task ID: {res.get('task_id')}. Agent: {res.get('agent_id')}"}]}

    elif name == "get_fleet_status":
        req = urllib.request.Request(f"{OPENCLAW_URL}/habblaud/state")
        data = json.loads(urllib.request.urlopen(req, timeout=5).read().decode())
        summary = f"Active Agents: {len(data.get('agents', []))}\n"
        for a in data.get("agents", []):
            summary += f"- {a['name']} ({a['role']}): [{a['status']}] {a['current_thought']}\n"
        return {"content": [{"type": "text", "text": summary}]}

    elif name == "approve_operation":
        tid = arguments["task_id"]
        req = urllib.request.Request(f"{OPENCLAW_URL}/operations/{tid}/approve", data=b"{}", headers={"Content-Type": "application/json"})
        res = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        return {"content": [{"type": "text", "text": f"Operation {tid} approved! Status: {res.get('status')}"}]}

    raise ValueError(f"Unknown tool: {name}")

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
            method = req.get("method")
            req_id = req.get("id")

            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "mkos-openbot-mcp", "version": "1.0.0"}
                    }
                }
            elif method == "tools/list":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": TOOLS}
                }
            elif method == "tools/call":
                params = req.get("params", {})
                tool_res = handle_call_tool(params.get("name"), params.get("arguments", {}))
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": tool_res
                }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method {method} not found"}
                }

            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()
        except Exception as e:
            logging.exception("MCP Error")
            if "req_id" in locals() and req_id is not None:
                err_res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": str(e)}
                }
                sys.stdout.write(json.dumps(err_res) + "\n")
                sys.stdout.flush()

if __name__ == "__main__":
    main()
