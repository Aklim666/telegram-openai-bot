# Telegram-бот «Генератор отмазок» на OpenAI

Учебный/пет-проект: Telegram-бот на Python, который генерирует «отмазку» в выбранном стиле и под конкретного получателя с помощью OpenAI Assistants API.

## Как работает

Бот ведёт пошаговый диалог на основе ConversationHandler: тема (от чего отмазаться), стиль (пикми, бабушка, учёный, бизнес-коуч и др.) и получатель. По этим параметрам формирует запрос к ассистенту OpenAI, возвращает готовый текст и позволяет его доработать.

## Стек

- Python
- python-telegram-bot (Telegram Bot API, ConversationHandler)
- OpenAI Assistants API (threads, runs, messages)
- python-dotenv (конфигурация через переменные окружения)

## Настройка и запуск

Установить зависимости: python-telegram-bot, openai, python-dotenv. Создать файл .env (в репозиторий не коммитится) с OPENAI_API_KEY, ASSISTANT_ID, TELEGRAM_TOKEN. Запуск: python main_open_ai.py

## Структура

- main_open_ai.py — логика бота: диалог, состояния, интеграция с OpenAI.
- src.py — загрузка конфигурации из переменных окружения.

## Автор

Милана Солодовник
