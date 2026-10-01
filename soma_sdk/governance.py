"""Core Governance API."""
from __future__ import annotations

import json
import subprocess
import sys
import re
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None


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
        self.scripts_dir: Optional[Path] = self._find_scripts_dir()
    
    def _find_scripts_dir(self) -> Optional[Path]:
        """Locate Soma scripts directory."""
        candidates = [
            self.root / 'vendor' / 'soma' / 'enzymes',
            self.root / 'enzymes',
            Path(__file__).parent.parent / 'enzymes',
        ]
        for c in candidates:
            if c.is_dir() and (c / 'cell_fitness.py').exists():
                return c
        return None
    
    def _run_script(self, script_name: str, *args: str, json_output: bool = True) -> dict[str, Any] | str:
        """Run a Soma enzyme script and return parsed output."""
        if not self.scripts_dir:
            raise RuntimeError('Soma enzymes directory not found')
        
        script = self.scripts_dir / script_name
        if not script.exists():
            raise FileNotFoundError(f'Script not found: {script_name}')
        
        if script.suffix == '.sh':
            cmd = ['bash', str(script)] + list(args)
        else:
            cmd = [sys.executable, str(script)] + list(args)
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
    
    # === Cell Management ===
    
    def list_cells(self) -> list[dict[str, Any]]:
        """List all immune cells."""
        cells = []
        if not self.cells_dir.exists():
            return cells
        for cell_file in self.cells_dir.rglob('*.md'):
            if cell_file.name == 'README.md': continue
            try:
                content = cell_file.read_text()
                if not content.startswith('---'): continue
                fm = yaml.safe_load(content[3:content.find('---', 3)])
                fm['_name'] = cell_file.stem
                fm['_path'] = str(cell_file.relative_to(self.root))
                cells.append(fm)
            except Exception: pass
        return cells
    
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
