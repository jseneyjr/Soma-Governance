import json
import re

with open("soma_mcp/tools.py", "r", encoding="utf-8") as f:
    content = f.read()

execute_tools = {
    "soma_propose_change", "soma_verify_changes", "soma_checkpoint",
    "soma_audit_security", "soma_audit_performance", "soma_generate_manifest"
}

# The simplest way to do this is to parse the python file by AST or just use regex.
# Since it's a python dict literal, we can use ast.literal_eval if we extract it,
# but it's simpler to do string replacements.

receipt_prop = ',\n                "receipt": {"type": "string", "description": "Execution receipt ID obtained from soma_request_receipt"}'

replacements = [
    ('{"type": "string", "description": "The complete proposed file content."}', '{"type": "string", "description": "The complete proposed file content."}' + receipt_prop),
    ('{"type": "string", "description": "Path to the file being changed."}', '{"type": "string", "description": "Path to the file being changed."}' + receipt_prop),
    ('"items": {"type": "string"},\n                    "description": "List of changed files to verify."\n                }', '"items": {"type": "string"},\n                    "description": "List of changed files to verify."\n                }' + receipt_prop),
    ('"workspace": {"type": "string", "description": "Path to the project workspace."}', '"workspace": {"type": "string", "description": "Path to the project workspace."}' + receipt_prop),
    ('"properties": {}', '"properties": {"receipt": {"type": "string", "description": "Execution receipt ID obtained from soma_request_receipt"}}'),
    # For soma_generate_manifest it has properties.
    ('"generate_key": {"type": "boolean", "description": "Whether to generate a new key if none exists."}', '"generate_key": {"type": "boolean", "description": "Whether to generate a new key if none exists."}' + receipt_prop)
]

for old, new in replacements:
    content = content.replace(old, new)

# Now add soma_request_receipt
request_receipt_tool = """
    {
        "name": "soma_request_receipt",
        "description": "Request an execution receipt for a privileged tool. Required before calling any execution tools (if execution is enabled).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "operation": {"type": "string", "description": "The name of the execute tool you want to call."},
                "arguments": {"type": "object", "description": "The arguments you will pass to the execute tool."}
            },
            "required": ["operation", "arguments"]
        }
    },"""

content = content.replace("TOOL_DEFINITIONS = [", "TOOL_DEFINITIONS = [" + request_receipt_tool)

with open("soma_mcp/tools.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patched tools.py")
