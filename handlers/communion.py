# File: handlers/communion.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import os, asyncio
from datetime import datetime
from db import conn, cursor
from dotenv import load_dotenv
from utils.ethiopian_calendar import ethiopian_day_name, to_ethiopian, format_ethiopian_date

# to make users ask for their communion date and show their communion dates
async def handle_view_communion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Check if user is registered
    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        return await update.message.reply_text("🚫 አገልግልቱን ለማግኘት በቅድሚያ /register ላይ ገብተው ይመዝገቡ.")
    
    # inline keyboard with selection between viewing communion date and setting a new one
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
        #await query.message.reply_text("የቆረቡበት ቀን ይህን ይመልከቱ:")
        message = "📅የቆረቡበት ቀናት:\n\n"
        for i, comm in enumerate(communions, 1):
            comm_date = comm[1]
            eth_date = format_ethiopian_date(comm_date)
            day_name = ethiopian_day_name(comm_date)
            message += f"{i}. {eth_date} ({day_name})\n"

        await query.message.reply_text(message)
    

    elif data.startswith("set_communion_"):
        selected_date = data.split("_")[2]
        communion_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        context.user_data['comm_date'] = communion_date

        eth_date = format_ethiopian_date(communion_date)
        day_name = ethiopian_day_name(communion_date)