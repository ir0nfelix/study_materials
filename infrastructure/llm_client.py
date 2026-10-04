"""
Единый клиент OpenRouter API.
Все агенты импортируют get_client() и get_model() вместо дублирования boilerplate.

Использование:
    from infrastructure.llm_client import get_client, get_model

    client = get_client()
    response = client.chat.completions.create(
        model=get_model("expert"),
        messages=[...]
    )
"""
import os
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Реестр моделей по ролям (меняй здесь — применится ко всем агентам)
# ---------------------------------------------------------------------------
MODELS = {
    # Miner: извлечение задач из транскрипций
    # Требуется огромный контекст (транскрипты >128K токенов)
    # Gemini 2.5 Flash: 1M контекст, $0.30/$2.50 за 1M токенов
    "miner": "google/gemini-2.5-flash",

    # Expert: генерация эталонных решений с кодом
    # Claude Sonnet 4: лучшее качество кода, $3/$15 за 1M токенов
    "expert": "anthropic/claude-sonnet-4",

    # Expert (бюджетный): для массовой обработки
    # GPT-4.1 Mini: $0.40/$1.60 за 1M токенов, контекст 1M
    "expert_budget": "openai/gpt-4.1-mini",

    # OCR: распознавание кода со скриншотов (vision)
    # Gemini 2.5 Flash: поддерживает мультимодал, дёшево
    "ocr": "google/gemini-2.5-flash",
}


def get_client() -> OpenAI:
    """Создаёт OpenAI-совместимый клиент для OpenRouter.

    - Загружает OPENROUTER_API_KEY из .env в корне проекта
    - Патчит socks:// → socks5:// для совместимости с httpx
    - Возвращает готовый клиент
    """
    root_dir = _find_project_root()
    load_dotenv(os.path.join(root_dir, ".env"))

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not found in .env")

    # Patch socks:// → socks5:// для httpx/socksio
    for var in [
        "http_proxy", "https_proxy", "all_proxy",
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    ]:
        val = os.environ.get(var, "")
        if val.startswith("socks://"):
            os.environ[var] = val.replace("socks://", "socks5://", 1)

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )


def get_model(role: str) -> str:
    """Возвращает ID модели OpenRouter для указанной роли.

    Args:
        role: Ключ из MODELS — "miner", "expert", "expert_budget", "ocr"

    Returns:
        Строка вида "google/gemini-2.5-flash"
    """
    return MODELS.get(role, MODELS["expert_budget"])


def _find_project_root() -> str:
    """Находит корень проекта (где лежит .env / mkdocs.yml)."""
    # Поднимаемся от infrastructure/ на один уровень
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)

    # Перестраховка: если запускают из другого места
    if os.path.exists(os.path.join(root, ".env")):
        return root
    # Fallback: текущая рабочая директория
    return os.getcwd()
