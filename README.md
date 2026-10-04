# 🎓 Study Materials — AI-powered база знаний по IT-собеседованиям

> Автоматический конвейер для извлечения, разбора и публикации алгоритмических задач из YouTube, PDF и картинок в красивую документацию MkDocs.

---

## Что это такое

Система автоматически:
1. **Скачивает субтитры** YouTube-видео с разборами задач
2. **Извлекает задачи** через LLM (Gemini 2.5 Flash — огромный контекст, дёшево)
3. **Генерирует эталонные решения** с объяснениями (Claude Sonnet 4)
4. **Тестирует код** в изолированной песочнице
5. **Публикует карточки** в интерактивную документацию MkDocs

Ты управляешь всем через чат-команды прямо в IDE (`/add`, `/review`, `/rm`, `/edit`...).

---

## Стек

| Слой | Технология |
|------|-----------|
| Документация | [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) |
| LLM-шлюз | [OpenRouter](https://openrouter.ai) (OpenAI-совместимый API) |
| Скачивание видео | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| Параллельная обработка | [Ray](https://ray.io) |
| Агент-оркестратор | Antigravity IDE (AI-агент с Skills) |

---

## Структура проекта

```
study_materials/
│
├── docs/                        # 📚 База знаний (MkDocs)
│   ├── index.md                 # Главная страница
│   ├── livecoding/
│   │   ├── python.md            # Задачи на Python
│   │   ├── go.md                # Задачи на Go
│   │   ├── java.md              # Задачи на Java
│   │   └── react.md             # Задачи на React/JS
│   ├── anatomy/                 # Внутренности CPython, Go runtime
│   ├── databases/               # SQL, PostgreSQL, Redis, индексы
│   ├── architecture/            # System Design
│   ├── management/              # Менеджмент, QA
│   └── bookmarks.md             # Закладки
│
├── agents/                      # 🤖 Python-скрипты пайплайна
│   ├── 01_ingestion/
│   │   ├── download.py          # Скачивает субтитры YouTube → raw_transcripts/
│   │   └── ingest_doc.py        # Читает PDF/TXT → raw_transcripts/
│   ├── 02_miner/
│   │   └── mine.py              # LLM: транскрипт → JSON-задачи
│   ├── 03_expert/
│   │   └── solve.py             # LLM: задача → эталонное решение с кодом
│   ├── 04_facilitator/
│   │   └── test_runner.py       # Запускает код в песочнице (Python/SQL)
│   └── 05_publisher/
│       └── publish.py           # JSON → Markdown-карточка в docs/
│
├── infrastructure/              # ⚙️ Инфраструктурный слой
│   ├── models.py                # ← ЕДИНАЯ ТОЧКА настройки LLM-моделей
│   ├── llm_client.py            # Шлюз OpenRouter (get_client, get_model)
│   └── cli_broker.py            # Ray worker pool для пакетной обработки
│
├── .agents/                     # 🧠 Конфигурация AI-агента
│   ├── AGENTS.md                # Правила и архитектура для агента
│   └── skills/                  # Skill-инструкции (читает агент)
│       ├── add-video/SKILL.md   # /add <url>
│       ├── add-doc/SKILL.md     # /add doc <path>
│       ├── search-videos/SKILL.md # /search "<query>"
│       ├── review-tasks/SKILL.md  # /review
│       ├── remove-task/SKILL.md # /rm <задача>
│       ├── edit-task/SKILL.md   # /edit <задача>
│       └── resume-broker/SKILL.md # /resume
│
├── .cache/                      # 🔄 File-based State Machine (очереди)
│   ├── 00_pending_download/     # Ожидают скачивания
│   ├── 01_pending_triage/       # Ожидают апрува в чате
│   ├── 02_pending_expert/       # Ожидают решения LLM
│   ├── 02b_pending_testing/     # Ожидают тестирования
│   ├── 03_pending_final/        # Ожидают финального апрува
│   ├── 04_pending_publish/      # Ожидают публикации
│   ├── 99_completed/            # Завершённые
│   ├── 99_rejected/             # Отклонённые
│   └── broker_status.json       # Статус очередей
│
├── raw_transcripts/             # Входящие субтитры и тексты
├── .env                         # OPENROUTER_API_KEY (не в git)
├── mkdocs.yml                   # Конфиг MkDocs
└── requirements.txt
```

---

## Быстрый старт

### 1. Установка

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install openai python-dotenv PyPDF2
```

### 2. Настройка

```bash
cp .env.example .env
# Вставь в .env:
# OPENROUTER_API_KEY=sk-or-...
```

Получить ключ: [openrouter.ai/keys](https://openrouter.ai/keys)

### 3. Запуск документации

```bash
source venv/bin/activate
mkdocs serve -a 127.0.0.1:8001
# → http://127.0.0.1:8001
```

---

## Команды (слэш-команды в чате)

| Команда | Что делает |
|---------|-----------|
| `/add <YouTube URL>` | Скачать видео, извлечь задачи, запустить ревью |
| `/add doc <path>` | Извлечь задачи из PDF, картинки или текстового файла |
| `/search "<запрос>"` | Поиск на YouTube по теме, пакетное скачивание |
| `/review` | Интерактивный апрув задач из очереди: OCR скринов + выбор языка |
| `/rm <задача>` | Удалить задачу из базы знаний (с подтверждением) |
| `/edit <задача>` | Отредактировать условие или решение; перегенерировать через LLM |
| `/resume` | Запустить Ray-брокер для пакетной фоновой обработки |

---

## Пайплайн

```
/add <url>                          /add doc <path>
     │                                    │
     ▼                                    ▼
download.py                        ingest_doc.py
(yt-dlp субтитры)                  (PyPDF2 / OCR)
     │                                    │
     └──────────────┬─────────────────────┘
                    ▼
             raw_transcripts/
                    │
                    ▼
               mine.py  ←── gemini-2.5-flash (1M контекст)
          (извлечение задач)
                    │
                    ▼
        .cache/01_pending_triage/
                    │
          [АПРУВ В ЧАТЕ]
          [OCR скринов?]
          [Выбор языка]
                    │
                    ▼
        .cache/02_pending_expert/
                    │
                    ▼
              solve.py  ←── claude-sonnet-4 (best coder)
          (эталонное решение)
                    │
                    ▼
           test_runner.py
          (Python/SQL sandbox)
                    │
                    ▼
        .cache/03_pending_final/
                    │
          [ФИНАЛЬНЫЙ АПРУВ]
                    │
                    ▼
             publish.py
       (Markdown-карточка в docs/)
                    │
                    ▼
        docs/livecoding/python.md  →  MkDocs 🎉
```

---

## Настройка LLM-моделей

Все модели настраиваются в **одном файле**: [`infrastructure/models.py`](infrastructure/models.py)

```python
MODELS = {
    "miner":          "google/gemini-2.5-flash",   # 1M контекст, $0.30/$2.50/M
    "expert":         "anthropic/claude-sonnet-4", # лучший кодер, $3/$15/M
    "expert_budget":  "openai/gpt-4.1-mini",       # bulk-обработка, $0.40/$1.60/M
    "ocr":            "google/gemini-2.5-flash",   # vision, $0.002/скрин
}
```

### Бюджет по сценариям

| Сценарий | Стоимость (claude-sonnet-4) | Стоимость (gpt-4.1-mini) |
|----------|---------------------------|--------------------------|
| 1 видео YouTube (~5 задач) | ~$0.28 | ~$0.05 |
| 10 видео через `/search` (~50 задач) | ~$2.80 | ~$0.50 |
| 1 PDF-документ (~3 задачи) | ~$0.17 | ~$0.03 |
| OCR 1 скриншота | ~$0.002 | ~$0.002 |

> Для массовой обработки (/search, плейлисты) рекомендуется переключить `"expert"` на `"expert_budget"` в `models.py`.

---

## Анатомия карточки задачи

Каждая задача в `.md` файле — автономный блок:

```markdown
## Задача 42: Слияние отсортированных массивов {#task-042-python-merge-sorted}
**Источник:** [Название видео](https://youtube.com/watch?v=...)

### Условие
Вам даны два отсортированных массива...

### Код задачи          ← опционально (OCR со скрина)
```python
def foo(): pass
```

### Эталонное решение (AI)

#### 1. Анализ задачи
**Time Complexity**: O(m+n) ...

#### 2. Код решения на Python
```python
def merge(...): ...
```

#### 3. Объяснение алгоритма
...
```

**Правила разметки (критично):**
- Внутри карточки **нельзя** использовать `#` и `##` — только `###`, `####`
- `{#slug}` в заголовке H2 **не удалять** — это id для JS-скрипта и навигации
- Секции `### Решение кандидата` и `### Эталонное решение (AI)` авто-оборачиваются в `<details>`

---

## Переменные окружения

| Переменная | Описание |
|-----------|---------|
| `OPENROUTER_API_KEY` | API-ключ OpenRouter (обязательно) |
| `APP_CACHE_DIR` | Путь к папке очередей (по умолчанию `.cache`) |
| `APP_RAW_DIR` | Путь к папке транскриптов (по умолчанию `raw_transcripts`) |

---

## Зависимости

```
mkdocs>=1.5.0
mkdocs-material>=9.4.0
yt-dlp>=2025.01.0
ray>=2.8.0
openai
python-dotenv
PyPDF2
```

---

## VPN-заметка

- **Скачивание субтитров** (`download.py`) — VPN **выключен** (скрипт сам сбрасывает прокси)
- **Вызовы LLM** (`mine.py`, `solve.py`) — VPN **включён** (OpenRouter через прокси)
