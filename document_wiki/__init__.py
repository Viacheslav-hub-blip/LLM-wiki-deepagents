"""Пакет document_wiki для агентов добавления и поиска знаний по markdown-документам.

Содержит:
- build_document_wiki_ingest_agent: сборка агента добавления source-документа в wiki.
- build_document_wiki_query_agent: сборка агента поиска ответов через wiki и sources.
"""

from document_wiki.agent import (
    build_document_wiki_ingest_agent,
    build_document_wiki_query_agent,
)


__all__ = [
    "build_document_wiki_ingest_agent",
    "build_document_wiki_query_agent",
]
