"""Entrypoint для запуска ingest-agent по готовому source markdown-файлу.

Содержит:
- run_document_wiki_ingest: запуск добавления одного source-файла в wiki.
- build_ingest_message: сборка пользовательского сообщения для IngestSupervisor.
- main: запуск ingest-agent из IDE по константам файла.
- format_wiki_files_report: формирование отчета о фактических wiki-файлах.
- _last_message_text: извлечение текста последнего сообщения агента.
"""

import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from document_wiki.agent import build_document_wiki_ingest_agent
from document_wiki.openrouter_runtime import ensure_openai_api_key, load_openrouter_model
from document_wiki.paths import relative_to_document_wiki, require_inside_document_wiki
from document_wiki.settings import DocumentWikiSettings, load_document_wiki_settings


DEFAULT_RECURSION_LIMIT = 100
DEFAULT_THREAD_ID = "document-wiki-ingest-ide"
SOURCE_PATH = "sources/doc_002.md"
WORKSPACE_ROOT = "."
DOCUMENT_WIKI_ROOT = None


def run_document_wiki_ingest(
    *,
    model: Any | None = None,
    source_path: str | Path,
    settings: DocumentWikiSettings | None = None,
    workspace_root: str | Path | None = None,
    document_wiki_root: str | Path | None = None,
    invoke_config: dict[str, Any] | None = None,
) -> Any:
    """Запускает ingest-agent для уже существующего source markdown-файла.

    Args:
        model: Chat-модель LangChain для запуска document_wiki ingest-agent. Если
            значение не передано, используется OpenRouter-модель из корневого ``model.py``.
        source_path: Путь к готовому source-файлу внутри директории document_wiki.
        settings: Готовые настройки document_wiki. Если не переданы, создаются из
            ``workspace_root`` и ``document_wiki_root``.
        workspace_root: Корень рабочего окружения, если ``settings`` не переданы.
        document_wiki_root: Корень директории document_wiki, если ``settings`` не переданы.
        invoke_config: Дополнительный config для вызова LangGraph agent.

    Returns:
        Результат выполнения ingest-agent.

    Raises:
        FileNotFoundError: Source-файл не найден.
        ValueError: Source-файл находится вне директории document_wiki.
    """

    resolved_settings = settings or load_document_wiki_settings(
        workspace_root=workspace_root,
        document_wiki_root=document_wiki_root,
    )
    run_model = model or load_openrouter_model()
    resolved_source_path = Path(source_path)
    if not resolved_source_path.is_absolute():
        resolved_source_path = resolved_settings.document_wiki_root / resolved_source_path
    resolved_source_path = resolved_source_path.resolve()

    require_inside_document_wiki(resolved_settings, resolved_source_path)
    if not resolved_source_path.is_file():
        raise FileNotFoundError(f"Source-файл не найден: {resolved_source_path}")

    source_path_for_agent = relative_to_document_wiki(
        resolved_settings,
        resolved_source_path,
    )
    agent = build_document_wiki_ingest_agent(
        model=run_model,
        settings=resolved_settings,
    )
    return agent.invoke(
        {"messages": [{"role": "user", "content": build_ingest_message(source_path_for_agent)}]},
        config=invoke_config,
    )


def build_ingest_message(source_path: str) -> str:
    """Собирает пользовательское сообщение для IngestSupervisor.

    Args:
        source_path: POSIX-путь к source-файлу относительно директории document_wiki.

    Returns:
        Текст сообщения для запуска ingest-процесса.
    """

    return (
        "Добавь markdown-файл в document_wiki.\n\n"
        f"source_path: {source_path}\n\n"
        "Файл уже существует в sources/."
    )


def main() -> int:
    """Запускает ingest-agent из IDE по константам модуля.

    Args:
        Отсутствуют. Параметры запуска задаются константами модуля.

    Returns:
        Код завершения процесса: ``0`` при успешном запуске.
    """

    ensure_openai_api_key()
    result = run_document_wiki_ingest(
        source_path=SOURCE_PATH,
        workspace_root=WORKSPACE_ROOT,
        document_wiki_root=DOCUMENT_WIKI_ROOT,
        invoke_config={
            "recursion_limit": DEFAULT_RECURSION_LIMIT,
            "configurable": {"thread_id": DEFAULT_THREAD_ID},
        },
    )
    print(_last_message_text(result))
    print()
    print(format_wiki_files_report())
    return 0


def format_wiki_files_report(
    document_wiki_root: str | Path | None = DOCUMENT_WIKI_ROOT,
) -> str:
    """Формирует отчет о фактически существующих wiki-файлах.

    Args:
        document_wiki_root: Корень директории document_wiki или ``None`` для папки
            рядом с текущим файлом.

    Returns:
        Markdown-отчет со списком файлов в `wiki/`.
    """

    root = Path(document_wiki_root) if document_wiki_root is not None else Path(__file__).resolve().parent
    wiki_root = root / "wiki"
    if not wiki_root.exists():
        return "## Фактические wiki-файлы\nwiki/ не существует."

    files = sorted(path.relative_to(root).as_posix() for path in wiki_root.rglob("*") if path.is_file())
    if not files:
        return "## Фактические wiki-файлы\nФайлы не найдены."
    lines = ["## Фактические wiki-файлы", *[f"- {path}" for path in files]]
    return "\n".join(lines)


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
    "build_ingest_message",
    "format_wiki_files_report",
    "main",
    "run_document_wiki_ingest",
]


if __name__ == "__main__":
    raise SystemExit(main())
