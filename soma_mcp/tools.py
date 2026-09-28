import os
import sys
import glob
import json

# Ensure soma_sdk is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from soma_sdk.governance import Governance

def resolve_workspace():
    """Find the project root containing .soma/cells/."""
    soma_root = os.environ.get("SOMA_ROOT")
    if soma_root and os.path.isdir(os.path.join(soma_root, ".soma", "cells")):
        return os.path.abspath(soma_root)

    cwd = os.getcwd()
    if os.path.isdir(os.path.join(cwd, ".soma", "cells")):
        return cwd

    d = cwd
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".soma", "cells")):
            return d
        d = os.path.dirname(d)
        
    return cwd

def get_governance():
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
                with open(cell_file) as f:
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
        "description": "Runs cell scan against current diff and returns results.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "soma_grade",
        "description": "Returns governance report card.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "soma_coverage",
        "description": "Returns cell coverage report.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "soma_fitness",
        "description": "Returns fitness landscape.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "bayesian": {"type": "boolean", "description": "Use Bayesian smoothing"}
            }
        }
    },
    {
        "name": "soma_list_cells",
        "description": "Lists all governance cells.",
        "inputSchema": {
            "type": "object",
            "properties": {}
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
        return {"prompt": prompt, "instruction": "Process this prompt and return the cell YAML. Then use a file-writing tool to save it to the appropriate .soma/cells/ directory."}
    
    elif name == "soma_scan":
        return gov.scan()
        
    elif name == "soma_grade":
        return gov.grade()
        
    elif name == "soma_coverage":
        return gov.coverage_report()
        
    elif name == "soma_fitness":
        return gov.fitness_landscape(bayesian=args.get("bayesian", False))
        
    elif name == "soma_list_cells":
        return gov.list_cells()
        
    else:
        raise ValueError(f"Unknown tool: {name}")
