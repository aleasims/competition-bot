import logging

from telegram.ext import (Application, CommandHandler, ConversationHandler,
                          MessageHandler, filters)

from src.competition_manager import CompetitionManager

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if __name__ == '__main__':
    with open("TOKEN") as f:
        TOKEN = f.read().strip()

    app = Application.builder().concurrent_updates(False).token(TOKEN).build()

    manager = CompetitionManager()

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler('start', manager.start)],
        states={
            CompetitionManager.State.REGISTER: [
                MessageHandler(filters.TEXT & (~ filters.COMMAND), manager.register),
            ],
            CompetitionManager.State.DATA_LOAD: [
                MessageHandler(filters.Document.ALL, manager.load_data),
            ],
            CompetitionManager.State.COMPETITION_CLAIM: [
                CommandHandler('compete', manager.compete),
                CommandHandler('single', manager.single),
                CommandHandler('reload', manager.reload_data),
            ],
            ConversationHandler.TIMEOUT: [
                MessageHandler(filters.ALL, manager.timeout),
            ],
        },
        fallbacks=[CommandHandler('stop', manager.stop)],
        conversation_timeout=manager.CONVERSATION_TIMEOUT,
    ))

    app.run_polling()
