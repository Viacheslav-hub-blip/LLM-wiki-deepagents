"""Entrypoint для запуска ingest-agent по одному или нескольким source markdown-файлам.

Содержит:
- run_document_wiki_ingest: запуск добавления одного source-файла в wiki.
- build_ingest_message: сборка пользовательского сообщения для IngestSupervisor.
- main: запуск ingest-agent из IDE по списку source-файлов.
- collect_wiki_snapshot: сбор фактического состояния wiki-файлов.
- format_wiki_change_report: формирование отчета о реальных изменениях wiki.
- format_wiki_files_report: формирование отчета о фактических wiki-файлах.
- build_ingest_model: создание модели для запуска ingest-agent.
- source_paths_to_process: получение списка source-файлов для обработки.
- has_wiki_changes: проверка наличия фактических изменений wiki.
- build_no_change_retry_instruction: сборка инструкции для повторной попытки записи.
- _last_message_text: извлечение текста последнего сообщения агента.
"""

import hashlib
import sys
import time
from pathlib import Path
from typing import Any

import urllib3

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from document_wiki.agent import build_document_wiki_ingest_agent
from document_wiki.paths import relative_to_document_wiki, require_inside_document_wiki
from document_wiki.settings import DocumentWikiSettings, load_document_wiki_settings


urllib3.disable_warnings()


DEFAULT_RECURSION_LIMIT = 100
DEFAULT_THREAD_ID = "document-wiki-ingest-ide"
MAX_NO_CHANGE_RETRIES = 1
WORKSPACE_ROOT = "."
DOCUMENT_WIKI_ROOT = None
SOURCE_PATH = "sources/doc_002.md"
SOURCE_PATHS = [
    "sources/doc_002.md",
]
PROCESS_ALL_SOURCES = False

KITAI_HOST_SDK = "https://hcscr-ift.delta.sbrf.ru"
CERT_FILE_PATH = r"C:\Users\23111424\IdeaProjects\FirstTest\src\config\client_crt.crt"
CERT_KEY_FILE_PATH = r"C:\Users\23111424\IdeaProjects\FirstTest\src\config\client_key.key"
KITAI_MODEL_NAME = "GigaChat-3-Ultra"
KITAI_SYSTEM_NAME = "csp_lab"
KITAI_MODULE_NAME = "csp_lab_antifraud_edge"


def run_document_wiki_ingest(
    *,
    model: Any | None = None,
    source_path: str | Path,
    settings: DocumentWikiSettings | None = None,
    workspace_root: str | Path | None = None,
    document_wiki_root: str | Path | None = None,
    invoke_config: dict[str, Any] | None = None,
    extra_instruction: str | None = None,
) -> Any:
    """Запускает ingest-agent для уже существующего source markdown-файла.

    Args:
        model: Chat-модель LangChain для запуска document_wiki ingest-agent. Если
            значение не передано, используется OpenRouter-модель из корневого ``model.py``.
        source_path: Путь к готовому source-файлу внутри директории document_wiki.
        settings: Готовые настройки document_wiki. Если не переданы, создаются из
            ``workspace_root`` и ``document_wiki_root``.
        workspace_root: Корень рабочего окружения, если ``settings`` не переданы.
        document_wiki_root: Корень директории document_wiki, если ``settings`` не переданы.
        invoke_config: Дополнительный config для вызова LangGraph agent.
        extra_instruction: Дополнительная инструкция для текущего запуска ingest-agent.

    Returns:
        Результат выполнения ingest-agent.

    Raises:
        FileNotFoundError: Source-файл не найден.
        ValueError: Source-файл находится вне директории document_wiki.
    """

    resolved_settings = settings or load_document_wiki_settings(
        workspace_root=workspace_root,
        document_wiki_root=document_wiki_root,
    )
    run_model = model or build_ingest_model()
    resolved_source_path = Path(source_path)
    if not resolved_source_path.is_absolute():
        resolved_source_path = resolved_settings.document_wiki_root / resolved_source_path
    resolved_source_path = resolved_source_path.resolve()

    require_inside_document_wiki(resolved_settings, resolved_source_path)
    if not resolved_source_path.is_file():
        raise FileNotFoundError(f"Source-файл не найден: {resolved_source_path}")

    source_path_for_agent = relative_to_document_wiki(
        resolved_settings,
        resolved_source_path,
    )
    agent = build_document_wiki_ingest_agent(
        model=run_model,
        settings=resolved_settings,
    )
    return agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": build_ingest_message(
                        source_path_for_agent,
                        extra_instruction=extra_instruction,
                    ),
                }
            ]
        },
        config=invoke_config,
    )


