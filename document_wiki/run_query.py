"""Entrypoint для запуска query-agent по базе document_wiki.

Содержит:
- run_document_wiki_query: запуск поиска ответа через wiki и sources.
- build_query_message: сборка пользовательского сообщения для QueryDeepAgent.
- main: запуск query-agent из IDE по константам файла.
- _last_message_text: извлечение текста последнего сообщения агента.
"""

import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from document_wiki.agent import build_document_wiki_query_agent
from document_wiki.openrouter_runtime import ensure_openai_api_key, load_openrouter_model
from document_wiki.settings import DocumentWikiSettings, load_document_wiki_settings


DEFAULT_RECURSION_LIMIT = 100
DEFAULT_THREAD_ID = "document-wiki-query-ide"
QUESTION = "Какие основные клиентские проблемы описаны в документах?"
WORKSPACE_ROOT = "."
DOCUMENT_WIKI_ROOT = None


def run_document_wiki_query(
    *,
    model: Any | None = None,
    question: str,
    settings: DocumentWikiSettings | None = None,
    workspace_root: str | Path | None = None,
    document_wiki_root: str | Path | None = None,
    invoke_config: dict[str, Any] | None = None,
) -> Any:
    """Запускает query-agent для ответа на вопрос по document_wiki.

    Args:
        model: Chat-модель LangChain для запуска document_wiki query-agent. Если
            значение не передано, используется OpenRouter-модель из корневого ``model.py``.
        question: Вопрос пользователя по базе документов.
        settings: Готовые настройки document_wiki. Если не переданы, создаются из
            ``workspace_root`` и ``document_wiki_root``.
        workspace_root: Корень рабочего окружения, если ``settings`` не переданы.
        document_wiki_root: Корень директории document_wiki, если ``settings`` не переданы.
        invoke_config: Дополнительный config для вызова LangGraph agent.

    Returns:
        Результат выполнения query-agent.

    Raises:
        ValueError: Вопрос пустой.
    """

    resolved_settings = settings or load_document_wiki_settings(
        workspace_root=workspace_root,
        document_wiki_root=document_wiki_root,
    )
    run_model = model or load_openrouter_model()
    agent = build_document_wiki_query_agent(
        model=run_model,
        settings=resolved_settings,
    )
    return agent.invoke(
        {"messages": [{"role": "user", "content": build_query_message(question)}]},
        config=invoke_config,
    )


def build_query_message(question: str) -> str:
    """Собирает пользовательское сообщение для QueryDeepAgent.

    Args:
        question: Вопрос пользователя по базе документов.

    Returns:
        Текст сообщения для query-agent.

    Raises:
        ValueError: Вопрос пустой после удаления пробелов по краям.
    """

    normalized_question = str(question or "").strip()
    if not normalized_question:
        raise ValueError("Вопрос для document_wiki query-agent не может быть пустым.")
    return (
        "Ответь на вопрос по базе document_wiki через wiki и source-файлы.\n\n"
        f"Вопрос: {normalized_question}\n\n"
        "Используй wiki только как карту поиска. Финальный ответ должен опираться на sources/."
    )


def main() -> int:
    """Запускает query-agent из IDE по константам модуля.

    Args:
        Отсутствуют. Параметры запуска задаются константами модуля.

    Returns:
        Код завершения процесса: ``0`` при успешном запуске.
    """

    ensure_openai_api_key()
    result = run_document_wiki_query(
        question=QUESTION,
        workspace_root=WORKSPACE_ROOT,
        document_wiki_root=DOCUMENT_WIKI_ROOT,
        invoke_config={
            "recursion_limit": DEFAULT_RECURSION_LIMIT,
            "configurable": {"thread_id": DEFAULT_THREAD_ID},
        },
    )
    print(_last_message_text(result))
    return 0


def _last_message_text(result: Any) -> str:
    """Достает текст последнего сообщения агента из результата invoke.

    Args:
        result: Словарь состояния, который вернул ``agent.invoke``.

    Returns:
        Текст последнего сообщения или строковое представление результата.
    """

    if not isinstance(result, dict):
        return str(result)
    messages = result.get("messages") or []
    if not messages:
        return str(result)
    last_message = messages[-1]
    text = getattr(last_message, "text", None)
    if isinstance(text, str) and text:
        return text
    content = getattr(last_message, "content", None)
    if isinstance(content, str):
        return content
    return str(last_message)


__all__ = [
    "build_query_message",
    "main",
    "run_document_wiki_query",
]


if __name__ == "__main__":
    raise SystemExit(main())
