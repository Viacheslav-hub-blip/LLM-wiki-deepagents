"""Реестр subagents document_wiki для ingest supervisor.

Содержит:
- build_ingest_subagent_specs: сборка списка compiled subagents для IngestSupervisor.
"""

from typing import Any

from document_wiki.subagents.dimensions_reader import (
    DIMENSIONS_READER_AGENT_DESCRIPTION,
    DIMENSIONS_READER_AGENT_NAME,
)
from document_wiki.subagents.source_profiler import (
    SOURCE_PROFILER_AGENT_DESCRIPTION,
    SOURCE_PROFILER_AGENT_NAME,
)
from document_wiki.subagents.wiki_writer import (
    WIKI_WRITER_AGENT_DESCRIPTION,
    WIKI_WRITER_AGENT_NAME,
)


def build_ingest_subagent_specs(
    *,
    source_profiler_agent: Any,
    dimensions_reader_agent: Any,
    wiki_writer_agent: Any,
) -> list[dict[str, Any]]:
    """Собирает спецификации compiled subagents для IngestSupervisor.

    Args:
        source_profiler_agent: Скомпилированный SourceProfilerSubagent.
        dimensions_reader_agent: Скомпилированный DimensionsReaderSubagent.
        wiki_writer_agent: Скомпилированный WikiWriterSubagent.

    Returns:
        Список словарей subagent-спецификаций для ``create_deep_agent`` supervisor.
    """

    return [
        {
            "name": SOURCE_PROFILER_AGENT_NAME,
            "description": SOURCE_PROFILER_AGENT_DESCRIPTION,
            "runnable": source_profiler_agent,
        },
        {
            "name": DIMENSIONS_READER_AGENT_NAME,
            "description": DIMENSIONS_READER_AGENT_DESCRIPTION,
            "runnable": dimensions_reader_agent,
        },
        {
            "name": WIKI_WRITER_AGENT_NAME,
            "description": WIKI_WRITER_AGENT_DESCRIPTION,
            "runnable": wiki_writer_agent,
        },
    ]


__all__ = ["build_ingest_subagent_specs"]
