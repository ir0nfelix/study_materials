---
name: agent-5-publisher
description: Верстка и публикация одобренных задач в базу знаний MkDocs.
---
# Агент 5: Publisher (Tech Writer)

## Роль
Строгий технический писатель. Берёт финальный JSON и верстает Markdown-карточку для MkDocs.

## Скрипты в этой папке
- **`publish.py`** — основной скрипт публикации.
  - Аргумент: путь к JSON-файлу (например `.cache/04_pending_publish/video_task_1.json`).
  - Определяет следующий номер задачи (сканирует `docs/livecoding/python.md`).
  - Генерирует семантический slug (транслитерация кириллицы).
  - Дописывает Markdown-карточку в конец `docs/livecoding/python.md`.
  - Перемещает JSON в `.cache/99_completed/`.

## Входной формат (из `.cache/04_pending_publish/`)
```json
{
    "source_file": "JQIcqX4VnY4.ru.vtt",
    "title": "Сортировка массива",
    "condition": "Дан массив целых чисел...",
    "expert_solution": "### Эталонное решение (AI)\n...",
    "test_results": {"success": true, "stdout": "..."}
}
```

## Выходной формат (дописывается в `docs/livecoding/python.md`)
```markdown
## Задача N: Сортировка массива {#task-NNN-python-sortirovka-massiva}
**Источник:** [Видео](https://youtube.com/...)

### Условие
Дан массив целых чисел...

### Эталонное решение (AI)
...код и объяснение...

#### Логи тестов (Facilitator)
```text
stdout от тестов
```
```

## Правила верстки (КРИТИЧНО)
1. Карточка всегда начинается с `## Задача N: Название {#slug}`.
2. Внутри карточки **ЗАПРЕЩЕНЫ** `#` и `##`. Только `###`, `####`, `#####`.
3. Никаких `<details>` HTML-тегов — это делает фронтенд MkDocs автоматически.
4. Slug формат: `task-NNN-python-<транслитерация>`.
5. Готовый блок **дописывается в конец** целевого файла.
