"""Core Governance API."""
from __future__ import annotations

import json
import subprocess
import sys
import re
from pathlib import Path
from typing import Any, Optional

from soma_core.cell_inventory import CellInventoryError, inventory_cells
from soma_core.frontmatter import parse_frontmatter

TYPE_TRANSLATION_MAP: dict[str, str] = {
    "safety-guard": "wall",
    "learned-trap": "vacuole",
    "agent-persona": "chloroplast",
    "escalation-boundary": "membrane",
    "contract-bridge": "plasmodesmata",
    "wall": "wall",
    "vacuole": "vacuole",
    "chloroplast": "chloroplast",
    "membrane": "membrane",
    "plasmodesmata": "plasmodesmata",
}

VALID_SOURCES = ('ci', 'manual', 'mcp', 'session')


class Governance:
    """Soma governance interface.
    
    Usage:
        from soma_sdk import Governance
        gov = Governance(project_root='.')
        
        landscape = gov.fitness_landscape(bayesian=True)
        coverage = gov.coverage_report()
        replay = gov.replay(commits=20)
        grade = gov.grade()
    """
    
    def __init__(self, project_root: str | Path = '.') -> None:
        self.root: Path = Path(project_root).resolve()
        self.cells_dir: Path = self.root / '.soma' / 'cells'
        self.metrics_dir: Path = self.root / '.soma' / 'metrics'
    
    def _run_script(self, script_name: str, *args: str, json_output: bool = True) -> dict[str, Any] | str:
        """Run a Soma enzyme script and return parsed output."""
        import importlib.resources
        from contextlib import ExitStack
        
        with ExitStack() as stack:
            try:
                # Use importlib.resources to locate the script in the packaged 'enzymes' module
                ref = importlib.resources.files('enzymes').joinpath(script_name)
                script_path = stack.enter_context(importlib.resources.as_file(ref))
            except Exception as e:
                raise RuntimeError(f'Soma enzyme script not found or failed to load: {script_name} ({e})')
            
            if not script_path.exists():
                raise FileNotFoundError(f'Script not found: {script_name}')
            
            if script_path.suffix == '.sh':
                cmd = ['bash', str(script_path)] + list(args)
            else:
                cmd = [sys.executable, str(script_path)] + list(args)
            
            if json_output:
                cmd.append('--json')
            
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.root))
            
            if result.returncode != 0:
                err_msg = result.stderr.strip() or result.stdout.strip()
                if json_output:
                    return {'error': f'Command failed with exit code {result.returncode}', 'details': err_msg}
                else:
                    raise RuntimeError(f'Command failed with exit code {result.returncode}: {err_msg}')
                    
            if json_output and result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {'raw': result.stdout, 'error': 'JSON parse failed'}
            return result.stdout
    
    # === Cell & Rule Management ===
    
    def list_cells(self, cell_type: Optional[str] = None) -> list[dict[str, Any]]:
        """List immune cells, optionally filtered by cell_type or porcelain alias.

        Invalid cell contents remain visible as diagnostic records. Unsafe or
        unreadable inventory trees fail closed because callers cannot safely
        distinguish an empty tree from an incomplete one.
        """
        try:
            inventory = inventory_cells(str(self.root))
        except CellInventoryError as exc:
            raise RuntimeError(str(exc)) from exc

        canonical_filter = TYPE_TRANSLATION_MAP.get(cell_type, cell_type) if cell_type else None

        cells = []
        for entry in inventory.entries:
            relative_path = entry.relative_path
            cell_name = Path(relative_path).stem
            if Path(relative_path).name == 'README.md':
                continue

            if canonical_filter:
                parent_name = Path(relative_path).parent.name
                path_matches = (
                    parent_name in (canonical_filter, canonical_filter + 's')
                    or f"/{canonical_filter}/" in relative_path
                    or f"/{canonical_filter}s/" in relative_path
                )
            else:
                path_matches = True

            try:
                content = entry.content.decode('utf-8')
            except UnicodeDecodeError as exc:
                if not path_matches:
                    continue
                cells.append({
                    '_name': cell_name,
                    '_path': relative_path,
                    '_error': f'invalid UTF-8: {exc}',
                })
                continue

            frontmatter = parse_frontmatter(content)
            if frontmatter is None:
                if not path_matches:
                    continue
                cells.append({
                    '_name': cell_name,
                    '_path': relative_path,
                    '_error': 'malformed YAML frontmatter',
                })
                continue
            if not frontmatter:
                if not path_matches:
                    continue
                cells.append({
                    '_name': cell_name,
                    '_path': relative_path,
                    '_error': 'no frontmatter metadata',
                })
                continue

            if canonical_filter:
                entry_type = frontmatter.get('type')
                type_matches = (entry_type == canonical_filter) or path_matches
                if not type_matches:
                    continue

            frontmatter['_name'] = cell_name
            frontmatter['_path'] = relative_path
            cells.append(frontmatter)
        return cells

    def list_rules(self, rule_type: Optional[str] = None) -> list[dict[str, Any]]:
        """List active rules (porcelain alias for list_cells)."""
        return self.list_cells(cell_type=rule_type)

    def record_outcome(
        self,
        rule_id: str,
        success: bool,
        metric: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Record an empirical rule outcome (tp/fp) in-process via atomic evidence telemetry.
        
        Underlying data updates Wilson confidence scores and Bayesian fitness.
        """
        signal_type = "tp" if success else "fp"
        merged_metric = dict(metric or {})
        source = kwargs.pop("source", "manual")
        if source not in VALID_SOURCES:
            raise ValueError(f"Invalid telemetry source '{source}'. Must be one of: {', '.join(VALID_SOURCES)}")
        merged_metric.update(kwargs)
        try:
            from soma_core.telemetry import append_signal
            return append_signal(
                workspace=str(self.root),
                cell_name=rule_id,
                signal_type=signal_type,
                source=source,
                metadata={"metric": merged_metric} if merged_metric else {},
            )
        except Exception:
            raw_output = self.signal(rule_id, signal_type, metric=merged_metric)
            return {
                "cell": rule_id,
                "signal": signal_type,
                "source": source,
                "status": "fallback_recorded",
                "raw": str(raw_output),
            }
    
    def create_cell(
        self,
        hypothesis: str,
        type: str = 'vacuole',
        target_paths: Optional[list[str]] = None,
        minimum_mode: str = 'breeze',
        tags: Optional[list[str]] = None,
        cell_id: Optional[str] = None,
    ) -> dict[str, Any] | str:
        """Create a new immune cell."""
        raw_slug = cell_id or hypothesis[:40]
        safe_slug = re.sub(r'[^a-zA-Z0-9_.-]', '-', raw_slug).strip('-')
        
        args = ['--id', safe_slug, '--type', type,
                '--hypothesis', hypothesis]
        if target_paths:
            args.extend(['--target-paths', ','.join(target_paths)])
        if minimum_mode != 'breeze':
            args.extend(['--minimum-mode', minimum_mode])
        if tags:
            args.extend(['--tags', ','.join(tags)])
        
        return self._run_script('cell_create.sh', *args, json_output=False)
    
    def create_cell_from_description(
        self, description: str, domain: Optional[str] = None, cell_type: Optional[str] = None,
    ) -> dict[str, Any] | str:
        """Create a cell using natural language via Gemini API."""
        args = [description]
        if domain:
            args.extend(['--domain', domain])
        if cell_type:
            args.extend(['--type', cell_type])
        return self._run_script('cell_create_nl.py', *args, json_output=False)
    
    def signal(
        self, cell_name: str, signal_type: str, metric: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any] | str:
        """Send a fitness signal to a cell.
        
        Args:
            cell_name: Name of the cell to signal
            signal_type: 'tp' (true positive) or 'fp' (false positive)
            metric: Optional dict of metrics, e.g. {'survival_day': 12}
        """
        args = [cell_name, signal_type]
        if metric:
            for k, v in metric.items():
                args.extend(['--metric', f'{k}={v}'])
        
        return self._run_script('cell_signal.sh', *args, json_output=False)
    
    # === Analysis ===
    
    def fitness_landscape(self, bayesian: bool = False) -> dict[str, Any] | str:
        """Get fitness scores for all cells."""
        args = []
        if bayesian:
            args.append('--bayesian')
        return self._run_script('cell_fitness.py', *args)
    
    def coverage_report(self, exclude: Optional[str] = None) -> dict[str, Any] | str:
        """Get cell coverage report."""
        args = []
        if exclude:
            args.extend(['--exclude', exclude])
        return self._run_script('cell_coverage.py', *args)
    
    def replay(self, commits: int = 20) -> dict[str, Any] | str:
        """Replay governance against historical commits."""
        return self._run_script('immune_replay.py', '--commits', str(commits))
    
    def trends(self, days: int = 30) -> dict[str, Any] | str:
        """Get cross-session governance trends."""
        return self._run_script('immune_trends.py', '--days', str(days))
    
    def grade(self) -> dict[str, Any] | str:
        """Get governance report card."""
        return self._run_script('immune_grade.py')
    
    def quorum(self, threshold: int = 3) -> dict[str, Any] | str:
        """Check for quorum (systemic multi-cell triggers)."""
        return self._run_script('cell_quorum.py', '--threshold', str(threshold))
    
    def dependencies(self, format: str = 'text') -> dict[str, Any] | str:
        """Get cell dependency graph."""
        return self._run_script('cell_deps.py', '--format', format, json_output=(format != 'mermaid'))
    
    def scan(self) -> dict[str, Any] | str:
        """Scan current diff against cells."""
        return self._run_script('cell_scan.py')

    def entropy(self) -> dict[str, Any] | str:
        """Compute immune entropy across all cells."""
        return self._run_script('immune_entropy.py')

    def adversarial(self, cell_name: Optional[str] = None) -> dict[str, Any] | str:
        """Run adversarial stress test against a cell.

        Args:
            cell_name: Optional name of the cell to test. If omitted,
                       tests all cells.
        """
        args = [cell_name] if cell_name else []
        return self._run_script('cell_adversarial.py', *args)
