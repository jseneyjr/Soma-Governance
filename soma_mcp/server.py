import contextlib
import json
import os
import secrets
import sys
import time
import traceback
from collections import defaultdict
from typing import Any, Dict

from .tools import TOOL_DEFINITIONS, execute_tool

_session_token = None

_READ_TOOLS = frozenset({
    "soma_scan", "soma_list_cells", "soma_grade", "soma_coverage", "soma_fitness",
})
_WRITE_TOOLS = frozenset({
    "soma_report_outcome", "soma_capture_insight", "soma_create_cell",
})
_EXECUTE_TOOLS = frozenset({
    "soma_propose_change", "soma_verify_changes", "soma_checkpoint",
    "soma_audit_security", "soma_audit_performance",
})

_tool_call_times = defaultdict(list)
_RATE_LIMITS = {
    "soma_propose_change": (5, 60),
    "soma_report_outcome": (20, 60),
    "soma_verify_changes": (5, 60),
    "soma_checkpoint": (3, 60),
}


def _check_rate_limit(tool_name: str) -> bool:
    """Return True if the call is within rate limits, False if exceeded."""
    if tool_name not in _RATE_LIMITS:
        return True
    max_calls, window_seconds = _RATE_LIMITS[tool_name]
    now = time.monotonic()
    timestamps = _tool_call_times[tool_name]
    # Prune old entries
    _tool_call_times[tool_name] = [t for t in timestamps if now - t < window_seconds]
    if len(_tool_call_times[tool_name]) >= max_calls:
        return False
    _tool_call_times[tool_name].append(now)
    return True

# Messages that mean "the operation did not happen", regardless of the tool.
_ERROR_STATUSES = ("FAIL", "FAILED", "ERROR", "REJECTED", "BLOCKED", "ESCALATION_REQUIRED")
_ERROR_TEXT_PREFIXES = ("ERROR", "CRITICAL ERROR")


def _server_version() -> str:
    """Resolve the version from a single source of truth.

    Was hardcoded here, giving a third independent copy alongside VERSION and
    pyproject.toml with no test tying them together. Prefers installed package
    metadata, falls back to the VERSION file for a source checkout.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version
        try:
            return version("soma-steering")
        except PackageNotFoundError:
            pass
    except ImportError:
        pass

    version_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "VERSION"
    )
    try:
        with open(version_file, "r", encoding="utf-8") as fh:
            return fh.read().strip() or "unknown"
    except OSError:
        return "unknown"


def send_response(response: Dict[str, Any]):
    # stdout is the JSON-RPC transport: only framed responses may be written here.
    print(json.dumps(response), flush=True)


def _is_error_text(value: Any) -> bool:
    return isinstance(value, str) and value.lstrip().upper().startswith(_ERROR_TEXT_PREFIXES)


def _is_error_result(result: Any) -> bool:
    """Decide whether a tool result represents a failure.

    A tool can signal failure three ways: an "error" key, an explicit failure
    "status", or a failure-prefixed message string. Checking only for "error"
    reported rejected proposals and failing audits as successes.
    """
    if _is_error_text(result):
        return True
    if isinstance(result, dict):
        if "error" in result:
            return True
        if str(result.get("status", "")).upper() in _ERROR_STATUSES:
            return True
        # Tools that wrap a human-readable verdict in {"result": "..."}.
        if _is_error_text(result.get("result")):
            return True
    return False

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
        global _session_token
        _session_token = secrets.token_hex(32)
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
                    "version": _server_version(),
                    "_sessionToken": _session_token
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

        # Auth check: write and execute tools require session token
        if name not in _READ_TOOLS:
            client_token = args.get("_sessionToken")
            if _session_token is not None and client_token != _session_token:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32600,
                        "message": f"Authentication required for tool '{name}'. Provide _sessionToken from initialize response."
                    }
                }

        # Rate limit check
        if not _check_rate_limit(name):
            limit_info = _RATE_LIMITS.get(name, (0, 0))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": f"Rate limit exceeded for '{name}': max {limit_info[0]} calls per {limit_info[1]}s"
                }
            }

        try:
            # Tool implementations (and the enzymes they call) may print progress
            # notes. stdout belongs to the JSON-RPC framing, so any stray writes
            # are re-routed to stderr instead of corrupting the stream.
            with contextlib.redirect_stdout(sys.stderr):
                result = execute_tool(name, args)
            is_error = _is_error_result(result)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result) if not isinstance(result, str) else result
                        }
                    ],
                    "isError": is_error
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
                            "text": f"Error: {e!s}"
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
    try:
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
            except Exception:
                traceback.print_exc(file=sys.stderr)
                if "id" in request:
                    send_error(request["id"], -32603, "Internal error")
    except (BrokenPipeError, KeyboardInterrupt):
        pass
                    
    return 0

def main():
    sys.exit(run_stdio_server())
