try:
    import fcntl
except ImportError:
    fcntl = None  # Windows: no flock; appends are unlocked
import glob
import importlib
import json
import os
import re
import sys
from datetime import datetime, timezone

# pyyaml is an OPTIONAL dependency of soma_mcp. The server must start on a bare
# interpreter (see .soma/cells/walls/wall-mcp-zero-deps.md), so we only use
# pyyaml when it happens to be installed.
try:
    import yaml
except ImportError:
    yaml = None

# Ensure soma_sdk is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import JIT engine (stdlib only — parses frontmatter without pyyaml)
from soma_mcp.jit_engine import express as jit_express
from soma_mcp.jit_engine import parse_frontmatter, warn

# Import security utilities
from soma_mcp.security import confine_workspace, confine_path, validate_cell_names
from soma_mcp.integrity import (
    load_manifest, verify_manifest, generate_manifest, save_manifest,
    generate_key, load_key,
)

# ── Enzyme import hardening ───────────────────────────────────────────
# Only allowlisted enzyme modules may be imported. This prevents a dropped
# .py file in enzymes/ from being auto-loaded by the MCP server.
_ENZYME_ALLOWLIST = frozenset({
    "ttc_verifier",
    "insight_capture",
})

_ENZYMES_DIR = os.path.realpath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "enzymes")
)


def _safe_import_enzyme(module_name: str, attr: str):
    """Import an attribute from an allowlisted enzyme module.

    Validates that the module is in the allowlist and that the resolved
    module file is inside the enzymes/ directory.
    """
    if module_name not in _ENZYME_ALLOWLIST:
        raise ImportError(f"Enzyme '{module_name}' is not in the import allowlist")
    mod = importlib.import_module(f"enzymes.{module_name}")
    mod_file = getattr(mod, "__file__", None)
    if mod_file:
        resolved = os.path.realpath(mod_file)
        if not resolved.startswith(_ENZYMES_DIR + os.sep):
            raise ImportError(
                f"Enzyme '{module_name}' resolved outside enzymes/: {resolved}"
            )
    return getattr(mod, attr)


# Import TTC Verifier via safe import
try:
    soma_propose_change = _safe_import_enzyme("ttc_verifier", "soma_propose_change")
except ImportError:
    soma_propose_change = None

# Try importing Governance SDK (requires pyyaml); fall back to stdlib-only impl
try:
    from soma_sdk.governance import Governance
    _HAS_SDK = True
except ImportError:
    _HAS_SDK = False


# INTENTIONAL DUPLICATION: wall-mcp-zero-deps prohibits importing from enzymes/
# Canonical source: enzymes/soma_resolve.py — keep in sync manually
def resolve_workspace():
    """Find the project root containing .soma/cells/."""
    soma_root = os.environ.get("SOMA_ROOT")
    if soma_root:
        if os.path.isdir(os.path.join(soma_root, ".soma", "cells")):
            return os.path.abspath(soma_root)
        else:
            raise ValueError(f"SOMA_ROOT is set to {soma_root} but no .soma/cells found there.")

    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, ".soma", "cells")):
        return cwd

    d = cwd
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".soma", "cells")):
            return d
        d = os.path.dirname(d)
        
    return cwd


# ── Checkpoint helpers (shared with soma_cli.checkpoint) ──────────────
# Imported from immune_system.verification.checkpoint_checks to avoid
# copy-paste divergence. See trap-recurring-finding-escape.md.

from immune_system.verification.checkpoint_checks import (
    run_all_checks as _run_checkpoint_checks,
    check_test_coverage as _checkpoint_test_coverage,
    check_hardcoded_paths as _checkpoint_hardcoded_paths,
    check_assertion_density as _checkpoint_assertion_density,
    check_cell_fitness as _checkpoint_cell_fitness,
    check_cell_conventions as _checkpoint_cell_conventions,
    check_arbitration_evidence as _checkpoint_arbitration_evidence,
    CHECK_NAMES as _CHECKPOINT_NAMES,
)



