"""Deepagent для поиска ответов по wiki и source-файлам.

Содержит:
- create_search_agent: создание search deepagent.
- search_agent: готовый deepagent для поиска.
"""

from deepagents import create_deep_agent

from agents.common import (
    create_model_retry_middleware,
    create_project_backend,
    ensure_project_dirs,
    register_project_profile,
)
from model import model
from prompts import QUERY_AGENT_PROMPT


def create_search_agent():
    """Создает deepagent для поиска ответов по базе документов.

    Входные данные:
    - нет.

    Возвращает:
    - CompiledStateGraph: готовый Deep Agents graph для чтения wiki и sources.
    """

    ensure_project_dirs()
    register_project_profile()

    return create_deep_agent(
        model=model,
        tools=[],
        system_prompt=QUERY_AGENT_PROMPT,
        middleware=[create_model_retry_middleware()],
        subagents=[],
        backend=create_project_backend(),
        name="wiki-search",
    )


search_agent = create_search_agent()
