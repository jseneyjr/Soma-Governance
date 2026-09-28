import json
import sys
import traceback
from typing import Dict, Any

from .tools import TOOL_DEFINITIONS, execute_tool

def send_response(response: Dict[str, Any]):
    print(json.dumps(response), flush=True)

def send_error(id: Any, code: int, message: str):
    send_response({
        "jsonrpc": "2.0",
        "id": id,
        "error": {
            "code": code,
            "message": message
        }
    })

def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    method = request.get("method")
    params = request.get("params", {})
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "soma-mcp",
                    "version": "0.1.0"
                }
            }
        }
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": TOOL_DEFINITIONS
            }
        }
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        
        try:
            result = execute_tool(name, args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result) if not isinstance(result, str) else result
                        }
                    ]
                }
            }
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: {str(e)}"
                        }
                    ],
                    "isError": True
                }
            }
    elif method == "notifications/initialized":
        # Just return None for notifications, no response
        return None
    else:
        # Method not found
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            }
        }

def run_stdio_server():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            send_error(None, -32700, "Parse error")
            continue
            
        try:
            if request.get("jsonrpc") != "2.0":
                continue # ignore invalid
                
            if "id" in request:
                # It's a request
                response = handle_request(request)
                if response:
                    send_response(response)
            else:
                # It's a notification
                handle_request(request)
        except Exception as e:
            traceback.print_exc(file=sys.stderr)
            if "id" in request:
                send_error(request["id"], -32603, "Internal error")
                
    return 0