def _parse_frontmatter(content):
    """Parse YAML frontmatter.

    Delegates to the shared implementation in jit_engine, which uses pyyaml when
    installed and a stdlib subset parser otherwise. Returns {} when there is no
    frontmatter and None when frontmatter is present but malformed.
    """
    return parse_frontmatter(content)


def _list_cells_stdlib(workspace):
    """List cells using only stdlib (no pyyaml)."""
    cells = []
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if not os.path.isdir(cells_dir):
        return cells
    for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
        if os.path.basename(cell_file) == 'README.md':
            continue
        rel = os.path.relpath(cell_file, workspace)
        try:
            with open(cell_file, encoding="utf-8") as f:
                content = f.read()
            fm = _parse_frontmatter(content)
            if fm is None:
                warn(f'skipped cell {rel}: malformed YAML frontmatter')
                continue
            if not fm:
                warn(f'skipped cell {rel}: no frontmatter metadata')
                continue
            fm['_name'] = os.path.splitext(os.path.basename(cell_file))[0]
            fm['_path'] = rel
            cells.append(fm)
        except Exception as e:
            warn(f'skipped cell {rel}: {e.__class__.__name__}: {e}')
    return cells


# Outcome vocabulary shared with the transport layer (see server._is_error_result).
_STATUS_PASS = "PASS"
_STATUS_FAIL = "FAIL"

# Mirrors the "outcome" enum advertised in TOOL_DEFINITIONS for soma_report_outcome.
_VALID_OUTCOMES = ("success", "partial", "failure", "tp", "fp")


_VERDICT_RE = re.compile(r'^\s*VERDICT:\s*([A-Z_]+)')
_PASSING_VERDICTS = ("APPROVED", "PASS", "SUCCESS", "OK")


def _classify_propose_result(result):
    """Classify a soma_propose_change return value as (status, verdict).

    enzymes.ttc_verifier returns a human-readable report whose first line is
    "VERDICT: <APPROVED|REJECTED|BLOCKED|ESCALATION_REQUIRED> ...". Only an
    approving verdict counts as a pass: a rejection, an inconclusive gate and an
    escalation hold all mean the change must not be treated as done.

    Passing outcomes are whitelisted rather than failures blacklisted, so an
    unrecognised report fails closed instead of telling the client that a
    blocked change went through.
    """
    verdict = None
    if isinstance(result, str):
        match = _VERDICT_RE.match(result)
        if match:
            verdict = match.group(1)
        elif result.lstrip().upper().startswith("SUCCESS"):
            verdict = "SUCCESS"
    elif isinstance(result, dict):
        if "error" in result:
            return _STATUS_FAIL, None
        verdict = str(result.get("status", "")).upper() or None
    if verdict is None:
        return _STATUS_FAIL, None
    return (_STATUS_PASS if verdict in _PASSING_VERDICTS else _STATUS_FAIL), verdict


def get_governance():
    if not _HAS_SDK:
        return None
    workspace = resolve_workspace()
    return Governance(project_root=workspace)


def build_cell_create_prompt(description: str, domain_hint: str = None, cell_type: str = None) -> str:
    workspace = resolve_workspace()
    
    examples = []
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if os.path.isdir(cells_dir):
        for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
            if os.path.basename(cell_file) == 'README.md': continue
            try:
                with open(cell_file, encoding="utf-8") as f:
                    content = f.read()
                if content.startswith('---'):
                    examples.append(content[:500])
            except Exception: pass
            
    example_text = '\n---\n'.join(examples[:3]) if examples else 'No existing cells found.'
    domain_context = f'\nDomain hint: {domain_hint}' if domain_hint else ''
    type_hint = f'\nPreferred cell type: {cell_type}' if cell_type else ''
    
    prompt = f"""You are a governance cell generator for Soma.

Given a natural language description of a concern, generate a governance cell in markdown with YAML frontmatter.

Cell types:
- wall: Non-negotiable invariant (hard safety gate). Use for things that must ALWAYS hold.
- vacuole: Learned anti-pattern trap. Use for known failure modes to watch for.
- membrane: Escalation gate. Use when sensitive areas need elevated review.
- chloroplast: Domain persona/accelerator. Use for idiomatic patterns to follow.
- plasmodesmata: Cross-service contract. Use for API/data shape agreements.

YAML fields required:
- type: (one of above)
- hypothesis: (clear, testable statement)
- prediction: (what will happen if the hypothesis is violated)
- falsification: (how to prove this cell is no longer needed)
- target_paths: (list of file glob patterns this cell monitors)
- minimum_mode: (breeze | gale | trident | maelstrom | tempest)
- tags: (list of relevant tags)

Optionally include:
- fitness: (triggers: 0, true_positives: 0, false_positives: 0, score: null)

Existing cells in this project for reference:
{example_text}
{domain_context}{type_hint}

User description: "{description}"

Generate ONLY the complete markdown cell file content. Start with --- for the YAML frontmatter. After the closing ---, include a brief description paragraph explaining the cell's purpose. Do not include any other text."""

    return prompt

