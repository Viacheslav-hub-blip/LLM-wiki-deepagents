"""Subagent specifications document_wiki.

Содержит:
- build_dimensions_reader_subagent_spec: сборка DimensionsReaderSubagent.
- build_ingest_subagent_specs: сборка списка ingest subagents.
- build_source_profiler_subagent_spec: сборка SourceProfilerSubagent.
- build_wiki_writer_subagent_spec: сборка WikiWriterSubagent.
"""

from document_wiki.subagents.dimensions_reader import build_dimensions_reader_subagent_spec
from document_wiki.subagents.registry import build_ingest_subagent_specs
from document_wiki.subagents.source_profiler import build_source_profiler_subagent_spec
from document_wiki.subagents.wiki_writer import build_wiki_writer_subagent_spec


__all__ = [
    "build_dimensions_reader_subagent_spec",
    "build_ingest_subagent_specs",
    "build_source_profiler_subagent_spec",
    "build_wiki_writer_subagent_spec",
]
