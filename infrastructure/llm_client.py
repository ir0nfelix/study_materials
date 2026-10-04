"""
Единый шлюз OpenRouter API.

Все агенты импортируют get_client() и get_model() отсюда.
Конфигурация моделей — в infrastructure/models.py (единственная точка настройки).

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

from infrastructure.models import MODELS


def get_client() -> OpenAI:
    """Создаёт OpenAI-совместимый клиент для OpenRouter.

    - Загружает OPENROUTER_API_KEY из .env в корне проекта
    - Патчит socks:// → socks5:// для совместимости с httpx/socksio
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

    Роли и их назначение — в infrastructure/models.py.

    Args:
        role: Ключ из MODELS — "miner", "expert", "expert_budget", "ocr"

    Returns:
        Строка вида "google/gemini-2.5-flash"

    Raises:
        KeyError: если роль не найдена в реестре и нет fallback
    """
    if role not in MODELS:
        fallback = MODELS.get("expert_budget", "openai/gpt-4.1-mini")
        print(f"[llm_client] WARNING: unknown role '{role}', using fallback: {fallback}")
        return fallback
    return MODELS[role]


def _find_project_root() -> str:
    """Находит корень проекта (где лежит .env / mkdocs.yml)."""
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)

    if os.path.exists(os.path.join(root, ".env")):
        return root
    return os.getcwd()
