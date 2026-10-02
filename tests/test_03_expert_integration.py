import json
import importlib.util
import sys

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

expert_solve = load_module("expert_solve", "agents/03_expert/solve.py")

def test_expert_process_task(isolated_cache):
    expert_dir = isolated_cache / "02_pending_expert"
    testing_dir = isolated_cache / "02b_pending_testing"
    
    # Create test processing file
    task_file = expert_dir / "vid123_task_1.json.processing"
    task_file.write_text(json.dumps({"title": "Test Task"}), encoding="utf-8")
    
    # Call the logic
    result = expert_solve.process_task(str(task_file))
    
    assert result is True
    # Assert original file is gone
    assert not task_file.exists()
    
    # Assert final file is created
    final_file = testing_dir / "vid123_task_1.json"
    assert final_file.exists()
    
    # Assert content
    data = json.loads(final_file.read_text(encoding="utf-8"))
    assert "expert_solution" in data
    assert "Мок решение" in data["expert_solution"]
