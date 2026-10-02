---
name: resume-broker
description: Запуск фонового Ray-брокера для параллельной обработки очередей. Триггер: /resume
---

# Skill: Запуск брокера (`/resume`)

## Триггер
Пользователь пишет: `/resume`

## Инструменты
- `infrastructure/cli_broker.py` — Ray-воркер-пул

## Когда нужен брокер
- В очередях `.cache/00_pending_download/` скопилось много задач (>5).
- Пользователь загрузил плейлист и хочет параллельную обработку.
- Нужно дообработать задачи, оставшиеся после предыдущей сессии.

## Рабочий процесс

1. Проверь, есть ли незавершённые задачи:
   ```
   .cache/00_pending_download/  — ожидают скачивания
   .cache/02_pending_expert/    — ожидают решения
   .cache/02b_pending_testing/  — ожидают тестирования
   .cache/04_pending_publish/   — ожидают публикации
   ```

2. Если задачи есть — запусти брокер фоновым процессом:
   ```bash
   ./venv/bin/python infrastructure/cli_broker.py
   ```

3. Сообщи пользователю статус очередей.

4. Брокер автоматически обработает:
   - Скачивание (download_dispatcher) → `raw_transcripts/`
   - Майнинг задач (miner_dispatcher) → `.cache/01_pending_triage/`
   - Решение экспертом (ray_dispatcher) → `.cache/02b_pending_testing/`
   - Тестирование (facilitator_dispatcher) → `.cache/03_pending_final/`
   - Публикация (publisher_dispatcher) → `.cache/99_completed/`

5. Задачи, требующие апрува (`.cache/01_pending_triage/`, `.cache/03_pending_final/`), **НЕ обрабатываются брокером**. Для них используй скилл `review-tasks`.

## Мониторинг
- Читай `.cache/broker_status.json` для проверки прогресса.
- Или сканируй папки `.cache/` напрямую (`list_dir`).

## Остановка
- Для остановки брокера используй `manage_task` → `kill`.
