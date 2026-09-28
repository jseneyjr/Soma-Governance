#!/usr/bin/env python3
"""Natural Language Cell Creation via Gemini API.

Takes a plain English description and generates a governance cell with
proper YAML frontmatter, hypothesis, prediction, and falsification.
"""
import os, sys, argparse, json, subprocess
from prism_resolve import resolve_workspace

def resolve_api_key(workspace):
    """Resolve Gemini API key from multiple sources."""
    # 1. Environment variable
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if key:
        return key
    
    # 2. steering.conf
    conf_path = os.path.join(workspace, 'steering.conf')
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('GEMINI_API_KEY=') and not line.startswith('#'):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    
    # 3. .prism/credentials.conf (gitignored)
    creds_path = os.path.join(workspace, '.prism', 'credentials.conf')
    if os.path.exists(creds_path):
        with open(creds_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('GEMINI_API_KEY=') and not line.startswith('#'):
                    return line.split('=', 1)[1].strip().strip('"').strip("'")
    
    # 4. No key found
    return None

def create_cell_from_description(description, domain_hint=None, cell_type=None):
    """Use Gemini to generate cell YAML from natural language."""
    try:
        from google import genai
    except ImportError:
        print('Error: google-genai package required. Install with: pip install google-genai')
        sys.exit(1)
    
    workspace = resolve_workspace(__file__)
    
    api_key = resolve_api_key(workspace)
    if api_key:
        client = genai.Client(api_key=api_key)
    else:
        # Try Application Default Credentials
        try:
            client = genai.Client()
        except Exception:
            print('Error: No Gemini API key found. Configure one of:')
            print('  1. Set GEMINI_API_KEY environment variable')
            print('  2. Add GEMINI_API_KEY=... to steering.conf')
            print('  3. Add GEMINI_API_KEY=... to .prism/credentials.conf')
            print('  4. Set up Google Application Default Credentials')
            sys.exit(1)
    
    # Load existing cells as examples
    import glob, yaml
    examples = []
    cells_dir = os.path.join(workspace, '.prism', 'cells')
    if os.path.isdir(cells_dir):
        for cell_file in glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True):
            if os.path.basename(cell_file) == 'README.md': continue
            try:
                with open(cell_file) as f:
                    content = f.read()
                if content.startswith('---'):
                    examples.append(content[:500])  # Truncate for context
            except Exception: pass
    
    example_text = '\n---\n'.join(examples[:3]) if examples else 'No existing cells found.'
    
    domain_context = f'\nDomain hint: {domain_hint}' if domain_hint else ''
    type_hint = f'\nPreferred cell type: {cell_type}' if cell_type else ''
    
    prompt = f"""You are a governance cell generator for Prism AI Steering.

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
    
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    
    return response.text.strip()


def main():
    parser = argparse.ArgumentParser(
        description='Create governance cells from natural language descriptions using Gemini'
    )
    parser.add_argument('description', help='Natural language description of the governance concern')
    parser.add_argument('--domain', help='Domain hint (e.g., rl, web, infra, data)')
    parser.add_argument('--type', choices=['wall', 'vacuole', 'membrane', 'chloroplast', 'plasmodesmata'],
                       help='Preferred cell type')
    parser.add_argument('--id', help='Short ID for the cell filename')
    parser.add_argument('--dry-run', action='store_true', help='Print generated cell without creating file')
    parser.add_argument('--json', action='store_true', help='Output metadata as JSON')
    args = parser.parse_args()
    
    print(f'🧬 Generating cell from description...')
    cell_content = create_cell_from_description(
        args.description,
        domain_hint=args.domain,
        cell_type=args.type
    )
    
    if args.dry_run:
        print('\n--- Generated Cell ---')
        print(cell_content)
        return
    
    # Parse the generated YAML to determine type and create filename
    import yaml
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
    
    cell_type = fm.get('type', 'vacuole')
    hypothesis = fm.get('hypothesis', args.description)
    
    # Generate filename
    if args.id:
        slug = args.id
    else:
        # Create slug from hypothesis
        import re
        slug = re.sub(r'[^a-z0-9]+', '-', hypothesis.lower())[:50].strip('-')
    
    filename = f'{cell_type}-{slug}.md' if not slug.startswith(cell_type) else f'{slug}.md'
    
    # Determine target directory
    workspace = resolve_workspace(__file__)
    type_dirs = {
        'wall': 'walls', 'membrane': 'membranes', 'vacuole': 'vacuoles',
        'chloroplast': 'chloroplasts', 'plasmodesmata': 'plasmodesmata'
    }
    target_dir = os.path.join(workspace, '.prism', 'cells', type_dirs.get(cell_type, 'vacuoles'))
    os.makedirs(target_dir, exist_ok=True)
    
    filepath = os.path.join(target_dir, filename)
    
    with open(filepath, 'w') as f:
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
    main()