TOOL_DEFINITIONS = [
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
    },
    {
        "name": "soma_create_cell",
        "description": "Takes a natural language description and builds a prompt to create a governance cell.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "Natural language description"},
                "cell_type": {"type": "string", "description": "Optional cell type hint"},
                "domain": {"type": "string", "description": "Optional domain hint"},
                "dry_run": {"type": "boolean", "description": "Optional dry run flag"}
            },
            "required": ["description"]
        }
    },
    {
        "name": "soma_scan",
        "description": (
            "CALL THIS BEFORE MAKING CHANGES. Returns governance guidance relevant to "
            "the specific files you are about to modify. Provides 2-3 focused rules "
            "based on your current git diff, ranked by proven effectiveness. "
            "Includes safety gates, known anti-patterns, and project-specific conventions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of files being changed. Auto-detects from git diff if omitted."
                }
            }
        }
    },
    {
        "name": "soma_report_outcome",
        "description": (
            "Report the outcome of your work for fitness scoring. "
            "Call after completing a task to improve future governance guidance."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "cells_used": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Names of cells that influenced your work"
                },
                "outcome": {
                    "type": "string",
                    "enum": ["success", "partial", "failure"],
                    "description": "Overall outcome of the task"
                },
                "tests_passed": {"type": "boolean", "description": "Did tests pass?"},
                "rework_count": {"type": "integer", "description": "How many times you redid work"},
                "notes": {"type": "string", "description": "Optional notes on what helped or didn't"}
            },
            "required": ["outcome"]
        }
    },
    {
        "name": "soma_grade",
        "description": "Returns governance report card with fitness grades.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "soma_coverage",
        "description": "Returns cell coverage report showing which files are governed.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "soma_fitness",
        "description": "Returns fitness landscape showing cell health and evolution.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bayesian": {"type": "boolean", "description": "Use Bayesian smoothing"}
            }
        }
    },
    {
        "name": "soma_list_cells",
        "description": "Lists all governance cells with their type, hypothesis, and fitness data.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "soma_propose_change",
        "description": "(PROTOTYPE - ADVISORY ONLY) The gateway MCP tool. Propose a change to a file. The system will verify the change against active JIT rules before writing to the file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Absolute or relative path to the file to change."},
                "proposed_content": {"type": "string", "description": "The complete proposed file content."},
                "receipt": {"type": "string", "description": "Execution receipt ID obtained from soma_request_receipt"}
            },
            "required": ["file_path", "proposed_content"]
        }
    },
    {
        "name": "soma_audit_security",
        "description": "Run a basic Security prototype audit on a proposed diff.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file being changed."},
                "proposed_content": {"type": "string", "description": "The complete proposed file content."},
                "receipt": {"type": "string", "description": "Execution receipt ID obtained from soma_request_receipt"}
            },
            "required": ["file_path", "proposed_content"]
        }
    },
    {
        "name": "soma_audit_performance",
        "description": "Run a basic Performance prototype audit on a proposed diff.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Path to the file being changed."},
                "proposed_content": {"type": "string", "description": "The complete proposed file content."},
                "receipt": {"type": "string", "description": "Execution receipt ID obtained from soma_request_receipt"}
            },
            "required": ["file_path", "proposed_content"]
        }
    },
    {
        "name": "soma_verify_changes",
        "description": "Verify proposed changes against Layer-1 governance checks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of changed files to verify."
                },
                "layer1_only": {"type": "boolean", "description": "Only run Layer-1 checks (default true)."},
                "receipt": {"type": "string", "description": "Execution receipt ID obtained from soma_request_receipt"}
            }
        }
    },
    {
        "name": "soma_checkpoint",
        "description": "Run all checkpoint checks against the workspace.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "receipt": {"type": "string", "description": "Execution receipt ID obtained from soma_request_receipt"}
            }
        }
    },
    {
        "name": "soma_generate_manifest",
        "description": (
            "Generate and sign a cell integrity manifest for the workspace. "
            "Creates an HMAC-SHA256 key if none exists and generate_key is true."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "generate_key": {
                    "type": "boolean",
                    "description": "Generate HMAC key if none exists (default false)."
                },
                "receipt": {"type": "string", "description": "Execution receipt ID obtained from soma_request_receipt"}
            }
        }
    },
    {
        "name": "soma_capture_insight",
        "description": (
            "Capture a human insight about the codebase. Records the insight, "
            "correlates it with governance cell coverage, and persists it to "
            ".soma/human_insights.jsonl for fitness scoring."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "insight": {
                    "type": "string",
                    "description": "Free-text description of the insight"
                },
                "context_files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Files the insight relates to (at least one required)"
                },
                "source_conversation": {
                    "type": "string",
                    "description": "Optional conversation/session identifier"
                },
                "category": {
                    "type": "string",
                    "description": "Optional category tag (e.g. contract_mismatch)"
                }
            },
            "required": ["insight", "context_files"]
        }
    }
]

