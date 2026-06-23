"""Prompt-константы document_wiki для ingest и query агентов.

Содержит:
- DIMENSIONS_READER_PROMPT: prompt чтения текущей wiki-карты.
- INGEST_SUPERVISOR_PROMPT: prompt supervisor добавления документа.
- QUERY_AGENT_PROMPT: prompt агента поиска по базе документов.
- SOURCE_PROFILER_PROMPT: prompt анализа нового source-документа.
- WIKI_WRITER_PROMPT: prompt обновления wiki.
"""

from document_wiki.prompts.dimensions_reader import DIMENSIONS_READER_PROMPT
from document_wiki.prompts.ingest_supervisor import INGEST_SUPERVISOR_PROMPT
from document_wiki.prompts.query_agent import QUERY_AGENT_PROMPT
from document_wiki.prompts.source_profiler import SOURCE_PROFILER_PROMPT
from document_wiki.prompts.wiki_writer import WIKI_WRITER_PROMPT


__all__ = [
    "DIMENSIONS_READER_PROMPT",
    "INGEST_SUPERVISOR_PROMPT",
    "QUERY_AGENT_PROMPT",
    "SOURCE_PROFILER_PROMPT",
    "WIKI_WRITER_PROMPT",
]
