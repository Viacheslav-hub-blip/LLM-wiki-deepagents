"""Спецификация SourceProfilerSubagent для анализа source-документа.

Содержит:
- SOURCE_PROFILER_AGENT_NAME: имя subagent анализа source-файла.
- SOURCE_PROFILER_AGENT_DESCRIPTION: описание subagent для supervisor.
- build_source_profiler_subagent_spec: сборка параметров создания SourceProfilerSubagent.
"""

from typing import Any

from document_wiki.prompts.source_profiler import SOURCE_PROFILER_PROMPT


SOURCE_PROFILER_AGENT_NAME = "source-profiler"
SOURCE_PROFILER_AGENT_DESCRIPTION = (
    "Используй `source-profiler`, когда нужно проанализировать один новый готовый "
    "markdown-файл из `sources/` и получить краткий профиль документа для последующего "
    "обновления wiki. Он читает только переданный source-файл, выделяет краткое содержание, "
    "тип документа, людей, метрики, продукты, процессы, правила и кандидатные смысловые "
    "разрезы по содержанию документа. Пример задачи: `проанализируй sources/doc_017.md "
    "и верни markdown-профиль`. Не используй его для чтения текущей wiki, проверки "
    "существующих dimensions, редактирования файлов, создания новых wiki-страниц или "
    "ответов пользователю по базе знаний."
)


def build_source_profiler_subagent_spec(
    *,
    model: Any,
    tools: list[Any],
    common_middleware: list[Any],
    skill_sources: list[str],
) -> dict[str, Any]:
    """Собирает параметры создания SourceProfilerSubagent.

    Args:
        model: Chat-модель LangChain для анализа source-документа.
        tools: Инструменты subagent. Ожидаются только read-only filesystem tools и
            загрузка skills, если она подключена в builder.
        common_middleware: Middleware, общие для document_wiki subagents.
        skill_sources: Виртуальные каталоги skills для нативного SkillsMiddleware.

    Returns:
        Словарь именованных аргументов, совместимый с ``create_deep_agent``.
    """

    return {
        "name": SOURCE_PROFILER_AGENT_NAME,
        "system_prompt": SOURCE_PROFILER_PROMPT,
        "model": model,
        "tools": list(tools),
        "skills": list(skill_sources),
        "middleware": list(common_middleware),
    }


__all__ = [
    "SOURCE_PROFILER_AGENT_DESCRIPTION",
    "SOURCE_PROFILER_AGENT_NAME",
    "build_source_profiler_subagent_spec",
]
