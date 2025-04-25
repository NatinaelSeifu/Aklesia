# handlers/admin.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import os, asyncio
from datetime import datetime
from db import conn, cursor
from dotenv import load_dotenv
from utils.ethiopian_calendar import to_ethiopian, ethiopian_day_name,ethiopian_to_gregorian
#from handlers.book import AMHARIC_DAYS

load_dotenv()

ADMIN_IDS = os.getenv("ADMIN_TELEGRAM_ID", "")
ADMIN_ID = [int(id.strip()) for id in ADMIN_IDS.split(",") if id.strip().isdigit()]

# 👥 Admin: View Appointments
async def handle_admin_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id

    if admin_id not in ADMIN_ID:
        return await update.message.reply_text("🚫 ይህን ለመጠቀም አልተፈቀደሎትም.")

    today = datetime.now().date()

    if context.args and context.args[0] == "all":
        cursor.execute("""
            SELECT a.id, u.name, a.appointment_date, a.status
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            ORDER BY a.appointment_date ASC
        """)
    elif context.args and context.args[0] == "today":
            cursor.execute("""
            SELECT a.id, u.name, a.appointment_date, a.status
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.appointment_date = %s AND a.status = 'በመጠበቅ'
            ORDER BY a.appointment_date ASC
        """, (today,))
    else:
        cursor.execute("""
            SELECT a.id, u.name, a.appointment_date, a.status
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.appointment_date >= %s AND a.status = 'በመጠበቅ'
            ORDER BY a.appointment_date ASC
        """, (today,))

    appointments = cursor.fetchall()

    if not appointments:
        return await update.message.reply_text("📭 ምንም ቀጠሮ የሎትም.")

    for appt_id, name, appt_date, status in appointments:
        keyboard = []
        if status == "በመጠበቅ":
            keyboard.append([
                InlineKeyboardButton("✅ ተካሂዷል", callback_data=f"admin_complete_{appt_id}"),
                InlineKeyboardButton("❌ ሰርዝ", callback_data=f"admin_cancel_{appt_id}")
            ])
        eth_date = to_ethiopian(appt_date)
        day_name = ethiopian_day_name(appt_date)
        
        await update.message.reply_text(
            f"👤 {name}\n"
            f"📅 {eth_date} {day_name}\n"
            f"📌 ሁኔታ: {status.capitalize()}",
            reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        )
    #     await update.message.reply_text(
    #     f"👤 {name}\n📅 {appt_date.strftime('%d/%m/%Y')} ({AMHARIC_DAYS[appt_date.weekday()]})\n📌 ሁኔታ: {status.capitalize()}",  # "Status" in Amharic
    #     reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    # )
        # await update.message.reply_text(
        #     f"👤 {name}\n📅 {appt_date.strftime('%A, %d %B %Y')}\n📌 Status: {status.capitalize()}",
        #     reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
        # )

# 🔄 Admin Callback Handler
async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    admin_id = query.from_user.id

    if admin_id not in ADMIN_ID:
        return await query.edit_message_text("🚫 ያልተፈቀደ.")

    if data.startswith("admin_complete_"):
        appointment_id = int(data.split("_")[2])
        cursor.execute("UPDATE appointments SET status = 'የተጠናቀቀ' WHERE id = %s", (appointment_id,))
        conn.commit()
        return await query.edit_message_text("✅ ቀጠሮው ተካሂዷል.")

    elif data.startswith("admin_cancel_"):
        appointment_id = int(data.split("_")[2])
        cursor.execute("UPDATE appointments SET status = 'የተሰረዘ' WHERE id = %s", (appointment_id,))
        conn.commit()
        # notify user
        cursor.execute("""
            SELECT u.telegram_id, a.appointment_date
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.id = %s
        """, (appointment_id,))
        result = cursor.fetchone()
        if result:
            telegram_id, appt_date = result
            message = (
                f"❌ የቀጠሮ ስረዛ ማስታውሻ\n\n"
                f"በ {to_ethiopian(appt_date)} የነበሮት ቀን ተሰርዟል.\n"
                f"እባኮት አዲስ ቀን ለመምረጥ /book የሚለውን ይጠቀሙ."
            )
            try:
                await context.bot.send_message(telegram_id, message)
                cursor.execute("INSERT INTO notifications (sent_to, message, sent_at) VALUES (%s, %s, %s)", (telegram_id, message, datetime.now()))
                conn.commit()
            except Exception as e:
                print(f"Failed to notify user {telegram_id}: {e}")
        return await query.edit_message_text("✅ ቀጠሮውን ሰርዘዋል")

