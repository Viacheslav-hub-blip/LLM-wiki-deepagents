"""Спецификация DimensionsReaderSubagent для чтения текущей wiki-карты.

Содержит:
- DIMENSIONS_READER_AGENT_NAME: имя subagent чтения wiki.
- DIMENSIONS_READER_AGENT_DESCRIPTION: описание subagent для supervisor.
- build_dimensions_reader_subagent_spec: сборка параметров создания DimensionsReaderSubagent.
"""

from typing import Any

from document_wiki.prompts.dimensions_reader import DIMENSIONS_READER_PROMPT


DIMENSIONS_READER_AGENT_NAME = "dimensions-reader"
DIMENSIONS_READER_AGENT_DESCRIPTION = (
    "Используй `dimensions-reader`, когда нужно понять текущее состояние wiki перед "
    "обновлением или поиском: прочитать `wiki/index.md`, найти `wiki/dimensions/*.md` "
    "и вернуть compact wiki map. Он описывает, какие dimensions уже существуют, что они "
    "покрывают, какие source-файлы упомянуты и где возможны пересечения. Пример задачи: "
    "`собери краткую карту текущей wiki перед добавлением sources/doc_017.md`. Не используй "
    "его для анализа нового source-файла, принятия решения о создании dimensions, "
    "редактирования wiki, записи файлов или финального ответа пользователю."
)


def build_dimensions_reader_subagent_spec(
    *,
    model: Any,
    tools: list[Any],
    common_middleware: list[Any],
    skill_sources: list[str],
) -> dict[str, Any]:
    """Собирает параметры создания DimensionsReaderSubagent.

    Args:
        model: Chat-модель LangChain для сжатия текущей wiki-карты.
        tools: Инструменты subagent. Ожидаются read-only filesystem tools и загрузка
            skills, если она подключена в builder.
        common_middleware: Middleware, общие для document_wiki subagents.
        skill_sources: Виртуальные каталоги skills для нативного SkillsMiddleware.

    Returns:
        Словарь именованных аргументов, совместимый с ``create_deep_agent``.
    """

    return {
        "name": DIMENSIONS_READER_AGENT_NAME,
        "system_prompt": DIMENSIONS_READER_PROMPT,
        "model": model,
        "tools": list(tools),
        "skills": list(skill_sources),
        "middleware": list(common_middleware),
    }


__all__ = [
    "DIMENSIONS_READER_AGENT_DESCRIPTION",
    "DIMENSIONS_READER_AGENT_NAME",
    "build_dimensions_reader_subagent_spec",
]
