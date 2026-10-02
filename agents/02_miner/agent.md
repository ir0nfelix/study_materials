---
name: agent-2-miner
description: Извлечение технических задач из сырых субтитров через LLM (OpenRouter).
---
# Агент 2: Miner (Technical Analyst)

## Роль
Технический аналитик. Читает сырые субтитры из `raw_transcripts/` и через LLM находит алгоритмические задачи и вопросы по System Design. Игнорирует HR-вопросы и теорию без практики.

## Скрипты в этой папке
- **`mine.py`** — основной скрипт извлечения задач.
  - Аргумент: путь к `.vtt` или `.txt` файлу (например `raw_transcripts/JQIcqX4VnY4.ru.vtt`).
  - Отправляет содержимое в `anthropic/claude-3.5-sonnet` через OpenRouter.
  - LLM возвращает JSON с массивом задач (`title` + `condition`).
  - Для каждой задачи создаёт отдельный JSON в `.cache/01_pending_triage/`.
  - Создаёт маркер `<filename>.processed` для предотвращения повторной обработки.

## Входной формат
Текстовый файл `.vtt` (субтитры WebVTT) или `.txt` из `raw_transcripts/`.

## Выходной формат (Maildir Pattern)
Для каждой найденной задачи — файл `.cache/01_pending_triage/<video_id>_task_<N>.json`:
```json
{
    "source_file": "JQIcqX4VnY4.ru.vtt",
    "title": "Сортировка массива пузырьком",
    "condition": "Дан массив целых чисел. Необходимо отсортировать его..."
}
```

## Переменные окружения
- `OPENROUTER_API_KEY` — читается из `.env` в корне проекта.

## Важные ограничения
- VPN **должен быть включён** при работе (обращение к OpenRouter API).