def execute_tool(name: str, args: dict):
    gov = get_governance()
    
    if name == "soma_create_cell":
        prompt = build_cell_create_prompt(
            description=args.get("description"),
            domain_hint=args.get("domain"),
            cell_type=args.get("cell_type")
        )
        if args.get("dry_run"):
            return {"prompt": prompt, "dry_run": True, "instruction": "Dry run: showing prompt that would be used. No cell will be created."}
        return {"prompt": prompt, "instruction": "Process this prompt and return the cell YAML. Then use a file-writing tool to save it to the appropriate .soma/cells/ directory."}
    
    elif name == "soma_list_cells":
        # list_cells works without pyyaml via stdlib fallback
        if gov:
            return gov.list_cells()
        return _list_cells_stdlib(resolve_workspace())

    elif name == "soma_propose_change":
        if not soma_propose_change:
            return {"error": "soma_propose_change not available"}
        workspace = resolve_workspace()
        file_path = args.get('file_path')
        proposed_content = args.get('proposed_content')
        
        # Express JIT rules for the given file to get active playbooks
        jit_result = jit_express(workspace, changed_files=[file_path])
        active_playbooks = jit_result.get('relevant_cells', [])
        
        result = soma_propose_change(file_path, proposed_content, active_playbooks)
        status, verdict = _classify_propose_result(result)
        # Explicit status so the transport does not have to sniff the message text.
        payload = {"result": result, "status": status}
        if verdict:
            payload["verdict"] = verdict
        return payload
        
    elif name == "soma_audit_security":
        content = args.get("proposed_content", "")
        file_path = args.get("file_path", "")
        # Prototype: Basic keyword scanning for secrets and OWASP basics
        flags = []
        if "password=" in content.lower() or "secret=" in content.lower():
            flags.append(f"- Hardcoded secret or password detected in {file_path}.")
        if "eval(" in content:
            flags.append(f"- eval() detected in {file_path}. Potential injection vector.")
        # Scope checks by file extension when file_path is provided
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ('.html', '.htm', '.js', '.jsx', '.ts', '.tsx'):
                if 'innerHTML' in content or 'document.write' in content:
                    flags.append(f"- Potential XSS vector in {file_path}: innerHTML/document.write usage.")
            if ext == '.sql' or ('execute(' in content and '%s' not in content and '?' not in content):
                if 'f"' in content or "f'" in content or '% ' in content:
                    flags.append(f"- Potential SQL injection in {file_path}: string formatting in query.")

        if flags:
            return {"status": "FAIL", "feedback": "\n".join(flags), "file_path": file_path, "instruction": "Fix these issues and resubmit."}
        return {"status": "PASS", "feedback": f"Security Audit passed for {file_path or 'input'}. No OWASP flaws or exposed secrets detected.", "file_path": file_path}

    elif name == "soma_audit_performance":
        content = args.get("proposed_content", "")
        file_path = args.get("file_path", "")
        # Prototype: Basic keyword scanning for hot-paths and inefficiencies
        flags = []
        if content.count("for ") > 2 and "in " in content:
            # Very naive nested loop check
            flags.append(f"- Potential O(N^2) or deeply nested loop detected in {file_path}.")
        if ".query(" in content and "SELECT *" in content:
            flags.append(f"- Inefficient DB query (SELECT *) detected in {file_path}. Select only needed columns.")
        # Scope checks by file extension when file_path is provided
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == '.py':
                if 'import *' in content:
                    flags.append(f"- Wildcard import in {file_path} may slow startup and increase memory.")

        if flags:
            return {"status": "FAIL", "feedback": "\n".join(flags), "file_path": file_path, "instruction": "Optimize the code and resubmit."}
        return {"status": "PASS", "feedback": f"Performance Audit passed for {file_path or 'input'}. No obvious bottlenecks detected.", "file_path": file_path}

    if name == "soma_verify_changes":
        try:
            workspace = confine_workspace(args.get('workspace') or resolve_workspace())
        except ValueError as exc:
            return {"error": str(exc), "status": _STATUS_FAIL}
        files = args.get('files', [])
        # Confine each file path within the workspace
        try:
            files = [confine_path(f, workspace)[1] for f in files]
        except ValueError as exc:
            return {"error": str(exc), "status": _STATUS_FAIL}
        layer1_only = args.get('layer1_only', True)
        try:
            from immune_system.verification import runner
        except ImportError:
            return {"error": "immune_system.verification is not importable. Install soma with immune_system package."}
        results = runner.run_layer1(changed_files=files, repo_root=workspace)
        verdict = runner.gate_verdict(results)
        summary = runner.format_summary(results)
        evidence = [
            {"tool": r.tool, "target": r.target, "verdict": r.verdict, "detail": r.detail}
            for r in results
        ]
        return {
            "status": "PASS" if verdict else "FAIL",
            "summary": summary,
            "layer1_only": layer1_only,
            "evidence": evidence,
        }

    elif name == "soma_checkpoint":
        try:
            workspace = confine_workspace(args.get('workspace') or resolve_workspace())
        except ValueError as exc:
            return {"error": str(exc), "status": _STATUS_FAIL}
        from pathlib import Path
        root = Path(workspace)
        issues = _run_checkpoint_checks(root)
        return {
            "status": "PASS" if not issues else "FAIL",
            "checks": _CHECKPOINT_NAMES,
            "issue_count": len(issues),
            "issues": issues,
        }

    elif name == "soma_scan":
        # v0.23: JIT expression — returns only relevant cells, not everything
        workspace = resolve_workspace()
        files = args.get('files', None)
        return jit_express(workspace, changed_files=files)

    elif name == "soma_report_outcome":
        # v0.23: Agent reports execution outcome for fitness scoring
        workspace = resolve_workspace()
        # Enforce the advertised enum here: persisting 'unknown' would silently
        # poison fitness scoring with un-gradeable rows.
        raw_outcome = args.get('outcome')
        outcome_value = raw_outcome.strip().lower() if isinstance(raw_outcome, str) else None
        if outcome_value not in _VALID_OUTCOMES:
            return {
                "error": (
                    f"Invalid 'outcome': {raw_outcome!r}. "
                    f"Expected one of {list(_VALID_OUTCOMES)}."
                ),
                "status": _STATUS_FAIL,
            }
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        cells_used = args.get('cells_used', [])
        # Validate cell names against actual inventory
        if cells_used:
            invalid = validate_cell_names(cells_used, workspace)
            if invalid:
                return {
                    "error": f"Unknown cell(s): {invalid}. Only existing cells can be reported.",
                    "status": _STATUS_FAIL,
                }
        tests_passed = args.get('tests_passed')
        rework_count = args.get('rework_count', 0)
        notes = args.get('notes', '')
        outcomes_file = os.path.join(workspace, '.soma', 'evidence', 'outcomes.jsonl')
        os.makedirs(os.path.dirname(outcomes_file), exist_ok=True)
        records = []
        for cell_id in cells_used:
            record = {
                'cell_id': cell_id,
                'outcome': outcome_value,
                'timestamp': timestamp,
                'tests_passed': tests_passed,
                'rework_count': rework_count,
                'notes': notes,
            }
            records.append(record)
        with open(outcomes_file, 'a', encoding="utf-8") as f:
            if fcntl is not None:
                fcntl.flock(f, fcntl.LOCK_EX)
            try:
                for record in records:
                    f.write(json.dumps(record) + '\n')
            finally:
                if fcntl is not None:
                    fcntl.flock(f, fcntl.LOCK_UN)
        # Also write to unified telemetry log
        try:
            from soma_sdk.telemetry import append_signal
            signal_map = {'success': 'tp', 'tp': 'tp', 'failure': 'fp',
                          'fp': 'fp', 'partial': 'trigger'}
            for cell_id in cells_used:
                append_signal(
                    workspace=workspace,
                    cell_name=cell_id,
                    signal_type=signal_map.get(outcome_value, 'trigger'),
                    source='mcp',
                    metadata={'notes': notes, 'tests_passed': tests_passed,
                              'rework_count': rework_count},
                )
        except ImportError:
            pass  # Graceful degradation
        return {'status': 'recorded', 'records': records}

    elif name == "soma_capture_insight":
        workspace = resolve_workspace()
        try:
            capture_insight = _safe_import_enzyme("insight_capture", "capture_insight")
        except ImportError:
            return {"error": "enzymes.insight_capture is not importable."}
        try:
            record = capture_insight(
                workspace=workspace,
                insight=args.get('insight', ''),
                context_files=args.get('context_files', []),
                source_conversation=args.get('source_conversation'),
                category=args.get('category'),
            )
        except ValueError as exc:
            return {"error": str(exc), "status": _STATUS_FAIL}
        return {
            'status': 'recorded',
            'insight': record,
        }

    elif name == "soma_generate_manifest":
        workspace = args.get("workspace", "")
        confine_workspace(workspace)
        cells_dir = os.path.join(workspace, ".soma", "cells")

        # Optionally generate HMAC key
        key_created = False
        if args.get("generate_key") and load_key(workspace) is None:
            generate_key(workspace)
            key_created = True

        manifest = generate_manifest(cells_dir)
        save_manifest(workspace, manifest)  # auto-signs if key exists

        return {
            "status": "OK",
            "cell_count": manifest["cell_count"],
            "signed": "signature" in manifest,
            "key_generated": key_created,
            "generated_at": manifest["generated_at"],
        }

    # All other tools require the full SDK (pyyaml)
    if not gov:
        if yaml is None:
            return {"error": "soma_sdk requires pyyaml. Install with: pip install pyyaml"}
        return {"error": "soma_sdk is not importable from this workspace; soma_grade, soma_coverage and soma_fitness are unavailable."}

    if name == "soma_grade":
        return gov.grade()
        
    elif name == "soma_coverage":
        return gov.coverage_report()
        
    elif name == "soma_fitness":
        return gov.fitness_landscape(bayesian=args.get("bayesian", False))
        
    else:
        raise ValueError(f"Unknown tool: {name}")
