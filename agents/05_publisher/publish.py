import sys
import os
import json
import re

CYRILLIC_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
}

def transliterate(text):
    return "".join(CYRILLIC_MAP.get(c, c) for c in text.lower())

def generate_slug(task_id, title):
    transliterated = transliterate(title)
    clean_text = re.sub(r'[^a-z0-9]+', '-', transliterated).strip('-')
    return f"task-{task_id:03d}-python-{clean_text[:20]}"

def main():
    if len(sys.argv) < 2:
        print("Usage: publish.py <path_to_processing_json>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
        
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    docs_dir = os.path.join("docs", "livecoding")
    os.makedirs(docs_dir, exist_ok=True)
    python_md_path = os.path.join(docs_dir, "python.md")
    
    # Check current task number
    next_task_id = 1
    if os.path.exists(python_md_path):
        with open(python_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r'^## Задача (\d+):', content, re.MULTILINE)
            if matches:
                next_task_id = max(int(m) for m in matches) + 1
    else:
        # Create empty file if not exists
        with open(python_md_path, 'w', encoding='utf-8') as f:
            f.write("# Python Livecoding\n\n")

    title = data.get("title", "Unknown Task")
    condition = data.get("condition", "Текст условия отсутствует.")
    expert_solution = data.get("expert_solution", "Нет эталонного решения.")
    url = data.get("url", "https://youtube.com")
    
    slug = generate_slug(next_task_id, title)
    
    md_content = f"\n## Задача {next_task_id}: {title} {{#{slug}}}\n"
    md_content += f"**Источник:** [Видео]({url})\n\n"
    md_content += f"### Условие\n{condition}\n\n"
    md_content += f"### Эталонное решение (AI)\n{expert_solution}\n\n"
    
    test_results = data.get("test_results")
    if test_results and "stdout" in test_results:
        md_content += "#### Логи тестов (Facilitator)\n"
        md_content += f"```text\n{test_results['stdout']}\n```\n\n"
    
    with open(python_md_path, 'a', encoding='utf-8') as f:
        f.write(md_content)
        
    basename = os.path.basename(file_path)
    if basename.endswith('.processing'):
        basename = basename[:-11]
        
    cache_dir = os.environ.get("APP_CACHE_DIR", ".cache")
    completed_dir = os.path.join(cache_dir, "99_completed")
    os.makedirs(completed_dir, exist_ok=True)
    
    final_path = os.path.join(completed_dir, basename)
    os.rename(file_path, final_path)
    print(f"Publisher appended Task {next_task_id} to python.md and moved {basename} to completed queue.")

if __name__ == "__main__":
    main()
