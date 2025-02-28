import os
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext

# Bot Token (Environment variable se lena hoga)
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# MongoDB connection string (Environment variable se lena hoga)
MONGO_URI = os.getenv('MONGO_URI')

# Premium group invite link (Environment variable se lena hoga)
PREMIUM_LINK = os.getenv('https://t.me/+ZvQhHzGFBS80NjJl')

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client.referal_bot
users_collection = db.users

# Add user to database
def add_user(user_id, referer_id=None):
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({
            "user_id": user_id,
            "referer_id": referer_id,
            "referal_count": 0,
            "referred_users": []  # Track referred users to avoid duplicate counts
        })

# Update referral count
def update_referal_count(referer_id, new_user_id):
    referer = users_collection.find_one({"user_id": referer_id})
    if referer and new_user_id not in referer.get("referred_users", []):
        users_collection.update_one(
            {"user_id": referer_id},
            {"$inc": {"referal_count": 1}, "$push": {"referred_users": new_user_id}}
        )

# Get referral count
def get_referal_count(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user.get("referal_count", 0) if user else 0

# Start command
def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    args = context.args

    if args and args[0].isdigit():
        referer_id = int(args[0])
        if referer_id != user.id:  # Self-referral prevention
            add_user(user.id, referer_id)
            update_referal_count(referer_id, user.id)
    else:
        add_user(user.id)

    referal_link = f"https://t.me/{context.bot.username}?start={user.id}"
    referal_count = get_referal_count(user.id)

    message = (
        f"\U0001F44B Namaste {user.first_name}!\n\n"
        "\U0001F4A1 5+ Premium Courses unlock karne ke liye, apne referral link ko 10 logo ke sath share karein:\n\n"
        f"\U0001F517 Apka Referral Link: {referal_link}\n\n"
        f"✅ Aapke {referal_count} valid referrals ho chuke hain.\n\n"
        "Aur niche diye gaye channels mein bhi join karein:"
    )

    # Channels ke buttons
    keyboard = [
        [InlineKeyboardButton("\U0001F4E2 Channel 1", url="https://t.me/skillcoursesfree")],
        [InlineKeyboardButton("\U0001F4E2 Channel 2", url="https://t.me/skillwithgaurav")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(message, reply_markup=reply_markup)

    if referal_count >= 10:
        premium_message = (
            "\U0001F389 Congratulations! Aapne 10+ logo ko invite kar diya hai.\n\n"
            "\U0001F449 Yeh raha aapka premium group ka invite link:\n\n"
            f"🔗 {https://t.me/+ZvQhHzGFBS80NjJl}"
        )
        update.message.reply_text(premium_message)

# Error handling
def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

# Main function
def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
