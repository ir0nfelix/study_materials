import sys
import os
import json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from infrastructure.llm_client import get_client, get_model

def process_task(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
        
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    client = get_client()
    
    task_title = data.get("title", "Unknown Task")
    task_condition = data.get("condition", "")
    target_language = data.get("target_language", "Python")
    
    prompt = f"""
    Ты Senior AI Software Engineer. Тебе дана задача с технического собеседования.
    Название: {task_title}
    Условие: {task_condition}
    
    Твоя задача: Написать эталонное решение (AI).
    Формат ответа:
    1. Краткий анализ задачи (Time/Space complexity).
    2. Оптимальный код решения СТРОГО НА {target_language}.
    3. Детальное объяснение, почему выбран именно этот алгоритм.
    
    Оформи ответ красиво в формате Markdown. Начни свой ответ с заголовка: ### Эталонное решение (AI)
    """
    
    try:
        response = client.chat.completions.create(
            model=get_model("expert"),
            messages=[
                {"role": "system", "content": "You are a Senior Software Engineer acting as an Expert Interviewer."},
                {"role": "user", "content": prompt}
            ]
        )
        expert_solution = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Expert Error: {e}")
        sys.exit(1)
        
    data["expert_solution"] = expert_solution
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    basename = os.path.basename(file_path)
    if basename.endswith('.processing'):
        basename = basename[:-11]
        
    cache_dir = os.environ.get("APP_CACHE_DIR", ".cache")
    final_dir = os.path.join(cache_dir, "02b_pending_testing")
    os.makedirs(final_dir, exist_ok=True)
    
    final_path = os.path.join(final_dir, basename)
    os.rename(file_path, final_path)
    print(f"Expert solved and moved {basename} to testing queue.")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: solve.py <path_to_processing_json>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    process_task(file_path)

if __name__ == "__main__":
    main()
