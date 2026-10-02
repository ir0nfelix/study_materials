---
name: agent-1-ingestion
description: Скачивание субтитров YouTube через yt-dlp с автоматическим извлечением cookies и обходом защиты.
---
# Агент 1: Ingestion (Downloader)

## Роль
Скачивает русскоязычные субтитры с YouTube. Обходит защиту (n-challenge) через `deno` и `--impersonate chrome`.

## Скрипты в этой папке
- **`download.py`** — скачивание субтитров одного видео по `video_id`.
  - Аргумент: `video_id` (например `JQIcqX4VnY4`).
  - Автоматически извлекает cookies из Chrome, сбрасывает прокси-переменные окружения.
  - Результат: файл `raw_transcripts/<video_id>.ru.vtt`.
- **`download_pipeline.sh`** — полный пайплайн поиска и пакетного скачивания.
  - Аргументы: `"<запрос>" <лимит>` (например `"Python собеседование" 10`).
  - Ищет видео через `yt-dlp ytsearch`, фильтрует по длительности и дате, скачивает субтитры.

## Входной формат (из очереди `.cache/00_pending_download/`)
```json
{
  "url": "https://www.youtube.com/watch?v=JQIcqX4VnY4",
  "video_id": "JQIcqX4VnY4",
  "status": "pending"
}
```

## Выходной формат
Файл `raw_transcripts/<video_id>.ru.vtt` (субтитры в формате WebVTT).

## Зависимости
- `yt-dlp` (в venv)
- `deno` (для решения JS-challenge)
- `curl-cffi` (для `--impersonate chrome`)
- `secretstorage` (для расшифровки cookies Chrome на Linux)

## Важные ограничения
- VPN **должен быть выключен** при скачивании (YouTube блокирует запросы через VPN).
- Скрипт сам сбрасывает переменные `http_proxy`, `https_proxy`, `HTTP_PROXY`, `HTTPS_PROXY`.
