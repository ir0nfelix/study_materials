---
name: agent-4-facilitator
description: Безопасный запуск и тестирование сгенерированного кода (Python, SQL).
---
# Агент 4: Facilitator (QA Automation)

## Роль
QA-инженер. Извлекает код из решения Эксперта, запускает его в песочнице и сохраняет результаты.

## Скрипты в этой папке
- **`test_runner.py`** — основной скрипт тестирования.
  - Аргумент: путь к JSON-файлу (например `.cache/02b_pending_testing/video_task_1.json`).
  - Извлекает блоки кода из `expert_solution` (поддерживает Python и SQL).
  - Python: запускает через `subprocess` с таймаутом 5 секунд.
  - SQL: выполняет в in-memory SQLite.
  - Записывает результаты в поле `test_results` того же JSON.
  - Перемещает файл в `.cache/03_pending_final/`.

## Входной формат (из `.cache/02b_pending_testing/`)
JSON с полем `expert_solution`, содержащим блоки кода в формате Markdown.

## Выходной формат (в `.cache/03_pending_final/`)
Тот же JSON, обогащённый полем:
```json
{
    "test_results": {
        "success": true,
        "stdout": "4\n[1, 2, 3]\n"
    }
}
```

## Поддерживаемые языки
- **Python** — извлекает ```python блоки, запускает через `sys.executable`.
- **SQL** — извлекает ```sql блоки, поддерживает ```sql-setup для DDL.