# 📅 Add Availability
async def handle_add_avail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        return await update.message.reply_text("🚫 ያልተፈቀደ.")
    
    context.user_data["avail_state"] = "awaiting_date"
    await update.message.reply_text("📅 እባኮትን የሚገኙበትን ቀን ያስፍሩ (YYYY-MM-DD):")
    return "awaiting_date"

async def handle_add_avail_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = context.user_data.get("avail_state")

    if user_id not in ADMIN_ID:
        return ConversationHandler.END

    if state == "awaiting_date":
        date_text = update.message.text.strip()

        try:
            #avail_date = datetime.strptime(date_text, "%Y-%m-%d").date()
            avail_date= ethiopian_to_gregorian(date_text)
        except ValueError:
            await update.message.reply_text("❌ የተሳሳተ ቀን. እባኮትን በዚህ መስፈርት ያስገቡ (e.g. 2017-04-29).")
            return "awaiting_date"

        if avail_date < datetime.today().date():
            await update.message.reply_text("❌ ያለፉ ቀናትን ማስገባት አይችሉም.")
            return "awaiting_date"

        context.user_data["avail_date"] = avail_date
        context.user_data["avail_state"] = "awaiting_slots"
        await update.message.reply_text("🔢 ምን ያህል ሰዎችን ማግኝት ይችላሉ?")
        return "awaiting_slots"

    elif state == "awaiting_slots":
        slots_text = update.message.text.strip()

        if not slots_text.isdigit() or int(slots_text) <= 0:
            await update.message.reply_text("❌ ከ 0 በላይ የሆነ ቁጥር ያስገቡ.")
            return "awaiting_slots"

        slots = int(slots_text)
        avail_date = context.user_data.get("avail_date")
        cursor.execute("""
            INSERT INTO available_days (appointment_date, max_slots)
            VALUES (%s, %s)
            ON CONFLICT (appointment_date) DO UPDATE SET max_slots = EXCLUDED.max_slots
        """, (avail_date, slots))
        conn.commit()

        context.user_data.pop("avail_state", None)
        context.user_data.pop("avail_date", None)
        
        await update.message.reply_text(
            f"✅ በ {to_ethiopian(avail_date)} {slots} ሰዎችን ለማግኘት ቀን አስገብተዋል."
        )
        return ConversationHandler.END

# 🛑 Cancel Availability Creation
async def cancel_availability_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("avail_state", None)
    context.user_data.pop("avail_date", None)
    await update.message.reply_text("❌ ቀን ማስገባቶን አቋርጠው ወተዋል.")
    return ConversationHandler.END

