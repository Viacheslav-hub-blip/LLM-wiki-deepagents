"""Сборка document_wiki агентов добавления документов и поиска знаний.

Содержит:
- build_document_wiki_ingest_agent: сборка агента добавления source-файла в wiki.
- build_document_wiki_query_agent: сборка агента поиска ответа через wiki и sources.
- _build_filesystem_backend: создание filesystem backend с корнем document_wiki.
- _build_skill_sources: подготовка путей к skills document_wiki.
- _build_common_middleware: подготовка общего списка middleware.
- _build_system_prompt: добавление GigaChat runtime-практик к базовому prompt.
- _register_document_wiki_harness_profile: регистрация harness profile основного DeepAgent.
- _build_optional_gigachat_middleware: подключение middleware основного DeepAgent, если они доступны.
- describe_document_wiki_runtime: описание фактически подключенного runtime-каркаса.
- format_document_wiki_runtime_report: markdown-отчет о фактически подключенном runtime-каркасе.
"""

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

from document_wiki.middleware import DocumentWikiWriteVerificationMiddleware
from document_wiki.prompts import INGEST_SUPERVISOR_PROMPT, QUERY_AGENT_PROMPT
from document_wiki.settings import DocumentWikiSettings, load_document_wiki_settings
from document_wiki.subagents import (
    build_dimensions_reader_subagent_spec,
    build_ingest_subagent_specs,
    build_source_profiler_subagent_spec,
    build_wiki_writer_subagent_spec,
)

try:
    from deep_agent.middleware.filesystem_path_contract import FilesystemPathContractMiddleware
    from deep_agent.middleware.gigachat_runtime import LoopBreakerMiddleware, ThinkToolMiddleware
    from deep_agent.middleware.tool_descriptions import PromptToolDescriptionsMiddleware
    from deep_agent.prompts.gigachat import build_gigachat_practices_prompt
    from deep_agent.prompts.tool_contracts import TOOL_DESCRIPTION_OVERRIDES
    from deep_agent.runtime.filesystem import Utf8FilesystemBackend
    from deep_agent.runtime.harness import register_analytics_harness_profile
except ImportError:
    FilesystemPathContractMiddleware = None  # type: ignore[assignment]
    LoopBreakerMiddleware = None  # type: ignore[assignment]
    PromptToolDescriptionsMiddleware = None  # type: ignore[assignment]
    ThinkToolMiddleware = None  # type: ignore[assignment]
    TOOL_DESCRIPTION_OVERRIDES = None  # type: ignore[assignment]
    Utf8FilesystemBackend = None  # type: ignore[assignment]
    build_gigachat_practices_prompt = None  # type: ignore[assignment]
    register_analytics_harness_profile = None  # type: ignore[assignment]


