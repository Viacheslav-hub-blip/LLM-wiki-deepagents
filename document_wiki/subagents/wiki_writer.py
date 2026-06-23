"""Спецификация WikiWriterSubagent для обновления wiki.

Содержит:
- WIKI_WRITER_AGENT_NAME: имя subagent записи wiki.
- WIKI_WRITER_AGENT_DESCRIPTION: описание subagent для supervisor.
- build_wiki_writer_subagent_spec: сборка параметров создания WikiWriterSubagent.
"""

from typing import Any

from document_wiki.prompts.wiki_writer import WIKI_WRITER_PROMPT


WIKI_WRITER_AGENT_NAME = "wiki-writer"
WIKI_WRITER_AGENT_DESCRIPTION = (
    "Используй `wiki-writer`, когда уже есть `source_path`, markdown-профиль нового "
    "документа от `source-profiler` и compact wiki map от `dimensions-reader`, и нужно "
    "встроить документ в wiki. Он обновляет `wiki/index.md`, обновляет релевантные "
    "`wiki/dimensions/*.md` и при необходимости создает новый широкий переиспользуемый "
    "dimension. Пример задачи: `обнови wiki по sources/doc_017.md, используя этот "
    "source_profile и current_wiki_map`. Не используй его для первичного анализа source, "
    "чтения всей wiki без цели записи, ответов пользователю по базе знаний или любых "
    "изменений в `sources/`. Он не должен создавать дубли dimensions, `.tmp`-файлы, "
    "`metadata.json`, индексы поиска или большие пересказы source-документа."
)


def build_wiki_writer_subagent_spec(
    *,
    model: Any,
    tools: list[Any],
    common_middleware: list[Any],
    skill_sources: list[str],
) -> dict[str, Any]:
    """Собирает параметры создания WikiWriterSubagent.

    Args:
        model: Chat-модель LangChain для обновления wiki.
        tools: Инструменты subagent. Ожидаются filesystem tools чтения и записи,
            а также загрузка skills, если она подключена в builder.
        common_middleware: Middleware, общие для document_wiki subagents.
        skill_sources: Виртуальные каталоги skills для нативного SkillsMiddleware.

    Returns:
        Словарь именованных аргументов, совместимый с ``create_deep_agent``.
    """

    return {
        "name": WIKI_WRITER_AGENT_NAME,
        "system_prompt": WIKI_WRITER_PROMPT,
        "model": model,
        "tools": list(tools),
        "skills": list(skill_sources),
        "middleware": list(common_middleware),
    }


__all__ = [
    "WIKI_WRITER_AGENT_DESCRIPTION",
    "WIKI_WRITER_AGENT_NAME",
    "build_wiki_writer_subagent_spec",
]
