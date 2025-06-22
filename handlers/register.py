# handlers/register.py
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from db import cursor, conn
import re
from datetime import datetime
import uuid

# Configure logger
import logging

logger = logging.getLogger("bot_logger")

if not logger.hasHandlers():
    logger.setLevel(logging.INFO)

    # Terminal (console) logging only
    stream_handler = logging.StreamHandler()
    stream_formatter = logging.Formatter('%(levelname)s - %(message)s')
    stream_handler.setFormatter(stream_formatter)

    logger.addHandler(stream_handler)



# Registration handler
async def handle_register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    telegram_id = user.id

    logger.info(f"/register triggered by user {telegram_id}")

    cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
    existing = cursor.fetchone()

    if existing:
        logger.info(f"User {telegram_id} is already registered.")
        await update.message.reply_text(
            "👤 ከዚህ በፊት ተመዝግበዋል. አካውንት ለማየት ወይም ለማስተካከል /profile የሚለውን ይጫኑ" #You're already registered. You can view or edit your profile using /profile.
        )
        return

    await update.message.reply_text("እባክዎ ሙሉ ስም ያስገቡ:")
    context.user_data['register_step'] = 'name'
    context.user_data['is_new_user'] = True

# Conversation handler
async def handle_register_convo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle callback queries first
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        text = query.data  # This will be "married" or "single"
        
        # For marital status callback
        context.user_data['marital_status'] = text
        
        if text == 'ያገባ':
            context.user_data['register_step'] = 'children'
            await query.edit_message_text("የልጆችዎ ስሞች ያስገቡ (በነጠላ ሰረዝ ለምሳሌ: ማርያም፣ ዮሐንስ)")
        else:
            context.user_data['children'] = None
            await save_user_profile(update, context)
            # send confirmation message
            await query.edit_message_text("✅ ምዝገባ ተጠናቋል! /book የሚለውን በመንካት ቀጠሮ ማካሄድ ይችላሉ. ወይም /profile የሚለውን በመጫን መገለጫዎን ይመልከቱ.")
        return  # Important: return after handling callback to prevent further processing
    
    # Only proceed with message handling if there's actually a message
    if not update.message or not update.message.text:
        return
    
    # Handle regular message updates
    user_id = update.effective_user.id
    step = context.user_data.get('register_step')
    text = update.message.text.strip()

    logger.info(f"User {user_id} step: {step}, input: {text}")

    if step == 'name':
        if context.user_data.get('is_new_user'):
            context.user_data['name'] = text
            context.user_data['register_step'] = 'phone'
            return await update.message.reply_text("እባክዎ ስልክ ቁጥር ያስገቡ: (0911234567)")
        else:
            cursor.execute("UPDATE users SET name = %s, updated_at = NOW() WHERE telegram_id = %s", (text, user_id))
            conn.commit()
            context.user_data.clear()
            logger.info(f"User {user_id} updated name") 
            return await update.message.reply_text("✅ ስም ተለውጧል.")

    elif step == 'phone':
        if not re.fullmatch(r"0\d{9}", text):
            logger.warning(f"User {user_id} የተሳሳተ ስልክ አስገብተዋል: {text}")
            return await update.message.reply_text("⚠️ ስልክ ቁጥር በ 0 የሚጀምር እና10 ዲጂት መሆን አለበት. እባኮት ድጋሚ ይሞክሩ:")

        if context.user_data.get('is_new_user'):
            context.user_data['phone'] = text
            context.user_data['register_step'] = 'email'
            return await update.message.reply_text("የክርስትና ስም:")
        else:
            cursor.execute("UPDATE users SET phone = %s, updated_at = NOW() WHERE telegram_id = %s", (text, user_id))
            conn.commit()
            context.user_data.clear()
            logger.info(f"User {user_id} updated phone")
            return await update.message.reply_text("📞 ስልክ ተለውጧል.")

    elif step == 'email':
        if context.user_data.get('is_new_user'):
            context.user_data['email'] = text
            context.user_data['register_step'] = 'joined_on'
            return await update.message.reply_text("አባል የሆኑበት ቀን (ምሳሌ: 2017-08-25)")
        else:
            cursor.execute("UPDATE users SET email = %s, updated_at = NOW() WHERE telegram_id = %s", (text, user_id))
            conn.commit()
            context.user_data.clear()
            logger.info(f"User {user_id} updated email")
            return await update.message.reply_text("📧 የክርስትና ስም ተለውጧል.")

    elif step == 'joined_on':
        try:
            joined_on = datetime.strptime(text, "%Y-%m-%d")
            if context.user_data.get('is_new_user'):
                context.user_data['joined_on'] = joined_on
                context.user_data['register_step'] = 'marital_status'
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("ያገባሁ", callback_data="ያገባ")],
                    [InlineKeyboardButton("ያገባሁ አይደለሁም", callback_data="ያላገባ")]
                ])
                await update.message.reply_text("የጋብቻ ሁኔታ?", reply_markup=keyboard)
                return
            else:
                cursor.execute("UPDATE users SET joined_on = %s, updated_at = NOW() WHERE telegram_id = %s", 
                            (joined_on, user_id))
                conn.commit()
                context.user_data.clear()
                logger.info(f"User {user_id} updated joined_on")
                return await update.message.reply_text("📅 የገቡበትን ቀን ቀይረዋል.")
        except ValueError:
            logger.warning(f"User {user_id} provided invalid date: {text}")
            return await update.message.reply_text("⚠️ የተሳሳተ ቀን አስገብተዋል. እባኮትን በዚህ መንገድ ያስተካክሉ: 2027-08-25")
    
    elif step == 'children':
        if context.user_data.get('is_new_user'):
            context.user_data['children'] = text
            await save_user_profile(update, context)
            await update.message.reply_text("✅ ምዝገባ ተጠናቋል! /book የሚለውን በመንካት ቀጠሮ ማካሄድ ይችላሉ. ወይም /profile የሚለውን በመጫን መገለጫዎን ይመልከቱ.")
        else:
            cursor.execute("UPDATE users SET children = %s, updated_at = NOW() WHERE telegram_id = %s", (text, user_id))
            conn.commit()
            context.user_data.clear()
            logger.info(f"User {user_id} updated children")
            return await update.message.reply_text("👶 የልጆች ክርስትና ስም ተለውጧል.")

