"""Автономный runtime-каркас document_wiki для DeepAgents.

Содержит:
- DocumentWikiFilesystemBackend: filesystem backend с явной UTF-8 записью.
- FilesystemPathContractMiddleware: нормализация путей filesystem tools и проверка записи.
- PromptToolDescriptionsMiddleware: замена описаний встроенных tools перед вызовом модели.
- ThinkToolMiddleware: добавление tool ``think`` для короткой промежуточной структуризации.
- LoopBreakerMiddleware: подсказка при повторяющихся неуспешных tool-вызовах.
- build_gigachat_practices_prompt: prompt-довесок для стабильной работы GigaChat/KitAI.
- register_document_wiki_harness_profile: регистрация harness profile для DeepAgents.
"""

import json
import os
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deepagents import GeneralPurposeSubagentProfile, HarnessProfile, register_harness_profile
from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import WriteResult
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import BaseTool, tool
from langgraph.types import Command
from pydantic import Field


WRITE_TOOLS = {"write_file", "edit_file"}
MAX_VERIFY_LINES = 10_000
DOCUMENT_WIKI_HARNESS_PROFILE_KEYS = (
    "openai",
    "kitai",
    "gigachat",
    "deepagentskitaichatmodel",
    "GigaChat-3-Ultra",
    "deepagentskitaichatmodel:GigaChat-3-Ultra",
)

TOOL_DESCRIPTION_OVERRIDES = {
    "task": """
task
---
Description:
Runs one named subagent and returns its final report.

Use when:
- the step needs isolated context, such as source profiling, dimensions reading, or wiki writing.

Do not use when:
- one direct filesystem tool call is enough.
""".strip(),
    "read_file": """
read_file
---
Description:
Reads a text file from the document_wiki workspace.

Input:
- `file_path`: canonical POSIX path such as `/sources/doc_001.md` or `/wiki/index.md`.
- `offset`: first line to read.
- `limit`: maximum number of lines.

Use when:
- source markdown, index, dimension, or skill content is needed before deciding what to write.

Limitations:
- do not pass Windows paths;
- when using text from output in `edit_file`, remove display-only line numbers and pagination notices.
""".strip(),
    "write_file": """
write_file
---
Description:
Writes a complete text file in the document_wiki workspace.

Input:
- `file_path`: canonical POSIX path such as `/wiki/index.md`;
- `content`: complete file content.

Use when:
- creating a new wiki file;
- intentionally replacing a complete small wiki file.

Limitations:
- do not write under `/sources/`;
- do not create temporary plan files;
- do not report success until the tool result contains write verification.
""".strip(),
    "edit_file": """
edit_file
---
Description:
Edits an existing text file by replacing an exact fragment.

Input:
- `file_path`: canonical POSIX path such as `/wiki/dimensions/metrics.md`;
- `old_string`: exact existing fragment;
- `new_string`: replacement fragment;
- `replace_all`: whether to replace every occurrence.

Use when:
- updating an existing wiki file locally.

Limitations:
- if the string is not found, re-read the file and change the fragment instead of retrying blindly;
- do not report success until the tool result contains write verification.
""".strip(),
    "glob": """
glob
---
Description:
Finds files by glob pattern in document_wiki.

Input:
- `pattern`: glob pattern, for example `*.md` or `**/*.md`;
- `path`: base POSIX directory such as `/wiki` or `/sources`.
""".strip(),
    "grep": """
grep
---
Description:
Searches text in files.

Input:
- `pattern`: one search phrase;
- `path`: base POSIX directory;
- `glob`: file filter;
- `output_mode`: requested output mode.

Use when:
- locating source mentions, wiki dimensions, or already indexed terms.
""".strip(),
}

GIGACHAT_AGENT_PRACTICES_PROMPT = """
## GigaChat Execution Practices

These practices reduce tool-calling loops and formatting mistakes. They supplement the project, skill, role, and user
instructions above; they do not override them.

- Read the request literally and process every source file named by the task, not only the first file.
- If the task names output files, create or edit those exact files with filesystem tools.
- Do not claim that a file was created or updated unless a successful write/edit tool call happened.
- If a tool returns the same result or the same error twice, change the approach instead of trying it again.
- Use only tools that are actually available in the current agent run.

## Filesystem Tool Practices

- Filesystem tools use canonical POSIX workspace paths. The workspace root is `/`.
- Use paths such as `/sources/doc_001.md`, `/wiki/index.md`, and `/wiki/dimensions/metrics.md`.
- Do not pass Windows paths or host absolute paths to filesystem tools.
- Prefer `edit_file` for local changes and `write_file` for new wiki files.
- If `edit_file` says that the string was not found, re-read the file and build a new exact fragment.
- After generating a required wiki artifact, verify that it exists and is non-empty.
""".strip()


