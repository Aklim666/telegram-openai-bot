import logging
from openai import OpenAI
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

from src import OPENAI_API_KEY, ASSISTANT_ID, TELEGRAM_TOKEN

client = OpenAI(api_key=OPENAI_API_KEY)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния диалога
THEME, STYLE, RECIPIENT, FEEDBACK = range(4)

# Хранилище потоков
user_threads = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Не хочешь — но надо ответить?\n"
        "Сначала скажи: от чего отмазываешься?"
    )
    return THEME


async def get_theme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["theme"] = update.message.text
    await update.message.reply_text("Окей. А в каком стиле хочешь отмазку?\n"
                                    "(Можешь выбрать любой, но вот несколько примеров: пикми, бабушка, учёный, бизнес-коуч)")
    return STYLE


async def get_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["style"] = update.message.text
    await update.message.reply_text("Понял. Кто же получатель сообщения?\n")
    return RECIPIENT


async def get_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["recipient"] = update.message.text

    # Формируем полный запрос для ассистента
    user_prompt = (
        f"Тема: {context.user_data['theme']}\n"
        f"Стиль: {context.user_data['style']}\n"
        f"Аудитория: {context.user_data['recipient']}"
    )

    user_id = update.message.from_user.id
    status_msg = await update.message.reply_text("Капец как сильно думаю... 🤯")

    try:
        # Получаем или создаём thread
        if user_id in user_threads:
            thread_id = user_threads[user_id]
        else:
            thread = client.beta.threads.create()
            thread_id = thread.id
            user_threads[user_id] = thread_id

        # Добавляем сообщение
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_prompt
        )

        # Запускаем ассистента
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Ждём завершения
        while run.status in ("queued", "in_progress"):
            import time
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

        # Получаем ответ
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        response_texts = [
            msg.content[0].text.value
            for msg in messages.data
            if msg.role == "assistant"
        ]

        response = response_texts[0] if response_texts else "Этот... как его... ну короче, держись. 😅"

    except Exception as e:
        logger.error(f"Ошибка OpenAI: {e}")
        response = "Что-то пошло не так. Попробуй через минуту."

    # Отправляем результат
    await status_msg.edit_text(response)

    # Спрашиваем, всё ли ок
    await update.message.reply_text(
        "Всё устроило? Если хочешь переделать — просто напиши, что изменить.\n"
        "Если готов(а) к новой отмазке — жми /start"
    )
    return FEEDBACK


async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Пользователь прислал уточнение (например: "сделай в стиле Пикми")
    feedback = update.message.text
    theme = context.user_data.get("theme", "")
    style = context.user_data.get("style", "")
    recipient = context.user_data.get("recipient", "")

    # Можно просто передать уточнение как новый запрос, но лучше — обновить контекст
    # Для простоты: отправим уточнение как дополнение к исходному запросу
    refined_prompt = (
        f"Тема: {theme}\n"
        f"Стиль: {style}\n"
        f"Аудитория: {recipient}\n"
        f"Уточнение: {feedback}"
    )

    user_id = update.message.from_user.id
    status_msg = await update.message.reply_text("Ща переделаю... 🛠️")

    try:
        thread_id = user_threads.get(user_id)
        if not thread_id:
            thread = client.beta.threads.create()
            thread_id = thread.id
            user_threads[user_id] = thread_id

        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=refined_prompt
        )

        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        while run.status in ("queued", "in_progress"):
            import time
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

        messages = client.beta.threads.messages.list(thread_id=thread_id)
        response_texts = [
            msg.content[0].text.value
            for msg in messages.data
            if msg.role == "assistant"
        ]
        response = response_texts[0] if response_texts else "Ну вот... опять что-то сдвинулось не туда. 😬"

    except Exception as e:
        logger.error(f"Ошибка при повторной генерации: {e}")
        response = "Не вышло переделать. Попробуй с /start."

    await status_msg.edit_text(response)
    await update.message.reply_text("Если нужно ещё — жми /start")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ладно, если передумаешь — /start")
    return ConversationHandler.END


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Диалог с состояниями
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            THEME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_theme)],
            STYLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_style)],
            RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_recipient)],
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_feedback)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)

    print("✅ Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()