"""Запуск поиска по wiki-базе.

Содержит:
- build_search_message: подготовка пользовательского сообщения для search agent.
- main: CLI-точка входа для поиска по базе.
"""

import argparse

from agents.common import get_last_message_text
from agents.search_agent import search_agent


def build_search_message(question: str) -> str:
    """Формирует запрос к search deepagent.

    Входные данные:
    - question: вопрос пользователя по документной базе.

    Возвращает:
    - str: текст сообщения для search deepagent.
    """

    return question


def main() -> None:
    """Запускает search deepagent из командной строки.

    Входные данные:
    - аргумент CLI `question`: вопрос пользователя.

    Возвращает:
    - None: печатает ответ агента в stdout.
    """

    parser = argparse.ArgumentParser(description="Найти ответ в LLM wiki.")
    parser.add_argument("question", nargs="+", help="Вопрос по базе документов")
    args = parser.parse_args()

    result = search_agent.invoke(
        {"messages": [{"role": "user", "content": build_search_message(" ".join(args.question))}]}
    )
    print(get_last_message_text(result))


if __name__ == "__main__":
    main()
