"""Инициализация модели LangChain для LLM wiki.

Содержит:
- model: объект chat-модели LangChain.

Функции:
- нет.
"""

from os import getenv

from langchain.chat_models import init_chat_model


model = init_chat_model(getenv("LLM_MODEL", "openai:gpt-5-mini"))
