# Document Wiki

`document_wiki` — отдельная переносимая архитектура DeepAgent для добавления и поиска знаний по готовым markdown-документам.

Папка не зависит от текущего аналитического агента проекта. В будущем ее можно будет перенести в целевое окружение или подключить как отдельный subagent/tool к другому supervisor.

## Основная Идея

Система работает с двумя файловыми слоями:

```text
sources/ — исходные markdown-документы, источник истины
wiki/    — навигационная карта знаний по документам
```

`sources/` не редактируется агентами после сохранения документа.

`wiki/` обновляется ingest-agent и используется query-agent для выбора релевантных source-файлов.

## Ожидаемая Структура

```text
document_wiki/
  sources/
    doc_001.md
    doc_002.md

  wiki/
    index.md
    dimensions/
      metrics.md
      products.md

  skills/
    source-profiling/
      SKILL.md
    dimensions-reading/
      SKILL.md
    wiki-writing/
      SKILL.md
    wiki-query/
      SKILL.md
```

Source-файл уже должен существовать в `sources/` до запуска ingest-agent. В текущей версии нет отдельного backend-слоя для создания markdown-файла.

## Агенты

В `agent.py` есть две функции сборки:

```python
build_document_wiki_ingest_agent(...)
build_document_wiki_query_agent(...)
```

Для прямого вызова есть helper-функции:

```python
run_document_wiki_ingest(...)
run_document_wiki_query(...)
```

Они принимают готовую LangChain-модель через аргумент `model`. Внутри `document_wiki` нет чтения API-ключей и нет создания модели по умолчанию.

Если `model` не передан в `run_document_wiki_ingest(...)` или `run_document_wiki_query(...)`,
helper-функции используют `document_wiki.openrouter_runtime.load_openrouter_model()`.
Этот модуль выставляет те же OpenRouter defaults, что и корневой `run.py`, а затем импортирует
`model` из корневого `model.py`.

API-ключ не задается внутри `document_wiki`. Для реального запуска он должен быть установлен
во внешнем окружении, например:

```powershell
$env:OPENAI_API_KEY = "<OPENROUTER_API_KEY>"
```

Если запускать `run_ingest.py` или `run_query.py` из терминала без установленного
`OPENAI_API_KEY`, файл попросит ввести ключ для текущего процесса через скрытый ввод.
Ключ не записывается в `.py` файлы и не сохраняется на диск.

`build_document_wiki_ingest_agent` собирает `IngestSupervisor`, который использует:

- `source-profiler` — анализирует один готовый source-файл и возвращает markdown-профиль;
- `dimensions-reader` — читает текущую wiki и возвращает compact wiki map;
- `wiki-writer` — обновляет `wiki/index.md` и релевантные `wiki/dimensions/*.md`.

Запись wiki-файлов дополнительно проверяется middleware `DocumentWikiWriteVerificationMiddleware`.
После `write_file` или `edit_file` middleware читает записанный файл обратно и добавляет
в результат tool строку `DocumentWikiWriteVerification`. Writer должен включать в summary
только подтвержденные записи.

`build_document_wiki_query_agent` собирает отдельного агента поиска. Он читает `wiki/index.md`, релевантные dimensions и source-файлы, затем отвечает с указанием источников.

## Поток Добавления Документа

```text
sources/doc_N.md уже создан
        ↓
IngestSupervisor
        ↓
source-profiler
        ↓
dimensions-reader
        ↓
wiki-writer
        ↓
summary обновления wiki
```

`source-profiler` не знает текущую wiki и не утверждает, какие dimensions уже существуют. Он предлагает только кандидатные смысловые разрезы по содержанию source-файла.

Решение обновить существующий dimension или создать новый принимает `wiki-writer` на основе `source_profile` и `current_wiki_map`.

После запуска `run_ingest.py` дополнительно печатается фактический список файлов в `wiki/`.
Этот список полезен для проверки, что summary агента совпадает с реальной файловой системой.

## Поток Поиска

```text
вопрос пользователя
        ↓
wiki/index.md
        ↓
релевантные wiki/dimensions/*.md
        ↓
релевантные sources/*.md
        ↓
ответ с указанием source-файлов
```

Wiki используется как карта. Sources остаются источником истины.

## Ограничения V1

В первой версии не используются:

```text
vector search
RAG
BM25
reranker
локальные поисковые индексы
metadata.json
parsed/
audit/
review_queue/
contradictions.md
.tmp-файлы
память прошлых ответов
```

## Проверка Без Модели

Синтаксис Python-файлов можно проверить без API-ключей:

```powershell
$files = @()
$files += Get-ChildItem -LiteralPath '.\document_wiki' -Filter '*.py' | ForEach-Object { $_.FullName }
$files += Get-ChildItem -LiteralPath '.\document_wiki\prompts' -Filter '*.py' | ForEach-Object { $_.FullName }
$files += Get-ChildItem -LiteralPath '.\document_wiki\subagents' -Filter '*.py' | ForEach-Object { $_.FullName }
python -m py_compile @files
```