class DocumentWikiFilesystemBackend(FilesystemBackend):
    """FilesystemBackend с явной UTF-8 записью текстовых wiki-файлов.

    Args:
        *args: Позиционные аргументы базового ``FilesystemBackend``.
        **kwargs: Именованные аргументы базового ``FilesystemBackend``.

    Returns:
        Backend, совместимый с DeepAgents filesystem tools.
    """

    def write(self, file_path: str, content: str) -> WriteResult:
        """Записывает текстовый файл в UTF-8.

        Args:
            file_path: Виртуальный POSIX-путь внутри document_wiki.
            content: Полное текстовое содержимое файла.

        Returns:
            ``WriteResult`` с путем при успехе или текстом ошибки.
        """

        try:
            resolved_path = self._resolve_path(file_path)
        except (OSError, RuntimeError) as error:
            return WriteResult(error=f"Error writing file '{file_path}': {error}")

        try:
            resolved_path.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            descriptor = os.open(resolved_path, flags, 0o644)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as file:
                file.write(content)
            return WriteResult(path=file_path)
        except (OSError, UnicodeEncodeError) as error:
            return WriteResult(error=f"Error writing file '{file_path}': {error}")


@tool("think")
def _think(
    thought: str = Field(
        ...,
        description="Короткий промежуточный вывод или план следующего шага.",
    ),
) -> str:
    """Возвращает промежуточную мысль без побочных эффектов.

    Args:
        thought: Короткий текст, который помогает агенту структурировать следующий шаг.

    Returns:
        Тот же текст ``thought``.
    """

    return thought


class ThinkToolMiddleware(AgentMiddleware):
    """Добавляет tool ``think`` в runtime агента.

    Returns:
        Middleware с одним безопасным tool без доступа к файлам или внешним API.
    """

    tools = [_think]


