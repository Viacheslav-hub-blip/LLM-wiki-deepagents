"""Запуск добавления или обновления wiki-базы.

Содержит:
- build_ingest_message: подготовка пользовательского сообщения для supervisor.
- main: CLI-точка входа для добавления source-файла.
"""

import argparse

from agents.common import get_last_message_text
from agents.ingest_agent import ingest_agent


def build_ingest_message(source_path: str) -> str:
    """Формирует запрос к ingest supervisor.

    Входные данные:
    - source_path: путь к markdown source-файлу относительно корня проекта.

    Возвращает:
    - str: текст сообщения для supervisor deepagent.
    """

    return f"Добавь или обнови wiki-базу по source-файлу: `{source_path}`."


def main() -> None:
    """Запускает ingest deepagent из командной строки.

    Входные данные:
    - аргумент CLI `source_path`: путь к source-файлу.

    Возвращает:
    - None: печатает итог работы агента в stdout.
    """

    parser = argparse.ArgumentParser(description="Добавить source-файл в LLM wiki.")
    parser.add_argument("source_path", help="Путь к source-файлу, например sources/doc_001.md")
    args = parser.parse_args()

    result = ingest_agent.invoke(
        {"messages": [{"role": "user", "content": build_ingest_message(args.source_path)}]}
    )
    print(get_last_message_text(result))


if __name__ == "__main__":
    main()
