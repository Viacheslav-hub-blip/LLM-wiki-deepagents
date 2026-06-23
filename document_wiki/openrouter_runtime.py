"""Локальная настройка OpenRouter-модели для document_wiki запусков.

Содержит:
- configure_openrouter_runtime: настройка OpenRouter-compatible переменных окружения.
- ensure_openai_api_key: интерактивный ввод API-ключа для текущего процесса.
- load_openrouter_model: ленивый импорт модели из корневого ``model.py`` проекта.
"""

import getpass
import os
from typing import Any


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
OPENROUTER_TEMPERATURE = "0.2"
OPENROUTER_TIMEOUT_SECONDS = "120"
OPENROUTER_MAX_RETRIES = "0"
OPENAI_API_KEY_ENV_VAR = "OPENAI_API_KEY"


def configure_openrouter_runtime() -> None:
    """Настраивает OpenRouter как OpenAI-compatible провайдер для document_wiki.

    Args:
        Отсутствуют. Функция использует константы модуля и переменные окружения.

    Returns:
        ``None``. В окружение процесса добавляются только отсутствующие настройки.

    Notes:
        Функция не задает ``OPENAI_API_KEY`` и не читает пользовательские ключи.
        Ключ должен быть установлен снаружи перед реальным запуском модели.
    """

    os.environ.setdefault("DEEP_AGENT_MODEL_PROVIDER", "openai")
    os.environ.setdefault("OPENAI_BASE_URL", OPENROUTER_BASE_URL)
    os.environ.setdefault("DEEP_AGENT_MODEL", OPENROUTER_MODEL)
    os.environ.setdefault("DEEP_AGENT_TEMPERATURE", OPENROUTER_TEMPERATURE)
    os.environ.setdefault("DEEP_AGENT_TIMEOUT", OPENROUTER_TIMEOUT_SECONDS)
    os.environ.setdefault("DEEP_AGENT_MAX_RETRIES", OPENROUTER_MAX_RETRIES)


def ensure_openai_api_key() -> None:
    """Запрашивает OpenRouter API-ключ, если он не задан в окружении.

    Args:
        Отсутствуют. Функция читает и изменяет переменные окружения текущего процесса.

    Returns:
        ``None``. Если ключ введен, он сохраняется только в ``os.environ`` текущего
        процесса и не записывается в файлы.

    Raises:
        ValueError: Пользователь не ввел API-ключ.
    """

    if os.environ.get(OPENAI_API_KEY_ENV_VAR):
        return

    api_key = getpass.getpass("Введите OpenRouter API key для текущего запуска: ").strip()
    if not api_key:
        raise ValueError("OPENAI_API_KEY не задан. Укажите ключ для запуска модели.")
    os.environ[OPENAI_API_KEY_ENV_VAR] = api_key


def load_openrouter_model() -> Any:
    """Загружает модель OpenRouter так же, как это делает корневой ``run.py``.

    Args:
        Отсутствуют. Функция использует переменные окружения текущего процесса.

    Returns:
        Chat-модель LangChain из корневого модуля ``model.py``.

    Raises:
        ImportError: Корневой модуль ``model.py`` недоступен в текущем окружении.
    """

    configure_openrouter_runtime()
    from model import model

    return model


__all__ = [
    "OPENROUTER_BASE_URL",
    "OPENROUTER_MAX_RETRIES",
    "OPENROUTER_MODEL",
    "OPENROUTER_TEMPERATURE",
    "OPENROUTER_TIMEOUT_SECONDS",
    "OPENAI_API_KEY_ENV_VAR",
    "configure_openrouter_runtime",
    "ensure_openai_api_key",
    "load_openrouter_model",
]
