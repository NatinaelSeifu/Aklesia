
import os
from dotenv import load_dotenv
from telegram import Update, BotCommand,BotCommandScopeChat
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters,ConversationHandler
)
import asyncio

from handlers import register, book, admin, questions, communion, scheduler

load_dotenv()

ADMIN_IDS = os.getenv("ADMIN_TELEGRAM_ID", "")
ADMIN_ID = [int(id.strip()) for id in ADMIN_IDS.split(",") if id.strip().isdigit()]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 እንኳን ወደ የቀሲስ ጥላሁን ጉደታ የንስሐ ልጆች አቅሌስያ መጡ!\nእባክዎ ለመጀመር /register የሚለውን በመጫን አካውንት ይክፈቱ." #or /book to schedule an appointment.
    )

async def set_commands(app):
    user_commands = [
        BotCommand("register", "ይመዘገቡ"),
        BotCommand("book", "ቀጠሮ ያስይዙ"),
        BotCommand("profile", "መገለጫዎን ይመልከቱ"),
        BotCommand("mybooking", "ያሎትን ቀጠሮዎች ይመልከቱ"),
        BotCommand("communion", "ቁርባን"),
        BotCommand("questions", "ጥያቄ ወይም አስተያየት ያቅርቡ"),
    ]

    # Set for default users
    await app.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Set for each admin
    if ADMIN_ID:
        for admin_id in ADMIN_ID:
            await app.bot.set_my_commands(
                commands=[
                    BotCommand("users", "የክርስትና ልጆች ዝርዝር ይመልከቱ"),
                    BotCommand("appointments", "ቀጠሮዎች ይመልከቱ"),
                    BotCommand("addavailability", "የቀን ዝርዝር ያክሉ"),
                    BotCommand("availability", "የቀን ዝርዝር ይሰርዙ"),  
                    BotCommand("question", "ጥያቄዎች ይመልከቱ"),
                    BotCommand("communions", "ቁርባን"),
                ],
                scope=BotCommandScopeChat(chat_id=admin_id)
            )
    print("✅ Commands set successfully.")
    
async def post_init(app):
    await set_commands(app)
    scheduler.start_scheduler()

def main():
    
    app = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    
    # Update the fallbacks to include the new cancel command
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("addavailability", admin.handle_add_avail_command)],
        states={
            "awaiting_date": [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.handle_add_avail_step)],
            "awaiting_slots": [MessageHandler(filters.TEXT & ~filters.COMMAND, admin.handle_add_avail_step)],
        },
        fallbacks=[
            # CommandHandler("cancelcreation", admin.cancel_availability_creation),
            # CommandHandler("availability", admin.handle_cancel_avail_command)
        ],
    ))
    
    
    app.add_handler(questions.questions_conversation)
    app.add_handler(communion.communion_conversation)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register.handle_register))
    app.add_handler(CommandHandler("profile", register.handle_profile))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register.handle_register_convo))
    app.add_handler(CallbackQueryHandler(register.handle_register_convo, pattern="^(ያገባ|ያላገባ)$"))
    app.add_handler(CallbackQueryHandler(register.handle_edit_profile_callback,pattern="^(edit_name|edit_phone|edit_email|edit_joined_on|edit_children|married|single|delete_profile|confirm_delete_yes|confirm_delete_no)$"))
    app.add_handler(CommandHandler("book", book.handle_booking))
    app.add_handler(CallbackQueryHandler(book.handle_booking_callback, pattern=r"^book_|^confirm_booking$|^cancel_booking$"))    
    app.add_handler(CommandHandler("mybookings", book.handle_mybookings))
    app.add_handler(CallbackQueryHandler(book.handle_mybookings_callback,pattern=r"^change_[a-f0-9-]+$|^abort_cancel_|^confirm_cancell_[a-f0-9-]+$|^cancel_[a-f0-9-]+$|^confirm_change_[a-f0-9-]+_\d{4}-\d{2}-\d{2}$"))
    app.add_handler(CallbackQueryHandler(admin.handle_admin_callback, pattern="^(view_schedule|add_day)"))
    app.add_handler(CommandHandler("appointments", admin.handle_admin_appointments))
    app.add_handler(CallbackQueryHandler(admin.handle_admin_callback, pattern="^(admin_complete_|admin_cancel_)"))
    app.add_handler(CommandHandler("users", admin.handle_admin_users))
    app.add_handler(CommandHandler("availability", admin.handle_cancel_avail_command))
    app.add_handler(CallbackQueryHandler(admin.handle_cancel_avail_callback, pattern=r"^cancel_avail_\d{4}-\d{2}-\d{2}$|^confirm_cancel_\d{4}-\d{2}-\d{2}$|^avail_cancel_back$|^cancel_avail_menu$"))
    app.add_handler(CommandHandler("question", admin.handle_view_questions))
    app.add_handler(CallbackQueryHandler(admin.handle_admin_question_callback, pattern=r"^question_cancel_[a-f0-9-]+|^question_complete_[a-f0-9-]+"))
    app.add_handler(CommandHandler("communion", communion.handle_view_communion))
    app.add_handler(CallbackQueryHandler(communion.handle_communion_callback, pattern=r"^view_communion_|^set_communion_"))
    app.add_handler(CommandHandler("communions", admin.handle_admin_communion))
    app.add_handler(CallbackQueryHandler(admin.handle_admin_communion_callback, pattern=r"^communion_complete_[a-f0-9-]+|^communion_cancel_[a-f0-9-]+"))

    # Set commands once app is running
    app.post_init = post_init

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
