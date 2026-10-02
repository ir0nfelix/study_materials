---
name: agent-3-expert
description: Генерация эталонных решений задач через LLM (OpenRouter).
---
# Агент 3: Expert (Senior Engineer)

## Роль
Senior AI Software Engineer. Берёт условие задачи и генерирует эталонное решение с кодом, анализом сложности и детальным объяснением.

## Скрипты в этой папке
- **`solve.py`** — основной скрипт генерации решений.
  - Аргумент: путь к JSON-файлу задачи (например `.cache/02_pending_expert/video_task_1.json`).
  - Читает `title` и `condition` из JSON.
  - Отправляет в `anthropic/claude-3.5-sonnet` через OpenRouter.
  - Записывает решение в поле `expert_solution` того же JSON.
  - Перемещает файл в `.cache/02b_pending_testing/`.

## Входной формат (из `.cache/02_pending_expert/`)
```json
{
    "source_file": "JQIcqX4VnY4.ru.vtt",
    "title": "Сортировка массива",
    "condition": "Дан массив целых чисел..."
}
```

## Выходной формат (в `.cache/02b_pending_testing/`)
Тот же JSON, обогащённый полем:
```json
{
    "expert_solution": "### Эталонное решение (AI)\n\n#### Анализ\nTime: O(n log n)..."
}
```

## Переменные окружения
- `OPENROUTER_API_KEY` — читается из `.env` в корне проекта.

## Формат решения (КРИТИЧНО)
- Начинается с `### Эталонное решение (AI)`.
- Внутри допустимы только `####` и `#####` (НЕ `#` или `##`).
- Содержит: анализ сложности, оптимальный код (Python/Go/Java), объяснение алгоритма.
