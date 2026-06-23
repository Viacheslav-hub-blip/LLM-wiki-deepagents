"""Утилиты путей document_wiki для source-документов и wiki.

Содержит:
- ensure_document_wiki_directories: создание базовых директорий document_wiki.
- ensure_parent_directory: создание родительской директории для файла.
- next_source_id: вычисление следующего source_id по существующим doc_N.md.
- source_file_path: построение пути к source-файлу по source_id.
- relative_to_document_wiki: получение относительного POSIX-пути внутри document_wiki.
- require_inside_document_wiki: проверка, что путь находится внутри document_wiki.
"""

from __future__ import annotations

import re
from pathlib import Path

from document_wiki.settings import DocumentWikiSettings


SOURCE_ID_PATTERN = re.compile(r"^doc_(\d+)$")
SOURCE_FILE_PATTERN = re.compile(r"^doc_(\d+)\.md$")


def ensure_document_wiki_directories(settings: DocumentWikiSettings) -> None:
    """Создает базовые директории document_wiki, если они отсутствуют.

    Args:
        settings: Настройки document_wiki с путями к sources, wiki, dimensions и skills.

    Returns:
        ``None``.
    """

    settings.sources_dir.mkdir(parents=True, exist_ok=True)
    settings.wiki_dir.mkdir(parents=True, exist_ok=True)
    settings.dimensions_dir.mkdir(parents=True, exist_ok=True)
    settings.skills_dir.mkdir(parents=True, exist_ok=True)


def ensure_parent_directory(path: Path) -> None:
    """Создает родительскую директорию для файла, если она отсутствует.

    Args:
        path: Путь к файлу, для которого нужно создать родительскую директорию.

    Returns:
        ``None``.
    """

    path.parent.mkdir(parents=True, exist_ok=True)


def next_source_id(settings: DocumentWikiSettings, width: int = 3) -> str:
    """Вычисляет следующий source_id по существующим файлам ``doc_N.md``.

    Args:
        settings: Настройки document_wiki с путем к директории sources.
        width: Минимальная ширина числовой части source_id с ведущими нулями.

    Returns:
        Новый source_id в формате ``doc_001``.

    Raises:
        ValueError: Ширина числовой части меньше 1.
    """

    if width < 1:
        raise ValueError("Ширина числовой части source_id должна быть положительной.")

    max_number = 0
    if settings.sources_dir.exists():
        for path in settings.sources_dir.glob("doc_*.md"):
            match = SOURCE_FILE_PATTERN.match(path.name)
            if match is None:
                continue
            max_number = max(max_number, int(match.group(1)))

    return f"doc_{max_number + 1:0{width}d}"


def source_file_path(settings: DocumentWikiSettings, source_id: str) -> Path:
    """Строит абсолютный путь к source-файлу по source_id.

    Args:
        settings: Настройки document_wiki с путем к директории sources.
        source_id: Идентификатор source-документа в формате ``doc_N``.

    Returns:
        Абсолютный путь к markdown-файлу source-документа.

    Raises:
        ValueError: source_id имеет недопустимый формат.
    """

    if SOURCE_ID_PATTERN.match(source_id) is None:
        raise ValueError(f"Некорректный source_id: {source_id}")

    path = (settings.sources_dir / f"{source_id}.md").resolve()
    require_inside_document_wiki(settings, path)
    return path


def relative_to_document_wiki(settings: DocumentWikiSettings, path: Path) -> str:
    """Возвращает POSIX-путь файла относительно корня document_wiki.

    Args:
        settings: Настройки document_wiki.
        path: Абсолютный или относительный путь внутри document_wiki.

    Returns:
        POSIX-путь относительно ``document_wiki_root``.

    Raises:
        ValueError: Путь находится вне document_wiki.
    """

    resolved_path = path.resolve()
    require_inside_document_wiki(settings, resolved_path)
    return resolved_path.relative_to(settings.document_wiki_root.resolve()).as_posix()


def require_inside_document_wiki(settings: DocumentWikiSettings, path: Path) -> None:
    """Проверяет, что путь находится внутри директории document_wiki.

    Args:
        settings: Настройки document_wiki.
        path: Проверяемый путь.

    Returns:
        ``None``.

    Raises:
        ValueError: Путь находится вне document_wiki.
    """

    try:
        path.resolve().relative_to(settings.document_wiki_root.resolve())
    except ValueError:
        raise ValueError(f"Путь должен находиться внутри document_wiki: {path}") from None


__all__ = [
    "SOURCE_FILE_PATTERN",
    "SOURCE_ID_PATTERN",
    "ensure_document_wiki_directories",
    "ensure_parent_directory",
    "next_source_id",
    "relative_to_document_wiki",
    "require_inside_document_wiki",
    "source_file_path",
]