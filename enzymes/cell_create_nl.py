#!/usr/bin/env python3
"""Natural Language Cell Creation via Gemini API.

Takes a plain English description and generates a governance cell with
proper YAML frontmatter, hypothesis, prediction, and falsification.
"""
import os, sys, argparse, json, subprocess
from soma_core.evidence import aggregate_signals
from soma_core.workspace import resolve_workspace
from soma_core.inference_provider import resolve_provider
from soma_core.lifecycle import create_cell_from_description

import yaml



def create_cell_from_insight_cluster(cluster: dict, workspace: str) -> str:
    """Create a governance cell from an insight cluster.

    Parameters
    ----------
    cluster : dict
        A cluster dict produced by :func:`enzymes.insight_correlator.cluster_insights`.
        Expected keys: ``common_category``, ``common_files``, ``confidence``.
    workspace : str
        Root of the Soma workspace.

    Returns
    -------
    str
        Absolute path to the newly created cell file.
    """
    import re

    category = cluster.get("common_category") or "unknown"
    files = cluster.get("common_files", [])
    confidence = cluster.get("confidence", 0.5)
    files_str = ", ".join(files) if files else "project-wide"

    hypothesis = f"Human attention pattern detected: {category} in {files_str}"

    # Compute slug before building frontmatter (used as id and filename)
    slug = re.sub(r"[^a-z0-9]+", "-", category.lower())[:50].strip("-") or "unknown"
    cell_id = f"vacuole-{slug}"

    frontmatter = {
        "id": cell_id,
        "type": "vacuole",
        "domain": "correctness",
        "hypothesis": hypothesis,
        "prediction": f"Recurring {category} issues will continue if unaddressed",
        "falsification": f"No {category} insights observed for 60 days",
        "target_paths": list(files),
        "minimum_mode": "breeze",
        "origin": "human_insight",
        "tags": ["auto-generated", "insight-cluster", category],
    }

    fm_text = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)

    body = f"This vacuole was auto-generated from a cluster of human insights " \
           f"about **{category}** (confidence {confidence:.2f}).\n"

    cell_content = f"---\n{fm_text}---\n\n{body}"

    # Determine filename
    filename = f"vacuole-{slug}.md"

    target_dir = os.path.join(workspace, ".soma", "cells", "vacuoles")
    os.makedirs(target_dir, exist_ok=True)

    filepath = os.path.join(target_dir, filename)

    # Collision safety: preserve cells with canonical trigger evidence.
    if os.path.isfile(filepath):
        evidence_dir = os.path.join(workspace, '.soma', 'evidence')
        signal_counts = aggregate_signals(evidence_dir).counts
        cell_id = frontmatter.get('id', '')
        if signal_counts.get(cell_id, {}).get('has_triggers', False):
            return filepath

    try:
        os.unlink(filepath)
    except OSError:
        pass
    fd = os.open(filepath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with open(fd, "w", encoding="utf-8") as f:
        f.write(cell_content)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description='Create governance cells from natural language descriptions'
    )
    parser.add_argument('description', nargs='?', default=None,
                       help='Natural language description of the governance concern')
    parser.add_argument('--domain', help='Domain hint (e.g., rl, web, infra, data)')
    parser.add_argument('--type', choices=['wall', 'vacuole', 'membrane', 'chloroplast', 'plasmodesmata'],
                       help='Preferred cell type')
    parser.add_argument('--provider', choices=['auto', 'gemini', 'anthropic', 'openai', 'prompt-only'], default='auto',
                       help='Inference provider to use')
    parser.add_argument('--id', help='Short ID for the cell filename')
    parser.add_argument('--dry-run', action='store_true', help='Print generated cell without creating file')
    parser.add_argument('--json', action='store_true', help='Output metadata as JSON')
    parser.add_argument('--from-insight-cluster', action='store_true',
                       help='Create cells from insight clusters instead of AI generation')
    args = parser.parse_args()
    
    if args.id:
        if "/" in args.id or "\\" in args.id or ".." in args.id:
            sys.exit("Error: Invalid ID contains path traversal characters.")
    
    if args.from_insight_cluster:
        try:
            from enzymes.insight_correlator import cluster_insights
        except ImportError:
            from insight_correlator import cluster_insights
        workspace = resolve_workspace(__file__)
        clusters = cluster_insights(workspace)
        if not clusters:
            print('No insight clusters found.')
            return
        for cluster in clusters:
            path = create_cell_from_insight_cluster(cluster, workspace)
            print(f'✅ Created from cluster: {os.path.relpath(path, workspace)}')
        return

    if not args.description:
        parser.error('description is required unless --from-insight-cluster is used')

    print(f'🧬 Generating cell from description...')
    
    provider_name = None if args.provider == 'auto' else args.provider
    cell_content = create_cell_from_description(
        args.description,
        domain_hint=args.domain,
        cell_type=args.type,
        provider_name=provider_name
    )
    
    if args.dry_run:
        print('\n--- Generated Cell ---')
        print(cell_content)
        return
    
    # Parse the generated YAML to determine type and create filename
    try:
        if cell_content.startswith('```'):
            # Strip markdown code fences if present
            cell_content = cell_content.split('\n', 1)[1]
            if cell_content.rstrip().endswith('```'):
                cell_content = cell_content.rstrip()[:-3].rstrip()
        
        if cell_content.startswith('---'):
            yaml_block = cell_content[3:cell_content.find('---', 3)]
            fm = yaml.safe_load(yaml_block)
        else:
            print('Warning: Could not parse generated YAML frontmatter')
            fm = {}
    except Exception as e:
        print(f'Warning: YAML parse error: {e}')
        fm = {}
    
    raw_cell_type = str(fm.get('type', 'vacuole'))
    cell_type = re.sub(r'[^a-zA-Z0-9_\-]', '', os.path.basename(raw_cell_type)) or 'vacuole'
    hypothesis = fm.get('hypothesis', args.description)
    
    # Generate filename
    if args.id:
        slug = re.sub(r'[^a-zA-Z0-9_\-]', '', os.path.basename(args.id))
    else:
        # Create slug from hypothesis
        slug = re.sub(r'[^a-z0-9]+', '-', hypothesis.lower())[:50].strip('-')
    
    filename = f'{cell_type}-{slug}.md' if not slug.startswith(cell_type) else f'{slug}.md'
    filename = os.path.basename(filename)
    
    # Determine target directory
    workspace = resolve_workspace(__file__)
    type_dirs = {
        'wall': 'walls', 'membrane': 'membranes', 'vacuole': 'vacuoles',
        'chloroplast': 'chloroplasts', 'plasmodesmata': 'plasmodesmata'
    }
    target_dir = os.path.join(workspace, '.soma', 'cells', type_dirs.get(cell_type, 'vacuoles'))
    os.makedirs(target_dir, exist_ok=True)
    
    filepath = os.path.realpath(os.path.join(target_dir, filename))
    if not filepath.startswith(os.path.realpath(target_dir) + os.sep):
        raise ValueError(f"Path traversal detected for filename '{filename}'")
    
    try:
        os.unlink(filepath)
    except OSError:
        pass
    fd = os.open(filepath, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with open(fd, 'w', encoding="utf-8") as f:
        f.write(cell_content)
    
    rel_path = os.path.relpath(filepath, workspace)
    print(f'✅ Created: {rel_path}')
    print(f'   Type: {cell_type}')
    print(f'   Hypothesis: {hypothesis[:80]}')
    
    if args.json:
        print(json.dumps({
            'path': rel_path,
            'type': cell_type,
            'hypothesis': hypothesis,
            'filename': filename
        }, indent=2))


if __name__ == '__main__':
    # A cp1252 stdout can't encode this script's symbols (BUG-038).
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(errors='replace')
    main()