@dataclass(frozen=True)
class PromptToolDescriptionsMiddleware(AgentMiddleware):
    """Заменяет descriptions tools перед вызовом модели.

    Args:
        tool_descriptions: Новые описания tools по имени инструмента.

    Returns:
        Middleware, меняющий только prompt-visible metadata tools.
    """

    tool_descriptions: Mapping[str, str]

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """Синхронно подменяет descriptions tools в запросе к модели.

        Args:
            request: Исходный запрос к модели.
            handler: Следующий обработчик model call.

        Returns:
            Ответ модели после вызова следующего обработчика.
        """

        return handler(self._override_request(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        """Асинхронно подменяет descriptions tools в запросе к модели.

        Args:
            request: Исходный запрос к модели.
            handler: Следующий асинхронный обработчик model call.

        Returns:
            Ответ модели после вызова следующего обработчика.
        """

        return await handler(self._override_request(request))

    def _override_request(self, request: ModelRequest) -> ModelRequest:
        """Создает копию запроса с обновленными descriptions.

        Args:
            request: Исходный запрос к модели.

        Returns:
            Новый ``ModelRequest``.
        """

        tools = _rewrite_tool_descriptions(request.tools, self.tool_descriptions)
        return request.override(tools=tools)


@dataclass(frozen=True)
class FilesystemPathContractMiddleware(AgentMiddleware):
    """Нормализует пути filesystem tools и проверяет успешную запись.

    Args:
        workspace_root: Реальный корень document_wiki.
        backend: Filesystem backend для проверочного чтения.
        enabled: Включена ли нормализация и проверка.

    Returns:
        Middleware, приводящий пути к POSIX-формату ``/path``.
    """

    workspace_root: Path
    backend: Any
    enabled: bool = True

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Выполняет tool call с нормализованными путями.

        Args:
            request: Запрос tool call.
            handler: Следующий обработчик tool call.

        Returns:
            Результат tool call или ошибка нормализации.
        """

        if not self.enabled:
            return handler(request)
        normalized_request = _normalize_filesystem_tool_call(
            request,
            workspace_root=self.workspace_root,
        )
        if isinstance(normalized_request, ToolMessage):
            return normalized_request
        result = handler(normalized_request)
        if isinstance(result, ToolMessage):
            return self._verify_write_result(normalized_request, result)
        return result

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """Асинхронно выполняет tool call с нормализованными путями.

        Args:
            request: Запрос tool call.
            handler: Следующий асинхронный обработчик tool call.

        Returns:
            Результат tool call или ошибка нормализации.
        """

        if not self.enabled:
            return await handler(request)
        normalized_request = _normalize_filesystem_tool_call(
            request,
            workspace_root=self.workspace_root,
        )
        if isinstance(normalized_request, ToolMessage):
            return normalized_request
        result = await handler(normalized_request)
        if isinstance(result, ToolMessage):
            return self._verify_write_result(normalized_request, result)
        return result

    def _verify_write_result(
        self,
        request: ToolCallRequest,
        result: ToolMessage,
    ) -> ToolMessage:
        """Проверяет успешный результат ``write_file`` или ``edit_file``.

        Args:
            request: Нормализованный запрос tool call.
            result: Результат filesystem tool.

        Returns:
            ToolMessage с подтверждением или ошибкой проверки.
        """

        tool_name = _tool_name_from_request(request)
        if tool_name not in WRITE_TOOLS or result.status == "error":
            return result
        verification = _verify_file_write(request, self.backend)
        if verification["status"] == "error":
            return _tool_message_with_content(
                result,
                str(verification["message"]),
                status="error",
            )
        return _tool_message_with_content(
            result,
            f"{result.content.rstrip()}\n\n{verification['message']}",
        )


class LoopBreakerMiddleware(AgentMiddleware):
    """Добавляет подсказку при повторяющихся неуспешных tool-вызовах.

    Returns:
        Middleware, которое перед model call добавляет HumanMessage с рекомендацией сменить подход.
    """

    name = "LoopBreakerMiddleware"

    def before_model(self, state: Any, runtime: Any) -> dict[str, Any] | None:
        """Добавляет корректирующую подсказку перед model call.

        Args:
            state: State агента с историей сообщений.
            runtime: Runtime LangGraph, не используется.

        Returns:
            ``{"messages": [HumanMessage(...)]}`` или ``None``.
        """

        messages = _messages_from_state(state)
        pairs = _last_n_tool_pairs(messages, 3)
        if not pairs:
            return None
        all_same_call = pairs[0] == pairs[1] == pairs[2]
        all_errors = all(_result_is_error(pair[2]) for pair in pairs)
        if not all_same_call and not all_errors:
            return None
        if _already_nudged(messages, "[LOOP-BREAKER]"):
            return None
        tool_name = pairs[0][0]
        last_result = pairs[0][2][:300]
        return {
            "messages": [
                HumanMessage(
                    content=(
                        "[LOOP-BREAKER] You have repeated an ineffective tool pattern "
                        f"with `{tool_name}`. Last result: {last_result!r}. "
                        "Change strategy: re-read the relevant file, use canonical POSIX paths, "
                        "or write/update the required wiki file directly."
                    )
                )
            ]
        }


def build_gigachat_practices_prompt() -> str:
    """Возвращает prompt-довесок с практиками GigaChat/KitAI.

    Returns:
        Строка с дополнительными правилами выполнения задач.
    """

    return GIGACHAT_AGENT_PRACTICES_PROMPT


def register_document_wiki_harness_profile(
    *,
    enable_general_purpose: bool = False,
) -> None:
    """Регистрирует harness profile document_wiki для известных provider keys.

    Args:
        enable_general_purpose: Нужно ли включать штатный ``general-purpose`` subagent.

    Returns:
        ``None``.
    """

    for profile_key in DOCUMENT_WIKI_HARNESS_PROFILE_KEYS:
        register_harness_profile(
            profile_key,
            HarnessProfile(
                tool_description_overrides=TOOL_DESCRIPTION_OVERRIDES,
                excluded_tools=frozenset(),
                general_purpose_subagent=GeneralPurposeSubagentProfile(
                    enabled=enable_general_purpose
                ),
            ),
        )


def normalize_filesystem_tool_path(value: str, workspace_root: Path) -> str:
    """Приводит путь filesystem tool к canonical POSIX-виду от корня workspace.

    Args:
        value: Путь из аргументов tool call.
        workspace_root: Реальный корень document_wiki.

    Returns:
        POSIX-путь вида ``/wiki/index.md``.

    Raises:
        ValueError: Путь пустой или абсолютный OS-путь указывает вне workspace.
    """

    raw_path = str(value or "").strip()
    if not raw_path:
        raise ValueError("Путь filesystem tool не может быть пустым.")

    normalized = raw_path.replace("\\", "/")
    candidate = Path(raw_path)
    if candidate.is_absolute():
        resolved = candidate.expanduser().resolve()
        try:
            relative_path = resolved.relative_to(workspace_root.resolve())
        except ValueError:
            raise ValueError(
                "Filesystem tool принимает только пути внутри document_wiki workspace "
                f"или POSIX-пути вида `/path`: {raw_path}"
            ) from None
        normalized_relative = relative_path.as_posix()
        return "/" if not normalized_relative else f"/{normalized_relative}"

    normalized_relative = normalized.lstrip("/")
    if not normalized_relative:
        return "/"
    return f"/{normalized_relative}"


def _rewrite_tool_descriptions(
    tools: list[BaseTool | dict[str, Any]],
    descriptions: Mapping[str, str],
) -> list[BaseTool | dict[str, Any]]:
    """Возвращает копию tools с переопределенными descriptions.

    Args:
        tools: Инструменты модели.
        descriptions: Новые descriptions по имени инструмента.

    Returns:
        Новый список tools.
    """

    rewritten: list[BaseTool | dict[str, Any]] = []
    for tool_item in tools:
        name = tool_item.get("name") if isinstance(tool_item, dict) else getattr(tool_item, "name", None)
        description = descriptions.get(str(name)) if name else None
        if description is None:
            rewritten.append(tool_item)
            continue
        if isinstance(tool_item, dict):
            copied = dict(tool_item)
            copied["description"] = description
            rewritten.append(copied)
        else:
            rewritten.append(tool_item.model_copy(update={"description": description}))
    return rewritten


def _normalize_filesystem_tool_call(
    request: ToolCallRequest,
    *,
    workspace_root: Path,
) -> ToolCallRequest | ToolMessage:
    """Нормализует аргумент пути в filesystem tool call.

    Args:
        request: Исходный запрос tool call.
        workspace_root: Реальный корень document_wiki.

    Returns:
        Новый ``ToolCallRequest`` или ``ToolMessage`` с ошибкой.
    """

    tool_name = _tool_name_from_request(request)
    path_arg = _file_path_arg_name(tool_name)
    if path_arg is None:
        return request

    args = dict((request.tool_call or {}).get("args") or {})
    if path_arg not in args:
        return request
    try:
        args[path_arg] = normalize_filesystem_tool_path(
            str(args[path_arg]),
            workspace_root.resolve(),
        )
    except ValueError as error:
        return ToolMessage(
            content=f"ValueError: {error}",
            tool_call_id=_tool_call_id_from_request(request),
            name=tool_name,
            status="error",
        )

    tool_call = dict(request.tool_call or {})
    tool_call["args"] = args
    return request.override(tool_call=tool_call)


def _verify_file_write(request: ToolCallRequest, backend: Any) -> dict[str, str]:
    """Проверяет доступность файла после успешного write/edit.

    Args:
        request: Нормализованный запрос ``write_file`` или ``edit_file``.
        backend: Backend с методом ``read``.

    Returns:
        Словарь со статусом и сообщением.
    """

    args = dict((request.tool_call or {}).get("args") or {})
    file_path = str(args.get("file_path") or "")
    read = getattr(backend, "read", None)
    if not callable(read):
        return {
            "status": "error",
            "message": f"FilesystemVerificationError: backend не поддерживает чтение `{file_path}`.",
        }

    read_result = read(file_path, offset=0, limit=MAX_VERIFY_LINES)
    error = getattr(read_result, "error", None)
    if error:
        return {
            "status": "error",
            "message": f"FilesystemVerificationError: файл не подтвержден после записи `{file_path}`: {error}",
        }
    file_data = getattr(read_result, "file_data", None)
    if not file_data or "content" not in file_data:
        return {
            "status": "error",
            "message": f"FilesystemVerificationError: содержимое `{file_path}` не получено после записи.",
        }
    return {
        "status": "success",
        "message": f"FilesystemVerification: файл `{file_path}` прочитан после записи; сохранение подтверждено.",
    }


def _file_path_arg_name(tool_name: str) -> str | None:
    """Возвращает имя path-аргумента для filesystem tool.

    Args:
        tool_name: Имя инструмента.

    Returns:
        Имя аргумента пути или ``None``.
    """

    if tool_name in {"read_file", "write_file", "edit_file"}:
        return "file_path"
    if tool_name in {"ls", "glob", "grep"}:
        return "path"
    return None


def _tool_name_from_request(request: ToolCallRequest) -> str:
    """Извлекает имя tool из запроса.

    Args:
        request: Запрос tool call.

    Returns:
        Имя инструмента.
    """

    tool_call = request.tool_call or {}
    return str(tool_call.get("name") or "tool")


def _tool_call_id_from_request(request: ToolCallRequest) -> str:
    """Извлекает id tool call из запроса.

    Args:
        request: Запрос tool call.

    Returns:
        Идентификатор tool call или пустая строка.
    """

    tool_call = request.tool_call or {}
    return str(tool_call.get("id") or "")


def _tool_message_with_content(
    message: ToolMessage,
    content: str,
    *,
    status: str | None = None,
) -> ToolMessage:
    """Копирует ToolMessage с новым content.

    Args:
        message: Исходный ToolMessage.
        content: Новый текст результата.
        status: Новый статус или ``None``.

    Returns:
        Новый ToolMessage.
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


def _messages_from_state(state: Any) -> list[Any]:
    """Извлекает сообщения из state middleware.

    Args:
        state: Mapping-like или object-like state.

    Returns:
        Список сообщений.
    """

    if isinstance(state, dict):
        messages = state.get("messages")
    else:
        messages = getattr(state, "messages", None)
    return list(messages or [])


def _last_n_tool_pairs(messages: list[Any], n: int) -> list[tuple[str, str, str]] | None:
    """Возвращает последние ``n`` пар tool call/result.

    Args:
        messages: История сообщений.
        n: Требуемое число пар.

    Returns:
        Список кортежей или ``None``.
    """

    pairs: list[tuple[str, str, str]] = []
    index = len(messages) - 1
    while index >= 0 and len(pairs) < n:
        message = messages[index]
        if isinstance(message, ToolMessage):
            if index == 0:
                return None
            ai_message = messages[index - 1]
            if not isinstance(ai_message, AIMessage):
                return None
            tool_calls = getattr(ai_message, "tool_calls", None) or []
            if not tool_calls:
                return None
            tool_call = tool_calls[0]
            content = message.content if isinstance(message.content, str) else str(message.content)
            pairs.append(
                (
                    tool_call.get("name", ""),
                    json.dumps(tool_call.get("args", {}), ensure_ascii=False, sort_keys=True),
                    content,
                )
            )
            index -= 2
            continue
        if isinstance(message, AIMessage):
            index -= 1
            continue
        break
    return pairs if len(pairs) == n else None


def _result_is_error(text: str) -> bool:
    """Проверяет, похож ли tool result на ошибку.

    Args:
        text: Текст результата.

    Returns:
        ``True``, если найден маркер ошибки.
    """

    markers = (
        "Error:",
        "error:",
        "Traceback",
        "FileNotFoundError",
        "String not found",
        "ValueError:",
        "FilesystemVerificationError",
        "DocumentWikiWriteVerificationError",
    )
    return any(marker in str(text or "") for marker in markers)


def _already_nudged(messages: list[Any], marker: str) -> bool:
    """Проверяет, была ли уже добавлена подсказка с маркером.

    Args:
        messages: История сообщений.
        marker: Маркер подсказки.

    Returns:
        ``True``, если подсказка уже была.
    """

    for message in reversed(messages):
        content = getattr(message, "content", "") or ""
        if isinstance(content, str) and marker in content:
            return True
        if isinstance(message, AIMessage):
            break
    return False


__all__ = [
    "DocumentWikiFilesystemBackend",
    "FilesystemPathContractMiddleware",
    "LoopBreakerMiddleware",
    "PromptToolDescriptionsMiddleware",
    "ThinkToolMiddleware",
    "TOOL_DESCRIPTION_OVERRIDES",
    "build_gigachat_practices_prompt",
    "normalize_filesystem_tool_path",
    "register_document_wiki_harness_profile",
]
