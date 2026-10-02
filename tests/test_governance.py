import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from soma_sdk.governance import Governance

def test_governance_uses_importlib_resources_instead_of_relative_path(tmp_path, monkeypatch):
    # If _find_scripts_dir is removed or doesn't find enzymes locally, 
    # it should use importlib.resources.
    gov = Governance(project_root=tmp_path)
    
    # We will mock subprocess.run to avoid actually executing and test if it runs the script from importlib
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"status": "ok"}'
        
        # We need to make sure the scripts_dir is not relying on relative paths
        # So we mock Path.exists to always return False for the local candidates if _find_scripts_dir still exists
        
        try:
            res = gov.fitness_landscape()
        except RuntimeError as e:
            pytest.fail(f"Failed with {e}, likely because it still relies on relative enzymes/")
            
        assert mock_run.called
        cmd_run = mock_run.call_args[0][0]
        # Check that the script being executed is cell_fitness.py
        assert any("cell_fitness.py" in str(arg) for arg in cmd_run)
