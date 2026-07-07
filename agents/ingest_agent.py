"""Deepagent для добавления и обновления wiki-базы.

Содержит:
- create_ingest_subagents: создание трех субагентов формирования базы.
- create_ingest_agent: создание supervisor deepagent для ingest-сценария.
- ingest_agent: готовый supervisor deepagent.
"""

from deepagents import create_deep_agent

from agents.common import (
    create_model_retry_middleware,
    create_project_backend,
    ensure_project_dirs,
    register_project_profile,
)
from model import model
from prompts import (
    DIMENSIONS_READER_PROMPT,
    INGEST_SUPERVISOR_PROMPT,
    SOURCE_PROFILER_PROMPT,
    WIKI_WRITER_PROMPT,
)


def create_ingest_subagents() -> list[dict]:
    """Создает спецификации трех субагентов для формирования wiki-базы.

    Входные данные:
    - нет.

    Возвращает:
    - list[dict]: список subagent-спецификаций с middleware повторного вызова модели.
    """

    return [
        {
            "name": "source-profiler",
            "description": "Анализирует source-файл и возвращает подробное описание сущностей, фактов и поисковых фраз.",
            "system_prompt": SOURCE_PROFILER_PROMPT,
            "middleware": [create_model_retry_middleware()],
        },
        {
            "name": "dimensions-reader",
            "description": "Читает текущую wiki-карту и существующие dimension-файлы.",
            "system_prompt": DIMENSIONS_READER_PROMPT,
            "middleware": [create_model_retry_middleware()],
        },
        {
            "name": "wiki-writer",
            "description": "Создает и точечно обновляет wiki/index.md и wiki/dimensions/*.md по профилю source-файла.",
            "system_prompt": WIKI_WRITER_PROMPT,
            "middleware": [create_model_retry_middleware()],
        },
    ]


def create_ingest_agent():
    """Создает supervisor deepagent для добавления документа в wiki.

    Входные данные:
    - нет.

    Возвращает:
    - CompiledStateGraph: готовый Deep Agents graph с тремя субагентами базы.
    """

    ensure_project_dirs()
    register_project_profile()

    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=INGEST_SUPERVISOR_PROMPT,
        middleware=[create_model_retry_middleware()],
        subagents=create_ingest_subagents(),
        backend=create_project_backend(),
        name="ingest-supervisor",
    )


ingest_agent = create_ingest_agent()