# Cancel Existing Availabilities
async def handle_cancel_avail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        if update.callback_query:
            await update.callback_query.answer("🚫 ያልተፈቀደ.")
        return
    
    cursor.execute("""
        SELECT appointment_date, max_slots 
        FROM available_days 
        WHERE appointment_date >= %s
        ORDER BY appointment_date ASC
    """, (datetime.now().date(),))
    
    availabilities = cursor.fetchall()
    
    if not availabilities:
        if update.callback_query:
            await update.callback_query.edit_message_text("📭 ምንም የሚሰረዙ ቀናት የሉም.")
        else:
            await update.message.reply_text("📭 ምንም የሚሰረዙ ቀናት የሉም.")
        return
    keyboard = [
        [InlineKeyboardButton(
            f"{ethiopian_day_name(date)} {to_ethiopian(date)} ({slots} ቦታዎች)",
            callback_data=f"cancel_avail_{date.strftime('%Y-%m-%d')}")]
        for date, slots in availabilities
    ]
    
    await update.message.reply_text(
        "🗑 ለመሰረዝ የሚፈልጉትን ቀን ይምረጡ:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    keyboard.append([InlineKeyboardButton("ይቅር", callback_data="cancel_avail_menu")])
        
async def handle_cancel_avail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    admin_id = query.from_user.id

    if admin_id not in ADMIN_ID:
        return await query.edit_message_text("🚫 ያልተፈቀደ.")

    if data == "cancel_avail_menu":
        await query.edit_message_text("🚫 አቋርጠው ወተዋል.")
        return

    if data.startswith("cancel_avail_"):
        date_str = data[len("cancel_avail_"):]
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if date < datetime.now().date():
                return await query.edit_message_text("❌ ያለፉ ቀናትን ማቋረጥ አይቻልም.")
        except ValueError:
            return await query.edit_message_text("❌ የተሳሳተ ቀን. እባኮትን በዚህ መስፈርት ያስገቡ (2017-08-29).")

        # Get appointment count and user details
        cursor.execute("""
            SELECT COUNT(*), array_agg(u.telegram_id)
            FROM appointments a
            JOIN users u ON a.user_id = u.id
            WHERE a.appointment_date = %s AND a.status = 'በመጠበቅ'
        """, (date,))
        result = cursor.fetchone()
        count = result[0] if result else 0
        telegram_ids = result[1] if result and result[1] else []

        confirm_text = f"⚠️ በ {to_ethiopian(date_str)} ያሉትን ቀናት መሰረዝ ይፈልጋሉ?"
        if count > 0:
            confirm_text += f"\n\nይህ ድርጊት {count} ቀጠሮዎችን ይሰርዛል."

        await query.edit_message_text(
            confirm_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ አረጋግጥ", callback_data=f"confirm_cancel_{date_str}")],
                [InlineKeyboardButton("ይቅር", callback_data="avail_cancel_back")]
            ])
        )
        
        context.user_data['pending_cancel'] = {
            'date_str': date_str,
            'telegram_ids': telegram_ids
        }
        return

    if data.startswith("confirm_cancel_"):
        date_str = data[len("confirm_cancel_"):]
        cancel_data = context.user_data.get('pending_cancel', {})
        telegram_ids = cancel_data.get('telegram_ids', [])
        
        try:
            # Prepare cancellation message
            message = (
                f"⚠️ የቀጠሮ ስረዛ ማስታውሻ\n\n"
                f"በ {to_ethiopian(date_str)} የነበሮት ቀን ተሰርዟል.\n"
                f"እባኮት አዲስ ቀን ለመምረጥ /book የሚለውን ይጫኑ."
            )
            
            # Delete availability (will cascade to appointments)
            cursor.execute("DELETE FROM available_days WHERE appointment_date = %s", (date_str,))
            conn.commit()
            
            # Notify affected users
            if telegram_ids:
                bot = context.bot
                for user_id in telegram_ids:
                    try:
                        await bot.send_message(user_id, message)
                        await asyncio.sleep(3)  # Rate limiting
                        cursor.execute("INSERT INTO notifications (sent_to, message, sent_at) VALUES (%s, %s, %s)", (user_id, message, datetime.now()))
                        conn.commit()
                    except Exception as e:
                        print(f"ማሳወቅ አልተቻለም {user_id}: {e}")

            await query.edit_message_text(
                f"✅ በ {to_ethiopian(date_str)} የነበረው ቀን ተሰርዟል.\n"
                f"📩 ለ {len(telegram_ids)} ሰዎች አሳውቀዋል."
            )
            
        except Exception as e:
            conn.rollback()
            await query.edit_message_text(
                f"❌ ቀን መኖሩን ማረጋግጥ አልተቻለም.\n"
                f"Error: {str(e)}"
            )
        finally:
            context.user_data.pop('pending_cancel', None)

    if data == "avail_cancel_back":
        #context.user_data.pop('pending_cancel', None)
        await query.edit_message_text("✅ ትተው ወተዋል።")


