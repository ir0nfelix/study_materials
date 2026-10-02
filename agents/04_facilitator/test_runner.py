import sys
import os
import json
import re
import tempfile
import subprocess
import sqlite3

def extract_code(markdown_text):
    if not markdown_text:
        return None
        
    result = {"language": None, "code": "", "setup": ""}
    
    # Check for python
    python_match = re.search(r'```python\n(.*?)\n```', markdown_text, re.DOTALL)
    if python_match:
        result["language"] = "python"
        result["code"] = python_match.group(1).strip()
        return result
        
    # Check for SQL
    sql_match = re.search(r'```sql\n(.*?)\n```', markdown_text, re.DOTALL)
    if sql_match:
        result["language"] = "sql"
        result["code"] = sql_match.group(1).strip()
        
        setup_match = re.search(r'```sql-setup\n(.*?)\n```', markdown_text, re.DOTALL)
        if setup_match:
            result["setup"] = setup_match.group(1).strip()
            
        return result
        
    return None

def run_python(code):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_name = f.name
        
    try:
        proc = subprocess.run(
            [sys.executable, temp_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        if proc.returncode == 0:
            return {"success": True, "stdout": proc.stdout}
        else:
            return {"success": False, "stdout": proc.stderr}
    except subprocess.TimeoutExpired:
        return {"success": False, "stdout": "Timeout Error"}
    except Exception as e:
        return {"success": False, "stdout": str(e)}
    finally:
        if os.path.exists(temp_name):
            os.remove(temp_name)

def run_sql(setup_code, query_code):
    try:
        conn = sqlite3.connect(':memory:')
        if setup_code:
            conn.executescript(setup_code)
            
        cursor = conn.execute(query_code)
        if cursor.description:
            rows = cursor.fetchall()
            output = "\n".join(str(row) for row in rows)
        else:
            output = "Query executed successfully with no output."
            
        conn.close()
        return {"success": True, "stdout": output}
    except sqlite3.Error as e:
        return {"success": False, "stdout": f"SQL Error: {e}"}
    except Exception as e:
        return {"success": False, "stdout": str(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: test_runner.py <path_to_processing_json>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
        
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    expert_solution = data.get("expert_solution", "")
    code_info = extract_code(expert_solution)
    
    if not code_info:
        test_results = {"success": False, "stdout": "No executable code found"}
    elif code_info["language"] == "python":
        test_results = run_python(code_info["code"])
    elif code_info["language"] == "sql":
        test_results = run_sql(code_info["setup"], code_info["code"])
    else:
        test_results = {"success": False, "stdout": "Unsupported language or no code found"}
        
    data["test_results"] = test_results
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    basename = os.path.basename(file_path)
    if basename.endswith('.processing'):
        basename = basename[:-11]
        
    cache_dir = os.environ.get("APP_CACHE_DIR", ".cache")
    final_dir = os.path.join(cache_dir, "03_pending_final")
    os.makedirs(final_dir, exist_ok=True)
    
    final_path = os.path.join(final_dir, basename)
    os.rename(file_path, final_path)
    print(f"Facilitator tested and moved {basename} to final queue. Success: {test_results['success']}")

if __name__ == "__main__":
    main()