def build_ingest_message(source_path: str, *, extra_instruction: str | None = None) -> str:
    """Собирает пользовательское сообщение для IngestSupervisor.

    Args:
        source_path: POSIX-путь к source-файлу относительно директории document_wiki.
        extra_instruction: Дополнительная инструкция для усиления конкретного запуска.

    Returns:
        Текст сообщения для запуска ingest-процесса.
    """

    message = (
        "Добавь markdown-файл в document_wiki.\n\n"
        f"source_path: {source_path}\n\n"
        "Файл уже существует в sources/.\n"
        "Финальный ответ должен опираться только на реально выполненные write_file/edit_file. "
        "Не пиши, что wiki-файл создан или обновлен, если соответствующий tool call не был выполнен."
    )
    if extra_instruction:
        message = f"{message}\n\nДополнительная инструкция:\n{extra_instruction}"
    return message


def build_ingest_model() -> Any:
    """Создает модель для запуска document_wiki ingest-agent.

    Args:
        Отсутствуют. Функция использует константы подключения KitAI в этом модуле.

    Returns:
        Chat-модель, совместимая с DeepAgents.
    """

    from Deepagent_adapter import DeepAgentsKitaiChatModel

    return DeepAgentsKitaiChatModel(
        model=KITAI_MODEL_NAME,
        kitai_host_sdk=KITAI_HOST_SDK,
        cert_file=CERT_FILE_PATH,
        key_file=CERT_KEY_FILE_PATH,
        system_name=KITAI_SYSTEM_NAME,
        module_name=KITAI_MODULE_NAME,
    )


def source_paths_to_process(settings: DocumentWikiSettings) -> list[str]:
    """Возвращает список source-файлов для обработки.

    Args:
        settings: Настройки document_wiki с путем к директории sources.

    Returns:
        Список POSIX-путей source-файлов относительно директории document_wiki.
    """

    if PROCESS_ALL_SOURCES:
        return [
            path.relative_to(settings.document_wiki_root).as_posix()
            for path in sorted(settings.sources_dir.glob("*.md"))
            if path.is_file()
        ]
    if SOURCE_PATHS:
        return list(SOURCE_PATHS)
    return [SOURCE_PATH]


def main() -> int:
    """Запускает ingest-agent из IDE по константам модуля.

    Args:
        Отсутствуют. Параметры запуска задаются константами модуля.

    Returns:
        Код завершения процесса: ``0`` при успешном запуске.
    """

    settings = load_document_wiki_settings(
        workspace_root=WORKSPACE_ROOT,
        document_wiki_root=DOCUMENT_WIKI_ROOT,
    )
    run_model = build_ingest_model()

    for source_path in source_paths_to_process(settings):
        started_at = time.perf_counter()
        print(f"\nОбработка файла: {source_path}")
        for attempt in range(MAX_NO_CHANGE_RETRIES + 1):
            before_snapshot = collect_wiki_snapshot(settings.document_wiki_root)
            retry_instruction = None
            if attempt > 0:
                retry_instruction = build_no_change_retry_instruction(source_path)
                print("Повторная попытка: предыдущий запуск не изменил ни одного wiki-файла.")
            try:
                result = run_document_wiki_ingest(
                    model=run_model,
                    source_path=source_path,
                    settings=settings,
                    invoke_config={
                        "recursion_limit": DEFAULT_RECURSION_LIMIT,
                        "configurable": {
                            "thread_id": f"{DEFAULT_THREAD_ID}-{Path(source_path).stem}-attempt-{attempt + 1}"
                        },
                    },
                    extra_instruction=retry_instruction,
                )
            except Exception as error:  # noqa: BLE001
                print(f"Ошибка при обработке {source_path}: {error}")
                break

            after_snapshot = collect_wiki_snapshot(settings.document_wiki_root)
            print(_last_message_text(result))
            print()
            print(format_wiki_change_report(before_snapshot, after_snapshot))
            if has_wiki_changes(before_snapshot, after_snapshot):
                break
            if attempt == MAX_NO_CHANGE_RETRIES:
                print(
                    "ОШИБКА КОНТРОЛЯ: агент завершил обработку, но физические wiki-файлы "
                    f"не изменились для {source_path}."
                )
        print(f"Время обработки: {time.perf_counter() - started_at:.2f} секунд")

    print()
    print(format_wiki_files_report(settings.document_wiki_root))
    return 0