async def handle_view_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        return await update.message.reply_text("🚫 ይህን ለመጠቀም አልተፈቀደሎትም.")
    
    cursor.execute("""
        SELECT id, question, status
        FROM questions
        WHERE status = 'በመጠበቅ'
        ORDER BY created_at DESC
    """)
    questions = cursor.fetchall()

    if not questions:
        return await update.message.reply_text("📭 ምንም ጥያቄ የሎትም.")

    for q_id, question, status in questions:
        keyboard = [
            [InlineKeyboardButton("✅ ተመልሷል", callback_data=f"question_complete_{q_id}"),
             InlineKeyboardButton("❌ ሰርዝ", callback_data=f"question_cancel_{q_id}")]
        ]
        await update.message.reply_text(
            f"❓ {question}\n"
            f"📌 ሁኔታ: {status.capitalize()}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# 🔄 Admin Callback Handler for Questions
async def handle_admin_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    admin_id = query.from_user.id

    if admin_id not in ADMIN_ID:
        return await query.edit_message_text("🚫 ይህን ለመጠቀም አልተፈቀደሎትም.")
    
    if data.startswith("question_complete_"):
        question_id = int(data.split("_")[2])
        cursor.execute("UPDATE questions SET status = 'የተጠናቀቀ' WHERE id = %s", (question_id,))
        conn.commit()
        return await query.edit_message_text("✅ ጥያቄው ተመልሷል.")
    elif data.startswith("question_cancel_"):
        question_id = int(data.split("_")[2])
        cursor.execute("UPDATE questions SET status = 'የተሰረዘ' WHERE id = %s", (question_id,))
        conn.commit()
        return await query.edit_message_text("❌ ጥያቄው ተሰረዟል.")


# Admin handler for communions
async def handle_admin_communion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        return await update.message.reply_text("🚫 ይህን ለመጠቀም አልተፈቀደሎትም.")
    
    # lets fetch the names of the users first
    cursor.execute("""
        SELECT u.id, u.name, u.email, c.id, c.comm_date, c.status
        FROM users u
        JOIN communion c ON u.id = c.user_id
        WHERE c.status = 'በመጠበቅ'
        ORDER BY u.name ASC
    """)
    users = cursor.fetchall()
    if not users:
        return await update.message.reply_text("📭 ምንም የቁርባን የሎትም.")
    
    # cursor.execute("""
    #     SELECT id, comm_date, status
    #     FROM communion
    #     WHERE status = 'በመጠበቅ'
    #     ORDER BY comm_date ASC
    # """)
    # communions = cursor.fetchall()

    # if not communions:
    #     return await update.message.reply_text("📭 ምንም የቁርባን የሎትም.")

    for u_id, name, email, c_id, comm_date, status in users:
        keyboard = [
            [InlineKeyboardButton("✅ ተቀበል", callback_data=f"communion_complete_{c_id}"),
             InlineKeyboardButton("❌ ሰርዝ", callback_data=f"communion_cancel_{c_id}")]
        ]
        await update.message.reply_text(
            f"ስም: {name}\n"
            f"ክርስትና ስም: {email}\n"
            f"የቁርባን ቀን፡ {to_ethiopian(comm_date)}\n"
            f"📌 ሁኔታ: {status.capitalize()}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# 🔄 Admin Callback Handler for Communions
async def handle_admin_communion_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    admin_id = query.from_user.id

    if admin_id not in ADMIN_ID:
        return await query.edit_message_text("🚫 ይህን ለመጠቀም አልተፈቀደሎትም.")
    
    if data.startswith("communion_complete_"):
        communion_id = int(data.split("_")[2])
        cursor.execute("UPDATE communion SET status = 'የተጠናቀቀ', updated_at= %s WHERE id = %s", (datetime.now(),communion_id,))
        conn.commit()
        return await query.edit_message_text("✅ የቁርባን ቀን ፀድቋል.")
    elif data.startswith("communion_cancel_"):
        communion_id = int(data.split("_")[2])
        cursor.execute("UPDATE communion SET status = 'የተሰረዘ', updated_at= %s WHERE id = %s", (datetime.now(),communion_id,))
        conn.commit()
        return await query.edit_message_text("❌ የቁርባን ቀን ተሰረዟል.")