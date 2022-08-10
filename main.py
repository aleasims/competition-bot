import io
import logging
import random
from enum import Enum, auto
from queue import Queue
from typing import Dict, TypeAlias

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          ConversationHandler, MessageHandler, filters)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


class State(Enum):
    REGISTER = auto()
    DATA_LOAD = auto()
    COMPETITION_CLAIM = auto()


Chat: TypeAlias = int


class Competitor:
    __slots__ = ('chat', 'name', 'data')

    def __init__(self, chat: Chat, name: str, data: bytes | None):
        self.chat = chat
        self.name = name
        self.data = data

    def __str__(self):
        return f"{self.name}[{self.chat}]"


# All registered competitors
competitors: Dict[Chat, Competitor] = {}

# Queue of max 1 competitor, waiting to run competition.
queue = Queue(maxsize=1)


async def start(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Hello! Please, type in your name:")
    return State.REGISTER


async def register(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    chat = update.message.chat_id
    competitors[chat] = Competitor(chat, name, None)

    reply = f"Registered you as `{name}`. Now send your data (.txt file):"
    await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
    return State.DATA_LOAD


async def get_data(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    file = await update.message.document.get_file()
    buf = io.BytesIO()
    await file.download(out=buf)
    buf.seek(0)
    data = buf.read()

    chat = update.message.chat_id
    competitor = competitors[chat]

    if not file.file_size == len(data):
        logging.error(f"Competitor `{competitor}` loaded {file.file_size} bytes"
                      f", but could download only {len(data)} bytes")
    else:
        logging.info(f"Competitor `{competitor}` loaded {len(data)} bytes")

    competitors[chat].data = data

    await update.message.reply_text("Got your data. Now you can take part in "
                                    "competition using /compete command. Or"
                                    "you can compete with yourself using "
                                    "/single command. Good luck!")
    return State.COMPETITION_CLAIM


async def compete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.message.chat_id
    comp1 = competitors[chat]
    global queue
    if queue.empty():
        queue.put(comp1)
        await update.message.reply_text("You were queued into competition.")
    else:
        comp2 = queue.get()
        if comp1.chat == comp2.chat:
            queue.put(comp1)
            await update.message.reply_text("You are already in the queue "
                                            "waiting for the opponent.")
        else:
            winner = run_competition(comp1, comp2)
            reply = f"You took part in a competition against `{comp2.name}`. Winner: `{winner.name}`."
            await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
            reply = f"You took part in a competition against `{comp1.name}`. Winner: `{winner.name}`."
            await context.bot.send_message(comp2.chat, reply, parse_mode=ParseMode.MARKDOWN)


async def single(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.message.chat_id
    competitor = competitors[chat]
    run_competition(competitor, competitor)
    await update.message.reply_text("You completed a single-mode competition.")


async def stop(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    chat = update.message.chat_id
    competitors.pop(chat, None)
    await update.message.reply_text("Good bye!")
    return ConversationHandler.END


async def timeout(update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
    chat = update.message.chat_id
    competitors.pop(chat, None)
    await update.message.reply_text("Your session has expired. Good bye!")
    return ConversationHandler.END


def run_competition(competitor_1: Competitor, competitor_2: Competitor) -> Competitor:
    logging.info(f"Running competition between {competitor_1} and {competitor_2}")
    return random.choice([competitor_1, competitor_2])


if __name__ == '__main__':
    CONVERSATION_TIMEOUT = 600  # 10 min

    with open("TOKEN") as f:
        TOKEN = f.read()

    app = Application.builder().concurrent_updates(False).token(TOKEN).build()

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            State.REGISTER: [
                MessageHandler(filters.TEXT, register),
            ],
            State.DATA_LOAD: [
                MessageHandler(filters.Document.ALL, get_data),
            ],
            State.COMPETITION_CLAIM: [
                CommandHandler('compete', compete),
                CommandHandler('single', single),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, timeout),
            ],
        },
        fallbacks=[CommandHandler('stop', stop)],
        conversation_timeout=CONVERSATION_TIMEOUT,
    ))

    app.run_polling()
