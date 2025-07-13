from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import logging, uuid
from db import conn, cursor

from warnings import filterwarnings
from telegram.warnings import PTBUserWarning

filterwarnings(action="ignore", message=r".*CallbackQueryHandler", category=PTBUserWarning)

logger = logging.getLogger("bot_logger")

if not logger.hasHandlers():
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter('%(levelname)s - %(message)s')
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)

# States for the conversation
SELECT_ACTION, ASK_QUESTION, EDIT_QUESTION = range(3)

async def handle_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info(f"Handling /questions for telegram_id: {telegram_id}")

    try:
        cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
        user = cursor.fetchone()
        if not user:
            logger.info(f"User {telegram_id} not registered")
            await update.message.reply_text(
                "እባክዎ መጀመሪያ መመዝገብ አለብዎ። ይመዝገቡ፡ /register"
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Database error in handle_questions: {e}")
        await update.message.reply_text(
            "ውስጣዊ ስህተት ተከስቷል። እባክዎ ቆይተው ይሞክሩ።"
        )
        return ConversationHandler.END

    try:
        cursor.execute(
            "SELECT id, question FROM questions WHERE user_id = %s AND status = 'በመጠበቅ'",
            (user,)
        )
        pending_questions = cursor.fetchall()
        logger.info(f"Found {len(pending_questions)} pending questions for user {telegram_id}")
    except Exception as e:
        logger.error(f"Database error fetching questions: {e}")
        await update.message.reply_text(
            "ጥያቄዎችን መጫን አልተቻለም። እባክዎ ቆይተው ይሞክሩ።"
        )
        return ConversationHandler.END

    if pending_questions:
        keyboard = [
            [InlineKeyboardButton(f"ጥያቄ {i+1}: {q[1][:30]}...", callback_data=f"edit_{q[0]}")]
            for i, q in enumerate(pending_questions)
        ]
        keyboard.append([InlineKeyboardButton("አዲስ ጥያቄ", callback_data="new_question")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "ያሉት ጥያቄዎች፡\nለመቀየር ወይም አዲስ ጥያቄ ለመጠየቅ ከታች ይምረጡ። ለማቋረጥ /cancel",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "ምንም ጥያቄዎች የሉዎትም። አዲስ ጥያቄ ያስገቡ። ለማቋረጥ /cancel"
        )
        return ASK_QUESTION

    return SELECT_ACTION

async def handle_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"Callback query received: {data}")

    if data == "new_question":
        await query.message.reply_text(
            "እባክዎ አዲስ ጥያቄዎን ያስገቡ። ለማቋረጥ /cancel"
        )
        return ASK_QUESTION
    elif data.startswith("edit_"):
        question_id = data.split("_")[1]
        try:
            cursor.execute(
                "SELECT question FROM questions WHERE id = %s AND status = 'በመጠበቅ'",
                (question_id,)
            )
            question = cursor.fetchone()
            if question:
                context.user_data["editing_question_id"] = question_id
                await query.message.reply_text(
                    f"የአሁኑ ጥያቄ: {question[0]}\nአዲሱን ጥያቄ ያስገቡ። ለማቋረጥ /cancel"
                )
                return EDIT_QUESTION
            else:
                await query.message.reply_text(
                    "ይህ ጥያቄ መቀየር አይችልም። እባክዎ ሌላ ይምረጡ ወዯም /questions ይጠቀሙ።"
                )
                return ConversationHandler.END
        except Exception as e:
            logger.error(f"Database error in handle_action_callback: {e}")
            await query.message.reply_text(
                "ጥያቄን መጫን አልተቻለም። እባክዎ ቆይተው ይሞክሩ።"
            )
            return ConversationHandler.END

async def handle_question_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    question = update.message.text.strip()
    logger.info(f"New question submitted by {telegram_id}: {question[:30]}...")

    que_id = str(uuid.uuid4())
    #select user id from users table
    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cursor.fetchone()
    if not user:
        logger.info(f"User {telegram_id} not registered")
        await update.message.reply_text(
            "እባክዎ መጀመሪያ መመዝገብ አለብዎ። ይመዝገቡ፡ /register"
        )
        return ConversationHandler.END
    
    if not question:
        await update.message.reply_text(
            "ጥያቄዎ ባዶ መሆን አይችልም። እባክዎ ጥያቄዎን እንደገና ያስገቡ።"
        )
        return ASK_QUESTION

    try:
        cursor.execute(
            "INSERT INTO questions (id, user_id, question, status) VALUES (%s, %s, %s, 'በመጠበቅ')",
            (que_id, user, question),
        )
        conn.commit()
        await update.message.reply_text(
            "ጥያቄዎ ተመዝግቧል!"
        )
    except Exception as e:
        logger.error(f"Database error storing question: {e}")
        await update.message.reply_text(
            "ጥያቄዎን መመዝገብ አልተቻለም። እባክዎ ቆይተው ይሞክሩ።"
        )
    return ConversationHandler.END

async def handle_question_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question_id = context.user_data.get("editing_question_id")
    new_question = update.message.text.strip()
    logger.info(f"Editing question {question_id} with new text: {new_question[:30]}...")

    if not new_question:
        await update.message.reply_text(
            "ጥያቄዎ ባዶ መሆን አይችልም። እባክዎ ጥያቄዎን እንደገና ያስገቡ።"
        )
        return EDIT_QUESTION

    try:
        cursor.execute(
            "UPDATE questions SET question = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s AND status = 'በመጠበቅ'",
            (new_question, question_id)
        )
        conn.commit()
        if cursor.rowcount > 0:
            await update.message.reply_text(
                "ጥያቄዎ ተቀይሯል!።"
            )
        else:
            await update.message.reply_text(
                "ይህ ጥያቄ መቀየር አይችልም። እባክዎ ሌላ ይምረጡ ወይም /questions ይጠቀሙ።"
            )
    except Exception as e:
        logger.error(f"Database error updating question: {e}")
        await update.message.reply_text(
            "ጥያቄን መቀየር አልተቻለም። እባክዎ ቆይተው ይሞክሩ።"
        )
    context.user_data.pop("editing_question_id", None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("editing_question_id", None)
    logger.info("Conversation cancelled")
    await update.message.reply_text(
        "ጥያቄ መጠየቅ ወይም መቀየር አቋርጠው ወተዋል። እንደገና ለመጀመር /questions ይጠቀሙ።"
    )
    return ConversationHandler.END

# Conversation handler for questions
questions_conversation = ConversationHandler(
    entry_points=[CommandHandler("questions", handle_questions)],
    states={
        SELECT_ACTION: [
            CallbackQueryHandler(handle_action_callback, pattern=r"^(new_question|edit_[a-f0-9-]+)$")
        ],
        ASK_QUESTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question_submission)
        ],
        EDIT_QUESTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question_edit)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_message=False
)