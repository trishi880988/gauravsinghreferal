import os
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
import requests

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
PREMIUM_LINK = os.getenv('PREMIUM_GROUP_LINK')

# Load channel IDs from environment variables
CHANNELS = os.getenv('CHANNEL_IDS', '').split(',')
CHANNELS = [int(channel_id.strip()) for channel_id in CHANNELS if channel_id.strip()]

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

client = MongoClient(MONGO_URI)
db = client.referral_bot
users_collection = db.users

def is_user_joined(user_id):
    for channel_id in CHANNELS:
        url = f"https://api.telegram.org/bot{TOKEN}/getChatMember?chat_id={channel_id}&user_id={user_id}"
        response = requests.get(url).json()
        if response.get("ok") and response["result"]["status"] not in ["member", "administrator", "creator"]:
            return False
    return True

def add_user(user_id, referer_id=None):
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({
            "user_id": user_id,
            "referer_id": referer_id,
            "referral_count": 0,
            "referred_users": []
        })

def update_referral_count(referer_id, new_user_id, context):
    referer = users_collection.find_one({"user_id": referer_id})
    if referer and new_user_id not in referer.get("referred_users", []):
        new_count = referer['referral_count'] + 1
        users_collection.update_one(
            {"user_id": referer_id},
            {"$inc": {"referral_count": 1}, "$push": {"referred_users": new_user_id}}
        )
        context.bot.send_message(chat_id=referer_id, text=f"🎉 New Referral! Total: {new_count}/10")
        
        # If user has completed 10 referrals, send premium link
        if new_count >= 10:
            context.bot.send_message(chat_id=referer_id, text="🎉 Congratulations! You've unlocked Free Premium Courses:",
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Premium", url=PREMIUM_LINK)]]))

def get_referral_count(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user.get("referral_count", 0) if user else 0

def create_progress_bar(count, total=10):
    return "🟩" * count + "⬜" * (total - count)

async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    if not is_user_joined(user_id):
        keyboard = [[InlineKeyboardButton(f"📌 Join Channel {i+1}", url=f"https://t.me/{str(CHANNELS[i])}") for i in range(len(CHANNELS))],
                    [InlineKeyboardButton("✅ Joined!", callback_data="check_join")]]
        await update.message.reply_text("⚠️ Please join the following channels to use the bot:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    await show_referral_message(update, context)

async def show_referral_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id
    add_user(user_id)
    
    referral_count = get_referral_count(user_id)
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    progress_bar = create_progress_bar(referral_count)
    
    message = (f"👋 Hello *{user.first_name}*!\n\n"
               "🌟 *Earn Free Premium Courses!*\n\n"
               "🎯 *Invite 10 friends* to get access to premium courses for free!\n\n"
               f"🔗 *Your Referral Link:* [{referral_link}]({referral_link})\n\n"
               f"📊 *Progress:* {progress_bar} ({referral_count}/10)")
    
    keyboard = [
        [InlineKeyboardButton("✅ Check Referrals", callback_data="check_referrals")],
        [InlineKeyboardButton("📤 Share Referral Link", url=f"https://t.me/share/url?url={referral_link}")]
    ]
    
    image_url = "https://i.imghippo.com/files/gDI9814XuE.jpg"
    await update.message.reply_photo(photo=image_url, caption=message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    if query.data == "check_join":
        if is_user_joined(user_id):
            await query.message.reply_text("✅ Thank you for joining! Now use /start to continue.")
        else:
            await query.message.reply_text("⚠️ Please join both channels to proceed!")
    elif query.data == "check_referrals":
        referral_count = get_referral_count(user_id)
        progress_bar = create_progress_bar(referral_count)
        await query.edit_message_text(text=f"📊 Your Progress: {progress_bar} ({referral_count}/10)", parse_mode="Markdown")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.run_polling()

if __name__ == '__main__':
    main()
