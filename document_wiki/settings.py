"""Настройки document_wiki для отдельного агента работы с markdown-базой знаний.

Содержит:
- DocumentWikiSettings: настройки директорий source-документов, wiki и skills.
- load_document_wiki_settings: создание настроек document_wiki по умолчанию.
- _resolve_root_path: разрешение корневой директории document_wiki.
- _require_inside_workspace: проверка, что путь находится внутри workspace.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_DOCUMENT_WIKI_DIR_NAME = "document_wiki"
DEFAULT_SOURCES_DIR_NAME = "sources"
DEFAULT_WIKI_DIR_NAME = "wiki"
DEFAULT_DIMENSIONS_DIR_NAME = "dimensions"
DEFAULT_SKILLS_DIR_NAME = "skills"
DEFAULT_INDEX_FILE_NAME = "index.md"

SOURCE_PROFILING_SKILL_NAME = "source-profiling"
DIMENSIONS_READING_SKILL_NAME = "dimensions-reading"
WIKI_WRITING_SKILL_NAME = "wiki-writing"
WIKI_QUERY_SKILL_NAME = "wiki-query"


@dataclass(frozen=True)
class DocumentWikiSettings:
    """Настройки файловой структуры document_wiki.

    Args:
        workspace_root: Абсолютный путь к корню проекта или рабочего окружения.
        document_wiki_root: Абсолютный путь к директории document_wiki.
        sources_dir: Абсолютный путь к директории source-документов.
        wiki_dir: Абсолютный путь к директории wiki.
        dimensions_dir: Абсолютный путь к директории wiki-разрезов.
        skills_dir: Абсолютный путь к директории skills document_wiki.
        index_path: Абсолютный путь к главному wiki-файлу index.md.

    Returns:
        Экземпляр настроек с вычисленными путями для document_wiki.
    """

    workspace_root: Path
    document_wiki_root: Path
    sources_dir: Path
    wiki_dir: Path
    dimensions_dir: Path
    skills_dir: Path
    index_path: Path


def load_document_wiki_settings(
    workspace_root: str | Path | None = None,
    document_wiki_root: str | Path | None = None,
) -> DocumentWikiSettings:
    """Создает настройки document_wiki без зависимости от аналитического агента.

    Args:
        workspace_root: Корень проекта или рабочего окружения. Если не передан,
            используется текущая рабочая директория.
        document_wiki_root: Путь к директории document_wiki. Если не передан,
            используется директория ``document_wiki`` внутри workspace.

    Returns:
        Настройки document_wiki с абсолютными путями к sources, wiki, dimensions и skills.

    Raises:
        ValueError: Директория document_wiki находится вне workspace.
    """

    resolved_workspace_root = Path(workspace_root or Path.cwd()).resolve()
    resolved_document_wiki_root = _resolve_root_path(
        workspace_root=resolved_workspace_root,
        document_wiki_root=document_wiki_root,
    )
    _require_inside_workspace(resolved_document_wiki_root, resolved_workspace_root)

    sources_dir = resolved_document_wiki_root / DEFAULT_SOURCES_DIR_NAME
    wiki_dir = resolved_document_wiki_root / DEFAULT_WIKI_DIR_NAME
    dimensions_dir = wiki_dir / DEFAULT_DIMENSIONS_DIR_NAME
    skills_dir = resolved_document_wiki_root / DEFAULT_SKILLS_DIR_NAME
    index_path = wiki_dir / DEFAULT_INDEX_FILE_NAME

    return DocumentWikiSettings(
        workspace_root=resolved_workspace_root,
        document_wiki_root=resolved_document_wiki_root,
        sources_dir=sources_dir,
        wiki_dir=wiki_dir,
        dimensions_dir=dimensions_dir,
        skills_dir=skills_dir,
        index_path=index_path,
    )


def _resolve_root_path(
    workspace_root: Path,
    document_wiki_root: str | Path | None,
) -> Path:
    """Разрешает путь к корневой директории document_wiki.

    Args:
        workspace_root: Абсолютный путь к workspace.
        document_wiki_root: Пользовательский путь к document_wiki или ``None``.

    Returns:
        Абсолютный путь к директории document_wiki.
    """

    if document_wiki_root is None:
        return (workspace_root / DEFAULT_DOCUMENT_WIKI_DIR_NAME).resolve()

    path = Path(document_wiki_root)
    if path.is_absolute():
        return path.resolve()
    return (workspace_root / path).resolve()


def _require_inside_workspace(path: Path, workspace_root: Path) -> None:
    """Проверяет, что путь находится внутри workspace.

    Args:
        path: Проверяемый путь.
        workspace_root: Корень рабочего окружения.

    Returns:
        ``None``.

    Raises:
        ValueError: Путь находится вне workspace.
    """

    try:
        path.resolve().relative_to(workspace_root.resolve())
    except ValueError:
        raise ValueError(f"Путь document_wiki должен находиться внутри workspace: {path}") from None


__all__ = [
    "DEFAULT_DIMENSIONS_DIR_NAME",
    "DEFAULT_DOCUMENT_WIKI_DIR_NAME",
    "DEFAULT_INDEX_FILE_NAME",
    "DEFAULT_SKILLS_DIR_NAME",
    "DEFAULT_SOURCES_DIR_NAME",
    "DEFAULT_WIKI_DIR_NAME",
    "DIMENSIONS_READING_SKILL_NAME",
    "DocumentWikiSettings",
    "SOURCE_PROFILING_SKILL_NAME",
    "WIKI_QUERY_SKILL_NAME",
    "WIKI_WRITING_SKILL_NAME",
    "load_document_wiki_settings",
]
