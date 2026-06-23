"""Middleware проверки фактической записи wiki-файлов.

Содержит:
- DocumentWikiWriteVerificationMiddleware: проверка write_file/edit_file через read_file backend.
- build_write_verification_message: формирование текста подтверждения записи.
- _file_path_from_tool_call: извлечение пути файла из tool call.
- _tool_name_from_request: извлечение имени tool.
- _tool_call_id_from_request: извлечение id tool call.
- _copy_tool_message_with_content: копирование ToolMessage с новым content.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.types import Command


WRITE_TOOLS = {"write_file", "edit_file"}
MAX_VERIFY_READ_LINES = 20_000


@dataclass(frozen=True)
class DocumentWikiWriteVerificationMiddleware(AgentMiddleware):
    """Проверяет, что файл доступен после успешного write_file/edit_file.

    Args:
        backend: DeepAgents filesystem backend с методом ``read``.
        enabled: Включена ли проверка записи.

    Returns:
        Middleware, который добавляет к результату write/edit tool подтверждение
        фактического чтения записанного файла или переводит результат в ошибку.
    """

    backend: Any
    enabled: bool = True

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Выполняет tool call и проверяет результат записи.

        Args:
            request: Запрос tool call от агента.
            handler: Следующий обработчик tool call.

        Returns:
            Результат tool call с добавленным подтверждением записи для write/edit.
        """

        result = handler(request)
        if not self.enabled or not isinstance(result, ToolMessage):
            return result
        return self._verify_result(request, result)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """Асинхронно выполняет tool call и проверяет результат записи.

        Args:
            request: Запрос tool call от агента.
            handler: Следующий асинхронный обработчик tool call.

        Returns:
            Результат tool call с добавленным подтверждением записи для write/edit.
        """

        result = await handler(request)
        if not self.enabled or not isinstance(result, ToolMessage):
            return result
        return self._verify_result(request, result)

    def _verify_result(
        self,
        request: ToolCallRequest,
        result: ToolMessage,
    ) -> ToolMessage:
        """Проверяет ToolMessage после write_file/edit_file.

        Args:
            request: Исходный запрос tool call.
            result: Результат tool call.

        Returns:
            ToolMessage с подтверждением или ошибкой проверки записи.
        """

        tool_name = _tool_name_from_request(request)
        if tool_name not in WRITE_TOOLS or result.status == "error":
            return result

        file_path = _file_path_from_tool_call(request)
        if not file_path:
            return _copy_tool_message_with_content(
                result,
                f"{result.content.rstrip()}\n\n"
                "DocumentWikiWriteVerification: не удалось определить путь файла для проверки записи.",
                status="error",
            )

        verification = build_write_verification_message(self.backend, file_path)
        if verification.startswith("DocumentWikiWriteVerificationError:"):
            return _copy_tool_message_with_content(
                result,
                f"{result.content.rstrip()}\n\n{verification}",
                status="error",
            )
        return _copy_tool_message_with_content(
            result,
            f"{result.content.rstrip()}\n\n{verification}",
        )


def build_write_verification_message(backend: Any, file_path: str) -> str:
    """Проверяет файл через backend.read и возвращает сообщение для агента.

    Args:
        backend: DeepAgents filesystem backend с методом ``read``.
        file_path: Путь файла из аргументов write_file/edit_file.

    Returns:
        Текст подтверждения или ошибки проверки записи.
    """

    read = getattr(backend, "read", None)
    if not callable(read):
        return (
            "DocumentWikiWriteVerificationError: backend не поддерживает проверочное "
            f"чтение файла `{file_path}`."
        )

    read_result = read(file_path, offset=0, limit=MAX_VERIFY_READ_LINES)
    error = getattr(read_result, "error", None)
    if error:
        return (
            "DocumentWikiWriteVerificationError: файл не подтвержден после записи "
            f"`{file_path}`: {error}"
        )

    file_data = getattr(read_result, "file_data", None)
    content = "" if not file_data else str(file_data.get("content") or "")
    if not content:
        return (
            "DocumentWikiWriteVerificationError: файл не подтвержден после записи "
            f"`{file_path}`: содержимое не получено."
        )

    line_count = len(content.splitlines())
    return (
        "DocumentWikiWriteVerification: файл "
        f"`{file_path}` фактически прочитан после записи; "
        f"подтверждено строк: {line_count}."
    )


def _file_path_from_tool_call(request: ToolCallRequest) -> str:
    """Извлекает путь файла из аргументов tool call.

    Args:
        request: Запрос tool call.

    Returns:
        Путь файла или пустую строку, если аргумент не найден.
    """

    args = dict((request.tool_call or {}).get("args") or {})
    return str(args.get("file_path") or args.get("path") or "").strip()


def _tool_name_from_request(request: ToolCallRequest) -> str:
    """Извлекает имя tool из запроса.

    Args:
        request: Запрос tool call.

    Returns:
        Имя инструмента или ``tool``.
    """

    tool_call = request.tool_call or {}
    return str(tool_call.get("name") or "tool")


def _tool_call_id_from_request(request: ToolCallRequest) -> str:
    """Извлекает id tool call из запроса.

    Args:
        request: Запрос tool call.

    Returns:
        Идентификатор tool call или пустую строку.
    """

    tool_call = request.tool_call or {}
    return str(tool_call.get("id") or "")


def _copy_tool_message_with_content(
    message: ToolMessage,
    content: str,
    *,
    status: str | None = None,
) -> ToolMessage:
    """Копирует ToolMessage, заменяя content и при необходимости status.

    Args:
        message: Исходный ToolMessage.
        content: Новый текст результата tool.
        status: Новый статус или ``None`` для сохранения исходного.

    Returns:
        Новый ToolMessage с сохранением metadata.
    """

    return ToolMessage(
        content=content,
        artifact=message.artifact,
        tool_call_id=message.tool_call_id,
        name=message.name,
        status=status or message.status,
        additional_kwargs=message.additional_kwargs,
        response_metadata=message.response_metadata,
        id=message.id,
    )


__all__ = [
    "DocumentWikiWriteVerificationMiddleware",
    "build_write_verification_message",
]
