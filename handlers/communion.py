from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
import os
from datetime import datetime
from db import conn, cursor
from dotenv import load_dotenv
from utils.ethiopian_calendar import ethiopian_day_name, to_ethiopian, format_ethiopian_date, ethiopian_to_gregorian

SET_COMMUNION_DATE, CONFIRM_COMMUNION = range(2)


async def handle_view_communion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        return await update.message.reply_text("🚫 አገልግልቱን ለማግኘት በቅድሚያ /register ላይ ገብተው ይመዝገቡ.")
    
    keyboard = [
        [InlineKeyboardButton("የቆረቡባቸውን ቀናት ይመልከቱ", callback_data='view_communion_')],
        [InlineKeyboardButton("አዲስ ቀን ያስገቡ", callback_data='set_communion_')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "እባኮትን የሚፈልጉትን ይምረጡ:",
        reply_markup=reply_markup
    )

async def handle_communion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
    user = cursor.fetchone()

    if data.startswith("view_communion_"):
        cursor.execute("""
            SELECT id, comm_date FROM communion 
            WHERE user_id = %s AND status = 'የተጠናቀቀ'
            ORDER BY comm_date ASC
        """, (user[0],))
        communions = cursor.fetchall()
        
        if not communions:
            return await query.message.reply_text("📭 ምንም የቆረቡበት ቀን የለም.")
        
        message = "📅የቆረቡበት ቀናት:\n\n"
        for i, comm in enumerate(communions, 1):
            comm_date = comm[1]
            eth_date = format_ethiopian_date(comm_date)
            day_name = ethiopian_day_name(comm_date)
            message += f"{i}. {eth_date} ({day_name})\n"

        await query.message.reply_text(message)

    elif data.startswith("set_communion_"):
        await query.message.reply_text(
            "📅 እባክዎን የቆረቡበትን ቀን በዓመት-ወር-ቀን (ዓመት-ወር-ቀን) መልክ ያስገቡ:",
            reply_markup=ReplyKeyboardRemove()
        )
        return SET_COMMUNION_DATE

async def receive_communion_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    try:
        user_date = ethiopian_to_gregorian(user_input)
    except Exception:
        await update.message.reply_text(
        "❌ ትክክለኛ የኢትዮጵያ ቀን አላስገቡም። እባኮትን በ ዓመት-ወር-ቀን (2017-08-10) መልክ ያስገቡ።"
        )
        return SET_COMMUNION_DATE
    
    if user_date > datetime.now().date():
        await update.message.reply_text(
        "🚫 ወደፊት ያለ ቀን ማስገባት አይቻልም። እባኮትን የዛሬ ወይም ያለፈ ቀን ያስገቡ።"
        )
        return SET_COMMUNION_DATE
        
    context.user_data["comm_date"] = user_date
    eth_date = format_ethiopian_date(user_date)
    day_name = ethiopian_day_name(user_date)

    keyboard = [
        [InlineKeyboardButton("✅ አዎ", callback_data="confirm_communion_yes")],
        [InlineKeyboardButton("❌ አይ", callback_data="confirm_communion_no")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ ያስገቡት ቀን: {eth_date} ({day_name})\n\nይህን እንደ የቆረቡበት ቀን ማረጋገጥ ይፈልጋሉ?",
        reply_markup=reply_markup
    )
    return CONFIRM_COMMUNION

async def confirm_communion_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    confirmation = query.data
    user_id = query.from_user.id

    if confirmation == "confirm_communion_yes":
        cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
        user = cursor.fetchone()
        if not user:
            return await query.edit_message_text("🚫 እባኮትን መጀመሪያ /register በማለት ይመዝገቡ።")

        comm_date = context.user_data["comm_date"]
        
         # 🚨 Check if date already exists
        cursor.execute("""
            SELECT id FROM communion 
            WHERE user_id = %s AND comm_date = %s
        """, (user[0], comm_date))
        exists = cursor.fetchone()

        if exists:
            await update.callback_query.edit_message_text("⚠️ ያስገቡት ቀን አስቀድሞ ተመዝግቧል። እባክዎን በተለየ ቀን ይሞክሩ።")
            return ConversationHandler.END
            
        cursor.execute("""
            INSERT INTO communion (user_id, comm_date, status)
            VALUES (%s, %s, %s)
        """, (user[0], comm_date, 'በመጠበቅ'))
        conn.commit()

        await query.edit_message_text("✅ የቆረቡበት ቀን በትክክል ተመዝግቧል። ")
        return ConversationHandler.END

    else:
        await query.edit_message_text("❌ አቋርጠው ወተዋል ድጋሚ ለመጀመር /communion ይጫኑ።")
        return ConversationHandler.END

communion_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(handle_communion_callback, pattern='^set_communion_')],
    states={
        SET_COMMUNION_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_communion_date)],
        CONFIRM_COMMUNION: [CallbackQueryHandler(confirm_communion_date, pattern="^confirm_communion_")],
    },
    fallbacks=[],
)
