import os
from dotenv import load_dotenv
from telegram import Update, BotCommand,BotCommandScopeChat
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters,ConversationHandler
)


from handlers import register, book,admin

load_dotenv()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 እንኳን ወደ የቀሲስ ጥላሁን ጉደታ የንስሐ ልጆች አቅሌስያ መጡ!\nእባክዎ ለመጀመር /register የሚለውን በመጫን አካውንት ይክፈቱ." #or /book to schedule an appointment.
    )

async def set_commands(app):
    commands = [
        BotCommand("start", "ቦቱን ያስጀምሩ"),
        BotCommand("register", "ይመዘገቡ"),
        BotCommand("book", "ቀጠሮ ያስይዙ"),
#        BotCommand("cancel", "Cancel your appointment"),
        BotCommand("profile", "መገለጫዎን ይመልከቱ"),
        BotCommand("mybookings", "ያሎትን ቀጠሮዎች ይመልከቱ"),
    ]

    # Only show /admin for the admin
    if os.getenv("ADMIN_TELEGRAM_ID"):
        await app.bot.set_my_commands(
            # if needed the user use commands + []
            commands = [
                BotCommand("appointments", "ቀጠሮዎች ይመልከቱ"),
                BotCommand("addavailability", "የቀን ዝርዝር ያክሉ"),
                BotCommand("availability", "የቀን ዝርዝር ይሰርዙ"),  

            ],
            scope=BotCommandScopeChat(chat_id=int(os.getenv("ADMIN_TELEGRAM_ID")))
        )

    
    await app.bot.set_my_commands(commands)  # For everyone else
    print("✅ Commands set successfully.")
    


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
            CommandHandler("cancelcreation", admin.cancel_availability_creation),
            CommandHandler("availability", admin.handle_cancel_avail_command)
        ],
    ))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register.handle_register))
    app.add_handler(CommandHandler("profile", register.handle_profile))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, register.handle_register_convo))
    app.add_handler(CallbackQueryHandler(register.handle_edit_profile_callback,pattern="^(edit_name|edit_phone|edit_email|edit_joined_on|delete_profile|confirm_delete_yes|confirm_delete_no)$"))
    app.add_handler(CommandHandler("book", book.handle_booking))
    app.add_handler(CallbackQueryHandler(book.handle_booking_callback, pattern=r"^book_|^confirm_booking$|^cancel_booking$"))    
    app.add_handler(CommandHandler("mybookings", book.handle_mybookings))
    app.add_handler(CallbackQueryHandler(book.handle_mybookings_callback, pattern=r"^change_\d+$|^abort_cancel_|^confirm_cancell_|^cancel_\d+$|^confirm_change_\d+_\d{4}-\d{2}-\d{2}$"))

    app.add_handler(CallbackQueryHandler(admin.handle_admin_callback, pattern="^(view_schedule|add_day)"))
    app.add_handler(CommandHandler("appointments", admin.handle_admin_appointments))
    app.add_handler(CallbackQueryHandler(admin.handle_admin_callback, pattern="^(admin_complete_|admin_cancel_)"))
    # Add these new handlers after your existing admin handlers:
    app.add_handler(CommandHandler("availability", admin.handle_cancel_avail_command))
    app.add_handler(CallbackQueryHandler(admin.handle_cancel_avail_callback, pattern=r"^cancel_avail_\d{4}-\d{2}-\d{2}$|^confirm_cancel_\d{4}-\d{2}-\d{2}$|^avail_cancel_back$|^cancel_avail_menu$"))
    # Set commands once app is running
    app.post_init = set_commands

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
