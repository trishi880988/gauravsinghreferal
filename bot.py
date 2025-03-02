import os
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
import requests

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
PREMIUM_LINK = os.getenv('PREMIUM_GROUP_LINK')

# Add your channel IDs here (not usernames)
CHANNELS = [
    -1002390829801,  # Replace with your first channel ID
    -1002364162931   # Replace with your second channel ID
]

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
        users_collection.update_one(
            {"user_id": referer_id},
            {"$inc": {"referral_count": 1}, "$push": {"referred_users": new_user_id}}
        )
        context.bot.send_message(chat_id=referer_id, text=f"🎉 New Referral! Total: {referer['referral_count'] + 1}/4")

def get_referral_count(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user.get("referral_count", 0) if user else 0

def create_progress_bar(count, total=4):
    return "🟩" * count + "⬜" * (total - count)

async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    if not is_user_joined(user_id):
        keyboard = [[InlineKeyboardButton(f"📌 Join Channel {i+1}", url=f"https://t.me/c/{str(CHANNELS[i])[4:]}") for i in range(len(CHANNELS))],
                    [InlineKeyboardButton("✅ Joined!", callback_data="check_join")]]
        await update.message.reply_text("⚠️ Please join the following channels to use the bot:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    args = context.args
    if args and args[0].isdigit():
        referer_id = int(args[0])
        if referer_id != user_id:
            add_user(user_id, referer_id)
            update_referral_count(referer_id, user_id, context)
    else:
        add_user(user_id)

    referral_count = get_referral_count(user_id)
    referral_link = f"https://t.me/{context.bot.username}?start={user_id}"
    progress_bar = create_progress_bar(referral_count)

    message = f"👋 Hello *{user.first_name}*!\n\n🌟 *Earn Premium Access!*\n\n🔗 *Your Referral Link:* [{referral_link}]({referral_link})\n\n📊 *Progress:* {progress_bar} ({referral_count}/4)"
    keyboard = [
        [InlineKeyboardButton("✅ Check Referrals", callback_data="check_referrals")],
        [InlineKeyboardButton("📤 Share Referral Link", url=f"https://t.me/share/url?url={referral_link}")]
    ]
    
    await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    if referral_count >= 4:
        await update.message.reply_text("🎉 Congratulations! You've unlocked Premium Access:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Premium", url=PREMIUM_LINK)]]))

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
        await query.edit_message_text(text=f"📊 Your Progress: {progress_bar} ({referral_count}/4)", parse_mode="Markdown")

def main():
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.run_polling()

if __name__ == '__main__':
    main()
