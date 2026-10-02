---
name: search-videos
description: Поиск YouTube-видео по запросу и пакетное скачивание субтитров. Триггер: /search "<query>" [limit]
---

# Skill: Поиск видео (`/search`)

## Триггер
Пользователь пишет в чат: `/search "<запрос>" [лимит]`
- Пример: `/search "Python собеседование backend" 10`
- Лимит по умолчанию: 5

## Инструменты (скрипты)
- `agents/01_ingestion/download_pipeline.sh` — полный пайплайн поиска и скачивания
- `agents/01_ingestion/download.py <video_id>` — скачивание одного видео
- `agents/02_miner/mine.py <path_to_vtt>` — извлечение задач через LLM

## Рабочий процесс

1. Запусти пайплайн поиска:
   ```bash
   bash agents/01_ingestion/download_pipeline.sh "<запрос>" <лимит>
   ```
   Скрипт сам извлечёт cookies, найдёт видео через `yt-dlp ytsearch`, скачает субтитры.

2. После завершения проверь `raw_transcripts/` на новые `.vtt` файлы.

3. Для каждого нового файла запусти Miner:
   ```bash
   ./venv/bin/python agents/02_miner/mine.py raw_transcripts/<filename>.vtt
   ```

4. Покажи пользователю список найденных задач.

5. Перейди к скиллу `review-tasks`.

## Фильтры поиска (встроены в download_pipeline.sh)
- Видео не старше 1 года (`--dateafter today-1year`)
- Длительность больше 20 минут (`--match-filter "duration > 20"`)
- Язык субтитров: русский и английский (`--sub-lang ru,en`)

## Важно
- VPN должен быть **ВЫКЛЮЧЕН** при скачивании.
