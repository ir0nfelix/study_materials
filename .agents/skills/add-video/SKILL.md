---
name: add-video
description: Скачивание субтитров YouTube-видео и извлечение технических задач через LLM. Триггер: /add <url>
---

# Skill: Добавить видео (`/add`)

## Триггер
Пользователь пишет в чат: `/add <YouTube URL>` или `/add <Playlist URL>`

## Инструменты (скрипты)
- `agents/01_ingestion/download.py <video_id>` — скачивает субтитры (cookies + impersonate + deno)
- `agents/02_miner/mine.py <path_to_vtt>` — отправляет транскрипт в LLM, извлекает задачи
- `infrastructure/cli_broker.py` — Ray-воркер-пул для параллельной обработки

## Переменные окружения
- `OPENROUTER_API_KEY` — читается из `.env` в корне проекта (используется в `mine.py`)

## Рабочий процесс

### Сценарий A: Одно видео
1. Извлеки `video_id` из URL (часть после `?v=`).
2. Запусти скрипт скачивания напрямую:
   ```bash
   ./venv/bin/python agents/01_ingestion/download.py <video_id>
   ```
3. Дождись завершения. Проверь, что файл `.vtt` появился в `raw_transcripts/`.
4. Запусти Miner:
   ```bash
   ./venv/bin/python agents/02_miner/mine.py raw_transcripts/<video_id>.ru.vtt
   ```
5. Прочитай созданные JSON-файлы из `.cache/01_pending_triage/`.
6. Покажи пользователю найденные задачи (заголовок + условие).
7. Перейди к скиллу `review-tasks` для апрува и обработки.

### Сценарий B: Плейлист или пакетная загрузка (>5 видео)
1. Извлеки все `video_id` из плейлиста (через `yt-dlp --flat-playlist --print id <url>`).
2. Для каждого `video_id` создай JSON-файл в `.cache/00_pending_download/`:
   ```json
   {
     "url": "https://www.youtube.com/watch?v=<video_id>",
     "video_id": "<video_id>",
     "status": "pending"
   }
   ```
3. Запусти Ray-брокер фоновым процессом:
   ```bash
   ./venv/bin/python infrastructure/cli_broker.py
   ```
4. Сообщи пользователю: "Брокер запущен, N видео в очереди. Задачи будут появляться в `.cache/01_pending_triage/` по мере готовности."
5. Периодически проверяй статус в `.cache/broker_status.json`.

## Важно
- VPN должен быть **ВЫКЛЮЧЕН** при скачивании (скрипт сам сбрасывает прокси).
- VPN должен быть **ВКЛЮЧЕН** при работе LLM (mine.py обращается к OpenRouter).
- Скрипт `download.py` сам извлекает cookies из Chrome и использует `--impersonate chrome`.