DOCUMENT_WIKI_HARNESS_PROFILE_KEYS = (
    "openai",
    "kitai",
    "gigachat",
    "GigaChat-3-Ultra",
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
    _register_document_wiki_harness_profile()
    backend = _build_filesystem_backend(resolved_settings)
    skill_sources = _build_skill_sources(resolved_settings)
    common_middleware = _build_common_middleware(
        middleware,
        backend=backend,
        settings=resolved_settings,
    )

    source_profiler_agent = create_deep_agent(
        **_with_system_prompt(
            build_source_profiler_subagent_spec(
                model=model,
                tools=[],
                common_middleware=common_middleware,
                skill_sources=skill_sources,
            )
        ),
        backend=backend,
    )
    dimensions_reader_agent = create_deep_agent(
        **_with_system_prompt(
            build_dimensions_reader_subagent_spec(
                model=model,
                tools=[],
                common_middleware=common_middleware,
                skill_sources=skill_sources,
            )
        ),
        backend=backend,
    )
    wiki_writer_agent = create_deep_agent(
        **_with_system_prompt(
            build_wiki_writer_subagent_spec(
                model=model,
                tools=[],
                common_middleware=common_middleware,
                skill_sources=skill_sources,
            )
        ),
        backend=backend,
    )

    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=_build_system_prompt(INGEST_SUPERVISOR_PROMPT),
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


def _with_system_prompt(spec: dict[str, Any]) -> dict[str, Any]:
    """Возвращает копию subagent spec с усиленным system prompt.

    Args:
        spec: Словарь аргументов для ``create_deep_agent``.

    Returns:
        Новая спецификация subagent с добавленными практиками GigaChat, если они доступны.
    """

    updated_spec = dict(spec)
    updated_spec["system_prompt"] = _build_system_prompt(str(updated_spec.get("system_prompt") or ""))
    return updated_spec


def _build_system_prompt(base_prompt: str) -> str:
    """Добавляет к базовому prompt практики выполнения основного DeepAgent.

    Args:
        base_prompt: Исходный системный prompt document_wiki agent.

    Returns:
        Prompt с GigaChat-practices, если основной пакет ``deep_agent`` доступен.
    """

    if build_gigachat_practices_prompt is None:
        return base_prompt
    practices_prompt = build_gigachat_practices_prompt()
    return f"{base_prompt}\n\n{practices_prompt}"


def _register_document_wiki_harness_profile() -> None:
    """Регистрирует harness profile основного DeepAgent для document_wiki.

    Args:
        Отсутствуют.

    Returns:
        ``None``. Если основной пакет ``deep_agent`` недоступен, функция ничего не делает.
    """

    if register_analytics_harness_profile is None:
        return
    for profile_key in DOCUMENT_WIKI_HARNESS_PROFILE_KEYS:
        register_analytics_harness_profile(
            profile_key,
            enable_general_purpose=False,
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
    _register_document_wiki_harness_profile()
    backend = _build_filesystem_backend(resolved_settings)
    skill_sources = _build_skill_sources(resolved_settings)
    common_middleware = _build_common_middleware(
        middleware,
        backend=backend,
        settings=resolved_settings,
    )
    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=_build_system_prompt(QUERY_AGENT_PROMPT),
        skills=skill_sources,
        backend=backend,
        middleware=common_middleware,
        checkpointer=checkpointer,
    )


def describe_document_wiki_runtime(
    settings: DocumentWikiSettings | None = None,
    *,
    workspace_root: str | Path | None = None,
    document_wiki_root: str | Path | None = None,
) -> dict[str, Any]:
    """Описывает фактически подключенный runtime document_wiki.

    Args:
        settings: Готовые настройки document_wiki. Если не переданы, создаются из ``workspace_root`` и
            ``document_wiki_root``.
        workspace_root: Корень рабочего окружения, если ``settings`` не переданы.
        document_wiki_root: Корень директории document_wiki, если ``settings`` не переданы.

    Returns:
        Словарь с типом backend, списком middleware и признаком доступности runtime основного DeepAgent.
    """

    resolved_settings = settings or load_document_wiki_settings(
        workspace_root=workspace_root,
        document_wiki_root=document_wiki_root,
    )
    backend = _build_filesystem_backend(resolved_settings)
    middleware_items = _build_common_middleware(
        None,
        backend=backend,
        settings=resolved_settings,
    )
    return {
        "document_wiki_root": str(resolved_settings.document_wiki_root),
        "backend": type(backend).__name__,
        "middleware": [type(item).__name__ for item in middleware_items],
        "deep_agent_runtime_available": build_gigachat_practices_prompt is not None,
        "gigachat_practices_enabled": "GigaChat Execution Practices" in _build_system_prompt(""),
        "harness_profile_registration_available": register_analytics_harness_profile is not None,
    }


def format_document_wiki_runtime_report(
    settings: DocumentWikiSettings | None = None,
    *,
    workspace_root: str | Path | None = None,
    document_wiki_root: str | Path | None = None,
) -> str:
    """Формирует markdown-отчет о фактически подключенном runtime document_wiki.

    Args:
        settings: Готовые настройки document_wiki. Если не переданы, создаются из ``workspace_root`` и
            ``document_wiki_root``.
        workspace_root: Корень рабочего окружения, если ``settings`` не переданы.
        document_wiki_root: Корень директории document_wiki, если ``settings`` не переданы.

    Returns:
        Markdown-строка с backend, middleware и статусом подключения основного DeepAgent runtime.
    """

    runtime = describe_document_wiki_runtime(
        settings,
        workspace_root=workspace_root,
        document_wiki_root=document_wiki_root,
    )
    core_status = "enabled" if runtime["deep_agent_runtime_available"] else "disabled"
    practices_status = "enabled" if runtime["gigachat_practices_enabled"] else "disabled"
    harness_status = "enabled" if runtime["harness_profile_registration_available"] else "disabled"
    middleware_list = ", ".join(runtime["middleware"]) or "none"
    return "\n".join(
        [
            "## DocumentWiki runtime",
            f"- document_wiki_root: {runtime['document_wiki_root']}",
            f"- backend: {runtime['backend']}",
            f"- core DeepAgent runtime: {core_status}",
            f"- GigaChat practices: {practices_status}",
            f"- harness profile registration: {harness_status}",
            f"- middleware: {middleware_list}",
        ]
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
    backend_class = Utf8FilesystemBackend or FilesystemBackend
    return backend_class(
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


def _build_common_middleware(
    middleware: list[Any] | None,
    *,
    backend: Any,
    settings: DocumentWikiSettings,
) -> list[Any]:
    """Возвращает список middleware для document_wiki агентов.

    Args:
        middleware: Пользовательский список middleware или ``None``.
        backend: Filesystem backend для проверки фактической записи файлов.
        settings: Настройки document_wiki с корнем workspace для filesystem tools.

    Returns:
        Новый список middleware для передачи в ``create_deep_agent``.
    """

    return [
        *_build_optional_gigachat_middleware(
            backend=backend,
            settings=settings,
        ),
        DocumentWikiWriteVerificationMiddleware(backend=backend),
        *list(middleware or []),
    ]


def _build_optional_gigachat_middleware(
    *,
    backend: Any,
    settings: DocumentWikiSettings,
) -> list[Any]:
    """Возвращает middleware основного DeepAgent, если они доступны.

    Args:
        backend: Filesystem backend document_wiki.
        settings: Настройки document_wiki с корнем файлового пространства.

    Returns:
        Список middleware для стабилизации tool-calling у GigaChat/KitAI.
    """

    result: list[Any] = []
    if PromptToolDescriptionsMiddleware is not None and TOOL_DESCRIPTION_OVERRIDES is not None:
        result.append(PromptToolDescriptionsMiddleware(TOOL_DESCRIPTION_OVERRIDES))
    if ThinkToolMiddleware is not None:
        result.append(ThinkToolMiddleware())
    if FilesystemPathContractMiddleware is not None:
        result.append(
            FilesystemPathContractMiddleware(
                workspace_root=settings.document_wiki_root.resolve(),
                backend=backend,
            )
        )
    if LoopBreakerMiddleware is not None:
        result.append(LoopBreakerMiddleware())
    return result


__all__ = [
    "build_document_wiki_ingest_agent",
    "build_document_wiki_query_agent",
    "describe_document_wiki_runtime",
    "format_document_wiki_runtime_report",
]
