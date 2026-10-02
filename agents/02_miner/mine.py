import sys
import os
import json
import time
from dotenv import load_dotenv
from openai import OpenAI

def main():
    if len(sys.argv) < 2:
        print("Usage: mine.py <path_to_txt>")
        sys.exit(1)
        
    txt_path = sys.argv[1]
    
    if not os.path.exists(txt_path):
        print(f"File not found: {txt_path}")
        sys.exit(1)
        
    filename = os.path.basename(txt_path)
    video_id = os.path.splitext(filename)[0]
    if video_id.endswith(".ru") or video_id.endswith(".en"):
        video_id = video_id[:-3]
    
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    cache_dir = os.environ.get("APP_CACHE_DIR", ".cache")
    triage_dir = os.path.join(cache_dir, "01_pending_triage")
    os.makedirs(triage_dir, exist_ok=True)
    
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    load_dotenv(os.path.join(root_dir, ".env"))
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in .env")
        sys.exit(1)
        
    # Patch proxy schemes for httpx compatibility
    for p_var in ['http_proxy', 'https_proxy', 'all_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY']:
        if p_var in os.environ and os.environ[p_var].startswith('socks://'):
            os.environ[p_var] = os.environ[p_var].replace('socks://', 'socks5://', 1)
            
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    
    prompt = """
    Ты Senior Technical Analyst. Тебе на вход подается сырой транскрипт (субтитры) технического собеседования.
    Твоя задача: найти все технические, алгоритмические или System Design задачи, которые кандидат решал во время собеседования.
    Игнорируй болтовню, HR-вопросы, вопросы про опыт и теорию (если она не является частью практической задачи).
    
    Выведи результат СТРОГО в формате JSON-объекта с единственным ключом "tasks", который содержит массив найденных задач.
    Каждый элемент массива должен содержать:
    "title" - Краткое, но ёмкое название задачи (например: "Сортировка массива", "System Design: Мессенджер").
    "condition" - Полное и детальное условие задачи, восстановленное из речи интервьюера (без мусора из субтитров, отформатированное и читаемое).
    
    Если задач не найдено, верни пустой массив в ключе "tasks": {"tasks": []}
    """
    
    print(f"Miner: Sending {len(content)} chars to LLM for {video_id}...")
    try:
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"}
        )
        
        reply = response.choices[0].message.content.strip()
        
        # OpenRouter sometimes wraps JSON in markdown blocks despite json_object format
        if reply.startswith("```json"):
            reply = reply[7:-3].strip()
        elif reply.startswith("```"):
            reply = reply[3:-3].strip()
            
        data = json.loads(reply)
        tasks = data.get("tasks", [])
        
    except Exception as e:
        print(f"Miner Error: {e}")
        sys.exit(1)
        
    if not isinstance(tasks, list):
        print("Miner Error: LLM did not return a valid 'tasks' list")
        sys.exit(1)
        
    print(f"Miner: Found {len(tasks)} tasks via LLM.")
    
    for i, task in enumerate(tasks, 1):
        task_data = {
            "source_file": filename,
            "title": task.get("title", f"Задача {i}"),
            "condition": task.get("condition", "")
        }
        
        task_path = os.path.join(triage_dir, f"{video_id}_task_{i}.json")
        with open(task_path, 'w', encoding='utf-8') as f:
            json.dump(task_data, f, ensure_ascii=False, indent=4)
            
    marker_path = f"{txt_path}.processed"
    with open(marker_path, 'w', encoding='utf-8') as f:
        f.write(str(time.time()))
        
    print(f"Miner fully processed {txt_path}.")

if __name__ == "__main__":
    main()