def collect_wiki_snapshot(
    document_wiki_root: str | Path | None = DOCUMENT_WIKI_ROOT,
) -> dict[str, dict[str, str | int]]:
    """Собирает фактическое состояние файлов в директории wiki.

    Args:
        document_wiki_root: Корень директории document_wiki или ``None`` для папки
            рядом с текущим файлом.

    Returns:
        Словарь ``путь -> метаданные`` с размером и SHA-256 содержимого файла.
    """

    root = _resolve_document_wiki_root(document_wiki_root)
    wiki_root = root / "wiki"
    if not wiki_root.exists():
        return {}

    snapshot: dict[str, dict[str, str | int]] = {}
    for path in sorted(wiki_root.rglob("*")):
        if not path.is_file():
            continue
        content = path.read_bytes()
        relative_path = path.relative_to(root).as_posix()
        snapshot[relative_path] = {
            "size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    return snapshot


def format_wiki_change_report(
    before: dict[str, dict[str, str | int]],
    after: dict[str, dict[str, str | int]],
) -> str:
    """Формирует отчет о реальных изменениях wiki после ingest.

    Args:
        before: Snapshot wiki-файлов до запуска ingest-agent.
        after: Snapshot wiki-файлов после запуска ingest-agent.

    Returns:
        Markdown-отчет со списком реально созданных, измененных и удаленных файлов.
    """

    before_paths = set(before)
    after_paths = set(after)
    created = sorted(after_paths - before_paths)
    deleted = sorted(before_paths - after_paths)
    changed = sorted(
        path
        for path in before_paths & after_paths
        if before[path].get("sha256") != after[path].get("sha256")
    )

    lines = ["## Фактические изменения wiki"]
    if not created and not changed and not deleted:
        lines.append("Созданных, измененных или удаленных wiki-файлов не обнаружено.")
        return "\n".join(lines)

    if created:
        lines.append("")
        lines.append("### Создано фактически")
        lines.extend(f"- {path} ({after[path]['size']} байт)" for path in created)
    if changed:
        lines.append("")
        lines.append("### Изменено фактически")
        lines.extend(
            f"- {path} ({before[path]['size']} -> {after[path]['size']} байт)"
            for path in changed
        )
    if deleted:
        lines.append("")
        lines.append("### Удалено фактически")
        lines.extend(f"- {path}" for path in deleted)
    return "\n".join(lines)


def has_wiki_changes(
    before: dict[str, dict[str, str | int]],
    after: dict[str, dict[str, str | int]],
) -> bool:
    """Проверяет, были ли фактические изменения wiki-файлов.

    Args:
        before: Snapshot wiki-файлов до запуска ingest-agent.
        after: Snapshot wiki-файлов после запуска ingest-agent.

    Returns:
        ``True``, если wiki-файлы были созданы, изменены или удалены.
    """

    before_paths = set(before)
    after_paths = set(after)
    if before_paths != after_paths:
        return True
    return any(before[path].get("sha256") != after[path].get("sha256") for path in before_paths)


def build_no_change_retry_instruction(source_path: str) -> str:
    """Собирает инструкцию для повторной попытки, если wiki не изменилась.

    Args:
        source_path: POSIX-путь к source-файлу относительно директории document_wiki.

    Returns:
        Текст инструкции для повторного запуска ingest-agent.
    """

    return (
        f"Предыдущая попытка обработки `{source_path}` не изменила ни одного физического wiki-файла. "
        "Повтори обработку этого же source-файла заново. Обязательно прочитай source-файл, затем "
        "выполни write_file или edit_file для wiki/index.md и для всех релевантных файлов "
        "wiki/dimensions/*.md. Если нужно создать новый dimension-файл, создай его через write_file. "
        "Не завершай работу финальным ответом, пока фактически не выполнишь запись wiki-файлов."
    )


def format_wiki_files_report(
    document_wiki_root: str | Path | None = DOCUMENT_WIKI_ROOT,
) -> str:
    """Формирует отчет о фактически существующих wiki-файлах.

    Args:
        document_wiki_root: Корень директории document_wiki или ``None`` для папки
            рядом с текущим файлом.

    Returns:
        Markdown-отчет со списком файлов в `wiki/`.
    """

    root = _resolve_document_wiki_root(document_wiki_root)
    wiki_root = root / "wiki"
    if not wiki_root.exists():
        return "## Фактические wiki-файлы\nwiki/ не существует."

    files = sorted(path.relative_to(root).as_posix() for path in wiki_root.rglob("*") if path.is_file())
    if not files:
        return "## Фактические wiki-файлы\nФайлы не найдены."
    lines = ["## Фактические wiki-файлы", *[f"- {path}" for path in files]]
    return "\n".join(lines)


def _resolve_document_wiki_root(document_wiki_root: str | Path | None) -> Path:
    """Возвращает абсолютный путь к директории document_wiki.

    Args:
        document_wiki_root: Явный путь к document_wiki или ``None``.

    Returns:
        Абсолютный путь к директории document_wiki.
    """

    if document_wiki_root is None:
        return Path(__file__).resolve().parent
    return Path(document_wiki_root).resolve()


def _last_message_text(result: Any) -> str:
    """Достает текст последнего сообщения агента из результата invoke.

    Args:
        result: Словарь состояния, который вернул ``agent.invoke``.

    Returns:
        Текст последнего сообщения или строковое представление результата.
    """

    if not isinstance(result, dict):
        return str(result)
    messages = result.get("messages") or []
    if not messages:
        return str(result)
    last_message = messages[-1]
    text = getattr(last_message, "text", None)
    if isinstance(text, str) and text:
        return text
    content = getattr(last_message, "content", None)
    if isinstance(content, str):
        return content
    return str(last_message)


__all__ = [
    "build_ingest_message",
    "build_ingest_model",
    "build_no_change_retry_instruction",
    "collect_wiki_snapshot",
    "format_wiki_change_report",
    "format_wiki_files_report",
    "has_wiki_changes",
    "main",
    "run_document_wiki_ingest",
    "source_paths_to_process",
]


if __name__ == "__main__":
    raise SystemExit(main())
