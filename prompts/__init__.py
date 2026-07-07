"""Экспорт промптов LLM wiki.

Содержит:
- DIMENSIONS_READER_PROMPT: инструкции субагента чтения wiki.
- INGEST_SUPERVISOR_PROMPT: инструкции supervisor добавления документа.
- QUERY_AGENT_PROMPT: инструкции агента поиска.
- SOURCE_PROFILER_PROMPT: инструкции субагента анализа source-файла.
- WIKI_WRITER_PROMPT: инструкции субагента записи wiki.

Функции:
- нет.
"""

from prompts.wiki_prompts import (
    DIMENSIONS_READER_PROMPT,
    INGEST_SUPERVISOR_PROMPT,
    QUERY_AGENT_PROMPT,
    SOURCE_PROFILER_PROMPT,
    WIKI_WRITER_PROMPT,
)

__all__ = [
    "DIMENSIONS_READER_PROMPT",
    "INGEST_SUPERVISOR_PROMPT",
    "QUERY_AGENT_PROMPT",
    "SOURCE_PROFILER_PROMPT",
    "WIKI_WRITER_PROMPT",
]
