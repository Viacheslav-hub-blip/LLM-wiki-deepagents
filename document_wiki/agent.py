"""Сборка document_wiki агентов добавления документов и поиска знаний.

Содержит:
- build_document_wiki_ingest_agent: сборка агента добавления source-файла в wiki.
- build_document_wiki_query_agent: сборка агента поиска ответа через wiki и sources.
- _build_filesystem_backend: создание filesystem backend с корнем document_wiki.
- _build_skill_sources: подготовка путей к skills document_wiki.
- _build_common_middleware: подготовка общего списка middleware.
"""

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from document_wiki.prompts import INGEST_SUPERVISOR_PROMPT, QUERY_AGENT_PROMPT
from document_wiki.settings import DocumentWikiSettings, load_document_wiki_settings
from document_wiki.subagents import (
    build_dimensions_reader_subagent_spec,
    build_ingest_subagent_specs,
    build_source_profiler_subagent_spec,
    build_wiki_writer_subagent_spec,
)


def build_document_wiki_ingest_agent(
    *,
    model: Any,
    settings: DocumentWikiSettings | None = None,
    workspace_root: str | Path | None = None,
    document_wiki_root: str | Path | None = None,
    middleware: list[Any] | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Собирает IngestSupervisor для добавления source-документа в wiki.

    Args:
        model: Chat-модель LangChain для supervisor и subagents.
        settings: Готовые настройки document_wiki. Если не переданы, создаются из
            ``workspace_root`` и ``document_wiki_root``.
        workspace_root: Корень рабочего окружения, если ``settings`` не переданы.
        document_wiki_root: Корень директории document_wiki, если ``settings`` не переданы.
        middleware: Дополнительные middleware для supervisor и subagents.
        checkpointer: Checkpointer LangGraph. Если ``None``, агент собирается без
            явного checkpointer.

    Returns:
        Скомпилированный DeepAgents граф IngestSupervisor.
    """

    resolved_settings = settings or load_document_wiki_settings(
        workspace_root=workspace_root,
        document_wiki_root=document_wiki_root,
    )
    backend = _build_filesystem_backend(resolved_settings)
    skill_sources = _build_skill_sources(resolved_settings)
    common_middleware = _build_common_middleware(middleware)

    source_profiler_agent = create_deep_agent(
        **build_source_profiler_subagent_spec(
            model=model,
            tools=[],
            common_middleware=common_middleware,
            skill_sources=skill_sources,
        ),
        backend=backend,
    )
    dimensions_reader_agent = create_deep_agent(
        **build_dimensions_reader_subagent_spec(
            model=model,
            tools=[],
            common_middleware=common_middleware,
            skill_sources=skill_sources,
        ),
        backend=backend,
    )
    wiki_writer_agent = create_deep_agent(
        **build_wiki_writer_subagent_spec(
            model=model,
            tools=[],
            common_middleware=common_middleware,
            skill_sources=skill_sources,
        ),
        backend=backend,
    )

    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=INGEST_SUPERVISOR_PROMPT,
        subagents=build_ingest_subagent_specs(
            source_profiler_agent=source_profiler_agent,
            dimensions_reader_agent=dimensions_reader_agent,
            wiki_writer_agent=wiki_writer_agent,
        ),
        skills=skill_sources,
        backend=backend,
        middleware=common_middleware,
        checkpointer=checkpointer,
    )


def build_document_wiki_query_agent(
    *,
    model: Any,
    settings: DocumentWikiSettings | None = None,
    workspace_root: str | Path | None = None,
    document_wiki_root: str | Path | None = None,
    middleware: list[Any] | None = None,
    checkpointer: Any | None = None,
) -> Any:
    """Собирает QueryDeepAgent для поиска ответов по wiki и source-файлам.

    Args:
        model: Chat-модель LangChain для query-agent.
        settings: Готовые настройки document_wiki. Если не переданы, создаются из
            ``workspace_root`` и ``document_wiki_root``.
        workspace_root: Корень рабочего окружения, если ``settings`` не переданы.
        document_wiki_root: Корень директории document_wiki, если ``settings`` не переданы.
        middleware: Дополнительные middleware для query-agent.
        checkpointer: Checkpointer LangGraph. Если ``None``, агент собирается без
            явного checkpointer.

    Returns:
        Скомпилированный DeepAgents граф QueryDeepAgent.
    """

    resolved_settings = settings or load_document_wiki_settings(
        workspace_root=workspace_root,
        document_wiki_root=document_wiki_root,
    )
    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=QUERY_AGENT_PROMPT,
        skills=_build_skill_sources(resolved_settings),
        backend=_build_filesystem_backend(resolved_settings),
        middleware=_build_common_middleware(middleware),
        checkpointer=checkpointer,
    )


def _build_filesystem_backend(settings: DocumentWikiSettings) -> FilesystemBackend:
    """Создает filesystem backend с корнем в директории document_wiki.

    Args:
        settings: Настройки document_wiki с путем к корневой директории.

    Returns:
        Backend файловой системы, в котором `/` соответствует директории document_wiki.
    """

    settings.document_wiki_root.mkdir(parents=True, exist_ok=True)
    settings.sources_dir.mkdir(parents=True, exist_ok=True)
    settings.wiki_dir.mkdir(parents=True, exist_ok=True)
    settings.dimensions_dir.mkdir(parents=True, exist_ok=True)
    settings.skills_dir.mkdir(parents=True, exist_ok=True)
    return FilesystemBackend(
        root_dir=settings.document_wiki_root,
        virtual_mode=True,
    )


def _build_skill_sources(settings: DocumentWikiSettings) -> list[str]:
    """Возвращает список skill-директорий для document_wiki агентов.

    Args:
        settings: Настройки document_wiki с путем к директории skills.

    Returns:
        Список виртуальных путей skills для ``create_deep_agent``.
    """

    return ["/skills/"]


def _build_common_middleware(middleware: list[Any] | None) -> list[Any]:
    """Возвращает список middleware для document_wiki агентов.

    Args:
        middleware: Пользовательский список middleware или ``None``.

    Returns:
        Новый список middleware для передачи в ``create_deep_agent``.
    """

    return list(middleware or [])


__all__ = [
    "build_document_wiki_ingest_agent",
    "build_document_wiki_query_agent",
]
