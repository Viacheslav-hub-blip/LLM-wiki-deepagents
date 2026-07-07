"""Общие настройки agents для LLM wiki.

Содержит:
- PROJECT_ROOT: путь к корню проекта.
- WIKI_PATH: путь к папке wiki.
- SOURCES_PATH: путь к папке sources.
- create_project_backend: создание backend для файлов проекта.
- create_model_retry_middleware: создание middleware повторных вызовов модели.
- ensure_project_dirs: создание базовых папок wiki и sources.
- register_project_profile: регистрация профиля Deep Agents без general-purpose субагента.
- get_last_message_text: получение текста последнего сообщения агента.
"""

from os import getenv
from pathlib import Path
from typing import Any

from deepagents import (
    GeneralPurposeSubagentProfile,
    HarnessProfile,
    register_harness_profile,
)
from deepagents.backends import FilesystemBackend
from langchain.agents.middleware import ModelRetryMiddleware


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WIKI_PATH = PROJECT_ROOT / "wiki"
SOURCES_PATH = PROJECT_ROOT / "sources"
_PROFILE_REGISTERED = False


def create_project_backend() -> FilesystemBackend:
    """Создает файловый backend, который читает и пишет файлы в корне проекта.

    Входные данные:
    - нет.

    Возвращает:
    - FilesystemBackend: backend Deep Agents с корнем в папке проекта.
    """

    return FilesystemBackend(root_dir=str(PROJECT_ROOT), virtual_mode=True)


def create_model_retry_middleware() -> ModelRetryMiddleware:
    """Создает middleware для повторного вызова модели при ошибке.

    Входные данные:
    - нет.

    Возвращает:
    - ModelRetryMiddleware: middleware LangChain с настройками retry из переменных окружения.
    """

    return ModelRetryMiddleware(
        max_retries=int(getenv("LLM_MAX_RETRIES", "2")),
        initial_delay=float(getenv("LLM_RETRY_INITIAL_DELAY", "1.0")),
        backoff_factor=float(getenv("LLM_RETRY_BACKOFF_FACTOR", "2.0")),
        max_delay=float(getenv("LLM_RETRY_MAX_DELAY", "60.0")),
    )


def ensure_project_dirs() -> None:
    """Создает минимальные папки проекта для wiki и source-документов.

    Входные данные:
    - нет.

    Возвращает:
    - None: функция только создает папки, если их еще нет.
    """

    (WIKI_PATH / "dimensions").mkdir(parents=True, exist_ok=True)
    SOURCES_PATH.mkdir(parents=True, exist_ok=True)


def register_project_profile() -> None:
    """Регистрирует профиль Deep Agents без лишнего general-purpose субагента.

    Входные данные:
    - нет.

    Возвращает:
    - None: профиль применяется через глобальный реестр Deep Agents.
    """

    global _PROFILE_REGISTERED

    if _PROFILE_REGISTERED:
        return

    try:
        register_harness_profile(
            getenv("LLM_MODEL", "openai:gpt-5-mini"),
            HarnessProfile(
                general_purpose_subagent=GeneralPurposeSubagentProfile(enabled=False),
            ),
        )
    except ValueError:
        pass

    _PROFILE_REGISTERED = True


def get_last_message_text(result: dict[str, Any]) -> str:
    """Извлекает текст последнего сообщения из результата запуска агента.

    Входные данные:
    - result: словарь результата LangGraph/Deep Agents после invoke.

    Возвращает:
    - str: текст последнего сообщения или строковое представление сообщения.
    """

    message = result["messages"][-1]
    content = getattr(message, "content", message)

    if isinstance(content, str):
        return content

    return str(content)