async def handle_edit_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id

    logger.info(f"User {user_id} clicked profile button: {data}")

    context.user_data['is_new_user'] = False

    if data == 'edit_name':
        context.user_data['register_step'] = 'name'
        await query.edit_message_text("✏️ ሙሉ ስም:")
    elif data == 'edit_phone':
        context.user_data['register_step'] = 'phone'
        await query.edit_message_text("📞 ስልክ ቁጥር: ( ምሳሌ 0911234567)")
    elif data == 'edit_email':
        context.user_data['register_step'] = 'email'
        await query.edit_message_text("📧 ክርስትና ስም:")
    elif data == 'edit_joined_on':
        context.user_data['register_step'] = 'joined_on'
        await query.edit_message_text("📅 የክርስትና ልጅ የሆኑበት ቀን (ምሳሌ 2016-08-26):")
    # elif data == 'edit_marital_status':
    #     keyboard = InlineKeyboardMarkup([
    #         [InlineKeyboardButton("ያገባሁ", callback_data="married")],
    #         [InlineKeyboardButton("ያገባሁ አይደለሁም", callback_data="single")]
    #     ])
    #     await query.edit_message_text("የጋብቻ ሁኔታ?", reply_markup=keyboard)
    elif data == 'edit_children':
        context.user_data['register_step'] = 'children'
        await query.edit_message_text("የልጆችዎ ክርስትና ስሞች ያስገቡ (በነጠላ ሰረዝ ለምሳሌ: ማርያም፣ ዮሐንስ)")

    elif data == 'delete_profile':
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ አዎን፣ አጥፋ", callback_data="confirm_delete_yes"),
                InlineKeyboardButton("❌ አቋርጥ", callback_data="confirm_delete_no")
            ]
        ])
        await query.edit_message_text(
            "⚠️ አካውንቱን ማጥፋት ይፈልጋሉ? ይህ ድርጊት ወደኋላ መመለሻ የለውም.",
            reply_markup=keyboard
        )

    elif data == 'confirm_delete_yes':
        try:
            # First delete the user's appointments
            cursor.execute("DELETE FROM appointments WHERE user_id = %s", (user_id,))
            
            # Then delete the user profile
            cursor.execute("DELETE FROM users WHERE telegram_id = %s", (user_id,))
            
            conn.commit()
            
            logger.info(f"User {user_id} and their appointments were successfully deleted.")
            await query.edit_message_text("🗑️ አካውንቶ በተገቢ ሁኔታ ዲሌት ሆኗል።")
        
        except Exception as e:
            logger.error(f"Error deleting user {user_id} and appointments: {e}")
            await query.edit_message_text("❌ አካውንቶ ማጥፋት አልተቻለም። እባኮትን ድግሚ ይሞክሩ።")

    elif data == 'confirm_delete_no':
        logger.info(f"User {user_id} canceled profile deletion.")
        await query.edit_message_text("✅ አካውንት ዲሌት ማድርጉን አቋርጠዋል.")


