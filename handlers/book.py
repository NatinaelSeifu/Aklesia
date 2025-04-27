# handlers/booking.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db import cursor, conn
from datetime import datetime, timedelta
from utils.ethiopian_calendar import ethiopian_day_name, to_ethiopian, format_ethiopian_date


# AMHARIC_DAYS = {
#     0: "ሰኞ",    # Monday
#     1: "ማክሰኞ",  # Tuesday
#     2: "ረቡዕ",    # Wednesday
#     3: "ሐሙስ",    # Thursday
#     4: "ዓርብ",    # Friday
#     5: "ቅዳሜ",    # Saturday
#     6: "እሑድ"     # Sunday
# }

# /book command handler
async def handle_booking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Check if user is registered
    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        return await update.message.reply_text("🚫 አገልግልቱን ለማግኘት በቅድሚያ /register ላይ ገብተው ይመዝገቡ.")

    # Check if user already has a pending appointment
    today = datetime.now().date()
    cursor.execute("""
        SELECT * FROM appointments
        WHERE user_id = %s AND appointment_date >= %s AND status = 'በመጠበቅ'
    """, (user[0], today))
    existing = cursor.fetchone()
    if existing:
        return await update.message.reply_text("📌ከዚህ በፊት የተዘጋጀ ቀጠሮ አሎት. በዚህ ማየት ይችላሉ /mybookings")

    # Step 1: Get next 14 days
    next_14_days = [today + timedelta(days=i) for i in range(14)]

    # Step 2: Filter default available days: Wednesdays (2) and Fridays (4)
    default_days = [d for d in next_14_days if d.weekday() in [2, 4]]

    for day in default_days:
        cursor.execute("""
            INSERT INTO available_days (appointment_date, max_slots, status)
            VALUES (%s, %s, %s)
            ON CONFLICT (appointment_date) DO NOTHING
        """, (day, 15, 'active'))
    conn.commit()
    # Step 3: Check for added days
    cursor.execute("SELECT appointment_date FROM available_days WHERE appointment_date >= %s AND status = 'active'", (today,))
    added_days = [row[0] for row in cursor.fetchall()]

    # Step 4: Merge and deduplicate
    #combined_days = sorted(set(default_days + added_days))

    # Step 5: Filter out fully booked days
    valid_days = []
    for day in added_days:
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date = %s", (day,))
        booked = cursor.fetchone()[0]

        cursor.execute("SELECT max_slots FROM available_days WHERE appointment_date = %s", (day,))
        row = cursor.fetchone()
        max_slots = row[0] if row else 15  # Default: 1 slots for Wed/Fri

        if booked < max_slots:
            valid_days.append(day)

    if not valid_days:
        return await update.message.reply_text("😕 በዚህ ቀን ቀጠሮ ማግኘት አይችሉም. እባኮትን ሌላ ቀን ይምክሩ.")

    # Step 6: Show inline buttons
    buttons = [
        [InlineKeyboardButton(
            f"{ethiopian_day_name(day)} {to_ethiopian(day)}", 
            callback_data=f"book_{day.strftime('%Y-%m-%d')}")]
        for day in valid_days
    ]
    
    await update.message.reply_text(
        "📅 የሚገኙ ቀኖች (Ethiopian Calendar):",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    # buttons = [
    #     [InlineKeyboardButton(day.strftime("%A %Y-%m-%d"), callback_data=f"book_{day}")]
    #     for day in valid_days
    # ]
    # await update.message.reply_text("📅 Choose an available day:", reply_markup=InlineKeyboardMarkup(buttons))


# Callback handler for booking
async def handle_booking_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("book_"):
        selected_date = data.split("_")[1]
        appointment_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
        context.user_data['booking_date'] = appointment_date

        # Use the imported functions
        eth_date = format_ethiopian_date(appointment_date)
        day_name = ethiopian_day_name(appointment_date)

        

        buttons = [
            [InlineKeyboardButton("✅ አዎ", callback_data="confirm_booking")],
            [InlineKeyboardButton("❌ አይ", callback_data="cancel_booking")]
        ]
        # if the selected date is today response text should have a warning message saying they cant cancel or change in less than 24 hours
        time_left = datetime.combine(appointment_date, datetime.min.time()) - datetime.now()
        if time_left < timedelta(hours=24):
            eth_date = format_ethiopian_date(appointment_date)
            return await query.edit_message_text(
                f"⏰ ከ 24 ሰአት በታች ለሆኑ ቀጠሮዎች ማቋረጥ እንዲሁም መቀየር አይቻልም።\n"
                f"🗓️ የመረጡት: {day_name} {eth_date}\nለመወሰን ይፈልጋሉ?",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        await query.edit_message_text(
            f"🗓️ የመረጡት: {day_name} {eth_date}\nለመወሰን ይፈልጋሉ?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )

        # buttons = [
        #     [InlineKeyboardButton("✅ Confirm", callback_data="confirm_booking")],
        #     [InlineKeyboardButton("❌ Cancel", callback_data="cancel_booking")]
        # ]
        # await query.edit_message_text(
        #     f"🗓️ You selected: {appointment_date.strftime('%A, %d %B %Y')}\nDo you want to confirm?",
        #     reply_markup=InlineKeyboardMarkup(buttons)
        # )

    # Step 2: Confirm booking
    elif data == "confirm_booking":
        cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
        user = cursor.fetchone()

        appointment_date = context.user_data.get('booking_date')
        if not appointment_date:
            return await query.edit_message_text("❗ የሆነ ነገር ተበላሽቷል. እባኮትን ድጋሚ ይሞክሩ.")

        # Ensure appointment_date exists in available_days
        cursor.execute("SELECT max_slots FROM available_days WHERE appointment_date = %s", (appointment_date,))
        row = cursor.fetchone()
        if not row:
            # Default for Wed/Fri: add with 15 slots
            cursor.execute("""
                INSERT INTO available_days (appointment_date, max_slots)
                VALUES (%s, 15)
            """, (appointment_date,))
            conn.commit()

        # Recheck booking slot count
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date = %s", (appointment_date,))
        booked = cursor.fetchone()[0]

        cursor.execute("SELECT max_slots FROM available_days WHERE appointment_date = %s", (appointment_date,))
        row = cursor.fetchone()
        max_slots = row[0]

        if booked >= max_slots:
            return await query.edit_message_text("🚫 የመረጡት ቀን ሞልቷል፣ እባኮት ሌላ ቀን ይምረጡ.")

        # Insert appointment
        cursor.execute("""
            INSERT INTO appointments (user_id, appointment_date, status)
            VALUES (%s, %s, 'በመጠበቅ')
        """, (user[0], appointment_date))
        conn.commit()

        return await query.edit_message_text(
            f"✅ ቀጠሮ ለ {ethiopian_day_name(appointment_date)} {format_ethiopian_date(appointment_date)} ተደርጓል. /mybookings ላይ በመሄድ ያሎትን ቀጠሮ ማየት እንዲሁም መቀየር ይችላሉ." # .strftime('%A, %d %B %Y')
        )

        # Check again if slot is still available
        # cursor.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date = %s", (appointment_date,))
        # booked = cursor.fetchone()[0]

        # cursor.execute("SELECT max_slots FROM available_days WHERE appointment_date = %s", (appointment_date,))
        # row = cursor.fetchone()
        # max_slots = row[0] if row else 1

        # if booked >= max_slots:
        #     return await query.edit_message_text("🚫 That day is fully booked. Please choose another.")

        # # Save appointment
        # cursor.execute("""
        #     INSERT INTO appointments (user_id, appointment_date, status)
        #     VALUES (%s, %s, 'pending')
        # """, (user[0], appointment_date))
        # conn.commit()

        # return await query.edit_message_text(
        #     f"✅ Your appointment is confirmed for {appointment_date.strftime('%A, %d %B %Y')}."
        # )

    # Step 3: Cancel booking
    elif data == "cancel_booking":
        return await query.edit_message_text("❌ ቀጠሮ መያዙን አቋርጠዋል.")

async def handle_mybookings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT id FROM users WHERE telegram_id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        return await update.message.reply_text("🚫 አዲስ ስለሆኑ እባኮትን መጀመሪያ ይመዝገቡ. /register የሚለውን በመንካት መጀመር ይችላሉ.")

    cursor.execute("""
        SELECT id, appointment_date FROM appointments 
        WHERE user_id = %s AND status = 'በመጠበቅ'
        ORDER BY appointment_date ASC
    """, (user[0],))
    appointments = cursor.fetchall()

    if not appointments:
        return await update.message.reply_text("📭 ምንም ቀጠሮ የሎትም.")

    for appt_id, appt_date in appointments:
        can_change = datetime.combine(appt_date, datetime.min.time()) - datetime.now() > timedelta(hours=24)
        keyboard = []
        if can_change:
            keyboard.append([InlineKeyboardButton("🔄 ቀን ቀይር", callback_data=f"change_{appt_id}")])
            keyboard.append([InlineKeyboardButton("❌ ሰርዝ", callback_data=f"cancel_{appt_id}")])

        await update.message.reply_text(
            f"📅 አሁን ያለ ቀጠሮ {ethiopian_day_name(appt_date)} {format_ethiopian_date(appt_date)}",
            #f"📅 አሁን ያለ ቀጠሮ {appt_date.strftime('%A, %d %B %Y')}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# Handle change/cancel actions
async def handle_mybookings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data.startswith("cancel_"):
        appointment_id = int(data.split("_")[1])
        
        # Get appointment date first
        cursor.execute("""
            SELECT appointment_date FROM appointments 
            WHERE id = %s AND user_id = (SELECT id FROM users WHERE telegram_id = %s)
        """, (appointment_id, user_id))
        result = cursor.fetchone()
        
        if not result:
            return await query.edit_message_text("❌ ቀጠሮ አልተገኘም።")
        
        appt_date = result[0]
        
        # Check if it's too late to cancel (less than 24 hours)
        time_left = datetime.combine(appt_date, datetime.min.time()) - datetime.now()
        if time_left < timedelta(hours=24):
            eth_date = format_ethiopian_date(appt_date)
            return await query.edit_message_text(
                f"⏰ ከ 24 ሰአት በታች ለሆኑ ቀጠሮዎች ማቋረጥ እንዲሁም መቀየር አይቻልም።\n"
                f"ቀን: {eth_date}\n"
            )
        # Confirm cancellation
        buttons = [
            [InlineKeyboardButton("✅ አዎ", callback_data=f"confirm_cancell_{appointment_id}")],
            [InlineKeyboardButton("❌ አይ", callback_data="abort_cancel_")]
        ]
        await query.edit_message_text(
            f"📅 ቀጠሮዎን ማሰረዝ ይፈልጋሉ?\n"
            f"ቀን: {format_ethiopian_date(appt_date)}\n",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    
        
        # buttons = [
        #     [InlineKeyboardButton(day[0].strftime("%A %Y-%m-%d"), callback_data=f"confirm_change_{appointment_id}_{day[0]}")]
        #     for day in days
        # ]

        # await query.edit_message_text("🔄 Select a new date:", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("change_"):
        appointment_id = int(data.split("_")[1])
        
        # Get appointment date first
        cursor.execute("""
            SELECT appointment_date FROM appointments 
            WHERE id = %s AND user_id = (SELECT id FROM users WHERE telegram_id = %s)
        """, (appointment_id, user_id))
        result = cursor.fetchone()
        
        if not result:
            return await query.edit_message_text("❌ ቀጠሮ አልተገኘም።")
        
        appt_date = result[0]
        
        # Check if it's too late to change (less than 24 hours)
        time_left = datetime.combine(appt_date, datetime.min.time()) - datetime.now()
        if time_left < timedelta(hours=24):
            eth_date = format_ethiopian_date(appt_date)
            return await query.edit_message_text(
                f"⏰ ከ 24 ሰአት በታች ለሆኑ ቀጠሮዎች ማቋረጥ እንዲሁም መቀየር አይቻልም።\n"
                f"ቀን: {eth_date}\n"
            )

        # Get valid change options
        today = datetime.now().date()
        next_14_days = [today + timedelta(days=i) for i in range(14)]

    # Step 2: Filter default available days: Wednesdays (2) and Fridays (4)
        default_days = [d for d in next_14_days if d.weekday() in [2, 4]]

        cursor.execute("SELECT appointment_date FROM available_days WHERE appointment_date >= %s", (today,))
        added_days = [row[0] for row in cursor.fetchall()]
        # Merge and deduplicate
        combined_days = sorted(set(default_days + added_days))

        valid_days = []
        for day in combined_days:
            cursor.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date = %s", (day,))
            booked = cursor.fetchone()[0]

            cursor.execute("SELECT max_slots FROM available_days WHERE appointment_date = %s", (day,))
            row = cursor.fetchone()
            max_slots = row[0] if row else 15  # Default: 1 slots for Wed/Fri

            if booked < max_slots:
                valid_days.append(day)
        if not valid_days:
            return await query.edit_message_text("😕 በዚህ ቀን ቀጠሮ ማግኘት አይችሉም. እባኮትን ሌላ ቀን ይምክሩ.")
        # Step 6: Show inline buttons
        buttons = [
            [InlineKeyboardButton(f"{ethiopian_day_name(day)} {format_ethiopian_date(day)}", callback_data=f"confirm_change_{appointment_id}_{day.strftime('%Y-%m-%d')}")]
            for day in valid_days
        ]

        await query.edit_message_text("⚠️ከ 24 ሰአት በታች ለሚደረጉ ቅያሪዎች ማቋረጥ እንዲሁም መቀየር አይቻልም \n🔄 አዲስ ቀን ይምረጡ:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("confirm_cancell_"):
        appointment_id = int(data.split("_")[2])
        cursor.execute("DELETE FROM appointments WHERE id = %s", (appointment_id,))
        conn.commit()
        await query.edit_message_text("✅ ቀጠሮዎን ሰርዘዋል።")

    elif data.startswith("abort_cancel_"):
        await query.edit_message_text("✅ ትተው ወተዋል።")


    elif data.startswith("confirm_change_"):
        _, appointment_id, new_date_str = data.rsplit("_", 2)
        appointment_id = int(appointment_id)
        new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()

        # Final check if slot is still open
        cursor.execute("SELECT COUNT(*) FROM appointments WHERE appointment_date = %s", (new_date,))
        count = cursor.fetchone()[0]

        cursor.execute("SELECT max_slots FROM available_days WHERE appointment_date = %s", (new_date,))
        max_slots_row = cursor.fetchone()
        max_slots = max_slots_row[0] if max_slots_row else 15

        if count >= max_slots:
            return await query.edit_message_text("🚫 የመረጡት ቀን ሞልቷል እባኮትን ሌላ ይምረጡ.")

        # Ensure it's still valid to change
        cursor.execute("SELECT appointment_date FROM appointments WHERE id = %s", (appointment_id,))
        old_date_row = cursor.fetchone()
        if not old_date_row:
            return await query.edit_message_text("❌ ምንም ቀጠሮ የለም.")

        # if the date doesnt exist in the available days table, add it
        cursor.execute("SELECT appointment_date FROM available_days WHERE appointment_date = %s", (new_date,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO available_days (appointment_date, max_slots) VALUES (%s, 15)", (new_date,))
            conn.commit()

        # Apply the change
        cursor.execute("UPDATE appointments SET appointment_date = %s WHERE id = %s", (new_date, appointment_id))
        conn.commit()
        await query.edit_message_text(f"✅ የቀጠሮ ቀን ተቀይሯል።\n"f"አዲስ ቀን: {ethiopian_day_name(new_date)} {format_ethiopian_date(new_date)}"  # "Appointment date changed. New date: [day] [date]"
    )
