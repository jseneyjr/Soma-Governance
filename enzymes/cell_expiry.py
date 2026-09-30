#!/usr/bin/env python3
"""Cell Expiry Enforcement.

Audits all governance cells against their expiry_days and expiry_sessions
limits. Reports expired cells and optionally prunes them by adding an
expired_at marker to their frontmatter.

Usage:
    python3 enzymes/cell_expiry.py [workspace]
    python3 enzymes/cell_expiry.py [workspace] --prune
    python3 enzymes/cell_expiry.py [workspace] --json
    python3 enzymes/cell_expiry.py [workspace] --session-count 25
"""
import argparse
import glob
import json
import os
import sys
from datetime import datetime

import yaml
from soma_resolve import resolve_workspace


def audit_expiry(workspace, session_count=None):
    """Audit all cells for expiry violations.

    Args:
        workspace: Path to project root.
        session_count: Number of sessions elapsed (for expiry_sessions check).
            If None, session-based expiry is skipped.

    Returns:
        List of dicts with keys: cell_id, filepath, status, reason, details.
        status is one of: OK, EXPIRED, EXPIRY_WARNING, ALREADY_EXPIRED.
    """
    cells_dir = os.path.join(workspace, '.soma', 'cells')
    if not os.path.isdir(cells_dir):
        return []

    results = []
    now = datetime.now()

    for md_file in sorted(glob.glob(os.path.join(cells_dir, '**', '*.md'), recursive=True)):
        if os.path.basename(md_file) == 'README.md':
            continue

        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        if not content.startswith('---'):
            continue
        end = content.find('---', 3)
        if end == -1:
            continue

        try:
            metadata = yaml.safe_load(content[3:end]) or {}
        except Exception:
            continue

        cell_id = metadata.get('id', os.path.basename(md_file))
        cell_type = metadata.get('type', 'unknown')
        is_wall = cell_type == 'wall'

        # Skip already-expired cells
        if metadata.get('expired_at'):
            results.append({
                'cell_id': cell_id,
                'filepath': md_file,
                'status': 'ALREADY_EXPIRED',
                'reason': 'previously_pruned',
                'details': f"Expired at {metadata['expired_at']}",
            })
            continue

        expired = False
        reason = None
        details = None

        # Check expiry_days
        expiry_days = metadata.get('expiry_days')
        created_str = metadata.get('created')
        if expiry_days and created_str:
            try:
                fmt = "%Y-%m-%dT%H:%M:%SZ" if 'T' in str(created_str) else "%Y-%m-%d"
                created_date = datetime.strptime(str(created_str), fmt)
                days_elapsed = (now - created_date).days
                if days_elapsed > expiry_days:
                    expired = True
                    reason = 'expiry_days'
                    details = f"{days_elapsed} days elapsed (limit: {expiry_days})"
            except Exception:
                pass

        # Check expiry_sessions (only if not already expired by days)
        if not expired and session_count is not None:
            expiry_sessions = metadata.get('expiry_sessions')
            if expiry_sessions and session_count > expiry_sessions:
                expired = True
                reason = 'expiry_sessions'
                details = f"{session_count} sessions elapsed (limit: {expiry_sessions})"

        if expired:
            status = 'EXPIRY_WARNING' if is_wall else 'EXPIRED'
        else:
            status = 'OK'

        results.append({
            'cell_id': cell_id,
            'filepath': md_file,
            'status': status,
            'reason': reason,
            'details': details,
        })

    return results


def prune_expired(workspace, audit_results):
    """Add expired_at marker to expired cells.

    Args:
        workspace: Path to project root.
        audit_results: Output from audit_expiry().

    Returns:
        Number of cells pruned.
    """
    pruned = 0
    now_str = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

    for result in audit_results:
        if result['status'] != 'EXPIRED':
            continue

        filepath = result['filepath']
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        if not content.startswith('---'):
            continue
        end = content.find('---', 3)
        if end == -1:
            continue

        try:
            metadata = yaml.safe_load(content[3:end]) or {}
        except Exception:
            continue

        metadata['expired_at'] = now_str
        metadata['expired_reason'] = result.get('reason', 'unknown')

        new_fm = yaml.dump(metadata, default_flow_style=False, sort_keys=False)
        body = content[end + 3:]
        new_content = '---\n' + new_fm + '---' + body

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        pruned += 1

    return pruned


def main():
    parser = argparse.ArgumentParser(
        description='Audit and enforce cell expiry limits'
    )
    parser.add_argument('workspace', nargs='?', default='.',
                        help='Project workspace root')
    parser.add_argument('--prune', action='store_true',
                        help='Add expired_at marker to expired cells')
    parser.add_argument('--json', action='store_true',
                        help='Output results as JSON')
    parser.add_argument('--session-count', type=int, default=None,
                        help='Number of sessions elapsed (for session-based expiry)')
    args = parser.parse_args()

    workspace = resolve_workspace(args.workspace)
    results = audit_expiry(workspace, session_count=args.session_count)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        expired = [r for r in results if r['status'] in ('EXPIRED', 'EXPIRY_WARNING')]
        ok = [r for r in results if r['status'] == 'OK']
        already = [r for r in results if r['status'] == 'ALREADY_EXPIRED']

        print(f"Cells audited: {len(results)}")
        print(f"  OK: {len(ok)}")
        print(f"  Expired: {len(expired)}")
        print(f"  Already pruned: {len(already)}")

        if expired:
            print("\nExpired cells:")
            for r in expired:
                icon = "⚠️" if r['status'] == 'EXPIRY_WARNING' else "❌"
                print(f"  {icon} {r['cell_id']}: {r['details']} ({r['reason']})")

    if args.prune:
        pruned = prune_expired(workspace, results)
        print(f"\nPruned {pruned} cell(s)")

    return 0 if not any(r['status'] == 'EXPIRED' for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
