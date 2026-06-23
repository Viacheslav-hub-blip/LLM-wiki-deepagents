---
name: dimensions-reading
description: Чтение текущей wiki document_wiki и сжатие ее в компактную карту dimensions и source-ссылок.
---

# Dimensions Reading

## Назначение

Используй этот skill, когда нужно собрать compact wiki map перед обновлением wiki или поиском по базе документов.

DimensionsReaderSubagent читает текущую wiki, но не редактирует файлы и не принимает решение о создании новых dimensions.
Compact map должна сохранять не только названия dimensions, но и важные поисковые
термины, source-ссылки, краткое покрытие и возможные пересечения.

## Вход

Ожидаемая структура:

```text
wiki/index.md
wiki/dimensions/*.md
```

Wiki может быть пустой, если обрабатывается первый документ.

## Правила работы

1. Проверь наличие `wiki/index.md`.
2. Если `wiki/index.md` существует, прочитай его.
3. Найди dimension-файлы по маске `wiki/dimensions/*.md`.
4. Прочитай найденные dimension-файлы.
5. Верни markdown-карту текущей wiki: dimensions, source-ссылки, темы, термины и routing hints.
6. Не возвращай полный текст всех wiki-файлов.
7. Укажи, какие dimensions существуют и что они покрывают.
8. Укажи source-файлы, которые уже упоминаются в wiki.
9. Отметь возможные пересечения между dimensions, если они явно видны.
10. Сохрани в compact map ключевые search terms, по которым пользователь может искать документ.

## Формат ответа

Если wiki пустая:

```markdown
# Current wiki map

Wiki пока пустая.

## Existing dimensions
Не найдено.

## Sources in wiki
Не найдено.

## Notes
Нужно создать начальную wiki-структуру по содержанию первого source-документа.
```

Если wiki существует:

```markdown
# Current wiki map

## Existing dimensions
- `metrics.md` — кратко что покрывает.
- `products.md` — кратко что покрывает.

## Sources in wiki
- `sources/doc_001.md` — краткое описание.

## What each dimension covers
- `metrics.md`: метрики, KPI, показатели.

## Search terms already covered
- CSI, NPS, DeepFake, SIM-бокс, ГИС Антифрод, request_reason.

## Source routing hints
- `sources/doc_001.md`: использовать для вопросов про клиентские обращения, карты, CSI.

## Possible overlaps
- ...

## Navigation notes
- ...
```

## Запрещено

- Редактировать `wiki/`.
- Создавать новые dimensions.
- Изменять `sources/`.
- Возвращать полный текст всех wiki-файлов.
- Анализировать новый source-файл.
- Решать, какие файлы нужно обновить.
- Придумывать dimensions, которых нет в текущей wiki.

Не выбрасывай важные термины только потому, что они выглядят мелкими. Пользователь
может задать вопрос одним словом из середины документа.
