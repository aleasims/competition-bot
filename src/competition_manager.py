import io
import logging
from enum import Enum, auto
from queue import Queue
from typing import Dict, Union

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, ConversationHandler

from .competition import Competition
from .competitor import Competitor


class CompetitionManager:
    CONVERSATION_TIMEOUT = 600  # 10 min

    class State(Enum):
        REGISTER = auto()
        DATA_LOAD = auto()
        COMPETITION_CLAIM = auto()

    def __init__(self):
        self.competitors: Dict[int, Competitor] = {}
        self.queue: Queue = Queue(maxsize=1)

    def name_exists(self, name: str) -> bool:
        names = set(comp.name for comp in self.competitors.values())
        return name in names

    async def start(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
        chat = update.message.chat_id
        logging.info(f"Started conversation with _[{chat}]")

        await update.message.reply_text("Hello! Please, type in your name:")
        return self.State.REGISTER

    async def register(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> Union[int, None]:
        name = update.message.text
        if self.name_exists(name):
            await update.message.reply_text("Sorry, this name is already taken."
                                            " Try another one:")
            return

        chat = update.message.chat_id
        competitor = Competitor(chat, name, None)
        self.competitors[chat] = competitor
        logging.info(f"Registered competitor {competitor}")

        reply = f"Registered you as `{name}`. Now send your data (.txt file):"
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        return self.State.DATA_LOAD

    async def load_data(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
        competitor = self.competitors[update.message.chat_id]

        file = await update.message.document.get_file()
        buf = io.BytesIO()
        await file.download(out=buf)
        buf.seek(0)
        data = buf.read()

        if not file.file_size == len(data):
            logging.error(f"Competitor {competitor} loaded {file.file_size} bytes"
                        f", but could download only {len(data)} bytes")
        else:
            logging.info(f"Competitor {competitor} loaded {len(data)} bytes")

        self.competitors[update.message.chat_id].data = data

        await update.message.reply_text("Got your data. To reload data use "
                                        "/reload command. Now you can take part"
                                        " in competition using /compete command."
                                        " Or you can compete with yourself using"
                                        " /single command. Good luck!")
        return self.State.COMPETITION_CLAIM

    async def reload_data(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
        competitor = self.competitors[update.message.chat_id]
        logging.info(f"Competitor {competitor} reloading data")

        if not self.queue.empty():
            queued = self.queue.get()
            if queued and queued.chat == competitor.chat:
                logging.info(f"Competitor {competitor} moved out from queue")
            else:
                self.queue.put(queued)

        await update.message.reply_text("Send your data:")
        return self.State.DATA_LOAD

    async def compete(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        comp1 = self.competitors[update.message.chat_id]
        if self.queue.empty():
            self.queue.put(comp1)
            logging.info(f"Competitor {comp1} queued to competititon")
            await update.message.reply_text("You were queued into competition."
                                            " Waiting for the opponent...")
            return

        comp2 = self.queue.get()
        if comp1.chat == comp2.chat:
            self.queue.put(comp1)
            await update.message.reply_text("You are already in the queue "
                                            "waiting for the opponent.")
            return

        logging.info(f"Starting competition {comp1} vs {comp2}...")
        result = Competition(comp1, comp2).run()
        logging.info(f"Competition {comp1} vs {comp2}: {result}")

        reply = f"You took part in a competition against `{comp2.name}`. Result: `{result}`."
        await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        reply = f"You took part in a competition against `{comp1.name}`. Result: `{result}`."
        await context.bot.send_message(comp2.chat, reply, parse_mode=ParseMode.MARKDOWN)

    async def single(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        competitor = self.competitors[update.message.chat_id]
        logging.info(f"Starting {competitor} single competition...")
        result = Competition(competitor, competitor).run()
        logging.info(f"{competitor} single competition ended. Result: {result}")

        await update.message.reply_text(f"You completed a single-mode "
                                        f"competition.Result: {result}")

    async def stop(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
        chat = update.message.chat_id
        competitor = self.competitors.pop(chat, None)
        name = competitor.name if competitor else '_'
        logging.info(f"End conversation with {name}[{chat}]")

        await update.message.reply_text("Good bye!")
        return ConversationHandler.END

    async def timeout(self, update: Update, _: ContextTypes.DEFAULT_TYPE) -> int:
        chat = update.message.chat_id
        competitor = self.competitors.pop(chat, None)
        name = competitor.name if competitor else '_'
        logging.info(f"End conversation with {name}[{chat}] due to timeout")

        await update.message.reply_text("Your session has expired. Good bye!")
        return ConversationHandler.END
