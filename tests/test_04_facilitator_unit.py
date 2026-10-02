import sys
import importlib.util

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

# Because folder names start with numbers, we must dynamically import
test_runner = load_module("test_runner", "agents/04_facilitator/test_runner.py")

def test_extract_code_python():
    markdown = "Some text\n```python\nprint('hello')\n```\nMore text."
    res = test_runner.extract_code(markdown)
    assert res is not None
    assert res["language"] == "python"
    assert res["code"] == "print('hello')"
    
def test_extract_code_sql():
    markdown = "Some text\n```sql-setup\nCREATE TABLE users(id INT);\n```\n```sql\nSELECT * FROM users;\n```"
    res = test_runner.extract_code(markdown)
    assert res is not None
    assert res["language"] == "sql"
    assert res["code"] == "SELECT * FROM users;"
    assert res["setup"] == "CREATE TABLE users(id INT);"

def test_run_python_success():
    res = test_runner.run_python("print('success')")
    assert res["success"] is True
    assert "success" in res["stdout"]

def test_run_python_error():
    res = test_runner.run_python("print(1/0)")
    assert res["success"] is False
    assert "ZeroDivisionError" in res["stdout"]

def test_run_sql_success():
    res = test_runner.run_sql("CREATE TABLE test(id INT); INSERT INTO test VALUES (1);", "SELECT * FROM test;")
    assert res["success"] is True
    assert "1" in res["stdout"]

def test_run_sql_error():
    res = test_runner.run_sql("", "SELECT * FROM nonexistent;")
    assert res["success"] is False
    assert "SQL Error: no such table" in res["stdout"]
