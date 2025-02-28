import os
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Bot Token (Environment variable se lena hoga)
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# MongoDB connection string (Environment variable se lena hoga)
MONGO_URI = os.getenv('MONGO_URI')

# Premium group invite link (Environment variable se lena hoga)
PREMIUM_LINK = os.getenv('PREMIUM_LINK')

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
            "referal_count": 0
        })

# Update referal count
def update_referal_count(referer_id):
    users_collection.update_one(
        {"user_id": referer_id},
        {"$inc": {"referal_count": 1}}
    )

# Get referal count
def get_referal_count(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user.get("referal_count", 0) if user else 0

# Start command
def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    args = context.args

    # Check if user is coming from a referal link
    if args and args[0].isdigit():
        referer_id = int(args[0])
        add_user(user.id, referer_id)
        update_referal_count(referer_id)
    else:
        add_user(user.id)

    referal_link = f"https://t.me/{context.bot.username}?start={user.id}"
    referal_count = get_referal_count(user.id)

    message = (
        f"Namaste {user.first_name}!\n\n"
        "5+ Premium Courses ko unlock karne ke liye, apne referal link ko 10 logo ke sath share karein:\n\n"
        f"📌 Apna Referal Link: {referal_link}\n\n"
        f"✅ Abhi tak {referal_count} logo ne apka link use kiya hai.\n\n"
        "Aur niche diye gaye channels mein bhi join karein:"
    )

    # Channels ke buttons
    keyboard = [
        [InlineKeyboardButton("Channel 1", url="https://t.me/skillcoursesfree")],
        [InlineKeyboardButton("Channel 2", url="https://t.me/skillwithgaurav")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(message, reply_markup=reply_markup)

    # Check if user has 10+ referals
    if referal_count >= 10:
        premium_message = (
            "Congratulations! 🎉 Aapne 10+ logo ko apna referal link share kiya hai.\n\n"
            "Yeh raha aapka premium group ka invite link:\n\n"
            f"👉 {https://t.me/+ZvQhHzGFBS80NjJl}"
        )
        update.message.reply_text(premium_message)

# Error handling
def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

# Main function
def main() -> None:
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start))

    # Error handler
    dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