# Save user profile to DB
async def save_user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    name = context.user_data['name']
    phone = context.user_data['phone']
    email = context.user_data['email']
    joined_on = context.user_data['joined_on']
    marital_status = context.user_data['marital_status']
    children = context.user_data.get('children')
    # set id uuid
    
    user_id = str(uuid.uuid4())
    
    logger.info(f"Saving profile for user {telegram_id}")

    cursor.execute("""
        INSERT INTO users (id,telegram_id, name, phone, email, joined_on, marital_status, children, created_at, updated_at)
        VALUES (%s,%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
    """, (user_id,telegram_id, name, phone, email, joined_on, marital_status, children))

    conn.commit()
    context.user_data.clear()

# /profile command handler
async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    logger.info(f"User {telegram_id} requested profile view")

    cursor.execute("SELECT name, phone, email, joined_on, marital_status, children FROM users WHERE telegram_id = %s", (telegram_id,))
    user = cursor.fetchone()

    if user:
        name, phone, email, joined_on, m_status, children = user
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("ስም ለማስተካከል", callback_data='edit_name')],
            [InlineKeyboardButton("ስልክ ለማስተካከል", callback_data='edit_phone')],
            [InlineKeyboardButton("ክርስትና ስም ለማስተካከል", callback_data='edit_email')],
            [InlineKeyboardButton("የአባልነት ቀን ለማስተካከል", callback_data='edit_joined_on')],
            #[InlineKeyboardButton("የጋብቻ ሁኔታ ለማስተካከል", callback_data='edit_marital_status')],
            [InlineKeyboardButton("የልጆች ስም ለማስተካከል", callback_data='edit_children')],
            [InlineKeyboardButton("🗑️ አካውንት ለማጥፋት", callback_data='delete_profile')],
        ])
        await update.message.reply_text(
            f"👤 የእርስዎ መገለጫ:\n\n👤 ስም: {name}\n📞 ስልክ: {phone}\n📧 ክርስትና ስም: {email}\n📅 የአባልነት ቀን: {joined_on.strftime('%Y-%m-%d') if joined_on else 'N/A'}\n  {"👶 የልጆች ክርስትና ስም፡ \n" + children if children else ''}",
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text("❌ አዲስ ስለሆኑ እባኮትን ይመዝገቡ. /register የሚለውን በመንካት መጀመር ይችላሉ.")
