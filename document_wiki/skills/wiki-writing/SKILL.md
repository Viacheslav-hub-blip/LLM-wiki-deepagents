---
name: wiki-writing
description: Обновление wiki/index.md и wiki/dimensions/*.md после анализа нового source-документа.
---

# Wiki Writing

## Назначение

Используй этот skill, когда нужно встроить новый source-документ в wiki-карту знаний.

WikiWriterSubagent получает:

```text
source_path
source_profile
current_wiki_map
```

Только WikiWriterSubagent может редактировать `wiki/` в ingest-процессе.

## Основной принцип

```text
Wiki — карта знаний.
Sources — источник истины.
```

Wiki помогает находить документы, но не заменяет исходные source-файлы. Все значимые заметки в wiki должны ссылаться на source-файлы.

Wiki должна помогать найти документ даже по короткому запросу: одному слову, имени,
аббревиатуре, названию технологии, сервису, метрике, проблеме или фразе из середины документа.

## Правила обновления

1. Всегда добавляй новый source в `wiki/index.md`.
2. Обновляй существующие dimensions, если они покрывают смысл нового документа.
3. Создавай новый dimension только при реальной необходимости.
4. Не создавай дублирующие dimensions.
5. Не копируй большие фрагменты source-документа в wiki.
6. Не редактируй `sources/`.
7. Держи `wiki/index.md` навигационной картой, но добавляй достаточно search terms.
8. Держи dimension-файлы содержательными и полезными для маршрутизации поиска.
9. Считай файл реально созданным или обновленным только после подтверждения `DocumentWikiWriteVerification` в результате `write_file` или `edit_file`.
10. Для каждого source добавляй в wiki ключевые термины, сущности, потенциальные вопросы и краткие факты.

## Когда можно создать новый dimension

Новый dimension можно создать, если одновременно выполняются условия:

1. Новый документ содержит устойчивый смысловой разрез, который может повториться в других документах.
2. Текущие dimensions не покрывают этот смысл.
3. Новый файл не является страницей под один конкретный документ.
4. Название dimension широкое, понятное и переиспользуемое.

Хорошие примеры:

```text
people.md
report-types.md
metrics.md
products.md
customer-problems.md
control-processes.md
fraud-rules.md
departments.md
data-sources.md
```

Плохие примеры:

```text
doc-001-details.md
june-2026-csi-problems.md
ivanov-report-details.md
card-complaints-from-doc-17.md
metrics-2.md
```

## Формат `wiki/index.md`

`wiki/index.md` должен содержать:

```markdown
# Wiki Index

## Sources
- [doc_001](../sources/doc_001.md) — краткое описание; search terms: CSI, NPS, карты, переводы, push-уведомления.

## Dimensions
- [metrics](dimensions/metrics.md) — метрики, показатели, KPI.

## Navigation notes
Для вопросов про метрики использовать `metrics.md`.
```

Index не должен превращаться в большой отчет, но для каждого source желательно хранить:

- краткое описание;
- 8-20 search terms;
- 3-8 routing hints или потенциальных пользовательских вопросов;
- ссылку на source-файл.

## Формат dimension-файла

```markdown
# <Dimension title>

## Purpose
Для каких вопросов использовать этот разрез.

## Key topics
- Тема или сущность — краткое описание; sources: `sources/doc_N.md`.

## Search terms
- термин; синоним; аббревиатура; английское название; близкая формулировка.

## Facts and signals
- Конкретный факт или утверждение, полезное для маршрутизации; source: `sources/doc_N.md`.

## Potential questions
- Вопрос, который пользователь может задать.

## Sources
- `sources/doc_N.md` — почему источник релевантен.
```

Для одного содержательного документа допустимо добавить 5-15 пунктов в релевантный
dimension. Не копируй большие абзацы source-документа, но сохраняй важные слова и термины.

## Формат summary

```markdown
# Wiki update summary

## Updated files
- wiki/index.md
- wiki/dimensions/metrics.md

## Created files
- wiki/dimensions/customer-problems.md

## Not changed
- wiki/dimensions/people.md — причина.

## How the source was integrated
...

## Notes
...

## Write verification
- wiki/index.md — подтверждено: DocumentWikiWriteVerification ...
```

В разделы `Updated files` и `Created files` включай только файлы, для которых был
успешный `write_file` или `edit_file` и получено подтверждение `DocumentWikiWriteVerification`.
Если подтверждения нет, укажи это в `Write verification`, но не называй файл созданным
или обновленным.

## Запрещено

- Изменять любые файлы в `sources/`.
- Создавать `.tmp`-файлы.
- Создавать `metadata.json`.
- Создавать `parsed/`, `audit/`, `review_queue/`.
- Создавать `contradictions.md`.
- Использовать vector search, RAG, BM25, reranker или локальные индексы.
- Копировать большие фрагменты source-документа в wiki.
- Создавать дубли dimensions без причины.
- Создавать узкие страницы под один документ.
