import os
import logging
from pymongo import MongoClient
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler

# Environment Variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MONGO_URI = os.getenv('MONGO_URI')
PREMIUM_LINK = os.getenv('PREMIUM_GROUP_LINK')

# Logging Setup
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Setup
client = MongoClient(MONGO_URI)
db = client.referral_bot
users_collection = db.users

# Function to add user safely
def add_user(user_id, referer_id=None):
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        users_collection.insert_one({
            "user_id": user_id,
            "referer_id": referer_id,
            "referral_count": 0,
            "referred_users": []
        })

# Function to update referral count safely
def update_referral_count(referer_id, new_user_id):
    referer = users_collection.find_one({"user_id": referer_id})
    if referer and new_user_id not in referer.get("referred_users", []):
        users_collection.update_one(
            {"user_id": referer_id},
            {"$inc": {"referral_count": 1}, "$push": {"referred_users": new_user_id}}
        )
        # Notify referer about new referral
        context.bot.send_message(
            chat_id=referer_id,
            text=f"🎉 **New Referral!** Aapke ek naye referral ne join kiya hai. Ab aapke total referrals: {referer['referral_count'] + 1}/4"
        )

# Function to get referral count
def get_referral_count(user_id):
    user = users_collection.find_one({"user_id": user_id})
    return user.get("referral_count", 0) if user else 0

# Function to create a progress bar
def create_progress_bar(count, total=4):
    filled = "🟩" * count
    empty = "⬜" * (total - count)
    return f"{filled}{empty}"

# Start Command
def start(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    args = context.args

    if args and args[0].isdigit():
        referer_id = int(args[0])
        if referer_id != user.id:
            add_user(user.id, referer_id)
            update_referral_count(referer_id, user.id)
    else:
        add_user(user.id)
    
    referral_link = f"https://t.me/{context.bot.username}?start={user.id}"
    referral_count = get_referral_count(user.id)
    progress_bar = create_progress_bar(referral_count)
    
    message = (
        f"👋 **Namaste {user.first_name}!**\n\n"
        "🌟 **Welcome to the Referral Program!**\n\n"
        "💡 **4 Referrals** complete karne par **Premium Group** ka access milega!\n\n"
        f"🔗 **Apka Referral Link:** [{referral_link}]({referral_link})\n\n"
        f"📊 **Aapke Referrals Progress:**\n{progress_bar} ({referral_count}/4)\n\n"
        "📢 **In Channels Ko Join Karna Na Bhoolein:**"
    )

    keyboard = [
        [InlineKeyboardButton("📌 Join Channel 1", url="https://t.me/skillwithgaurav")],
        [InlineKeyboardButton("📌 Join Channel 2", url="https://t.me/skillcoursesfree")],
        [InlineKeyboardButton("✅ Check Referrals", callback_data="check_referrals")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

    if referral_count >= 4:
        update.message.reply_text(
            f"🎉 **Congratulations!** Aapne 4 referrals complete kar liye hain. Yeh raha **Premium Group** ka link: {PREMIUM_LINK}"
        )

# Callback Query Handler
def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    referral_count = get_referral_count(user_id)
    progress_bar = create_progress_bar(referral_count)
    
    if query.data == "check_referrals":
        query.answer()
        query.edit_message_text(
            text=f"📊 **Aapke Referrals Progress:**\n{progress_bar} ({referral_count}/4)",
            parse_mode="Markdown"
        )

# Help Command
def help_command(update: Update, context: CallbackContext):
    help_text = (
        "❓ **How to Use This Bot:**\n\n"
        "1. Apna referral link share karein aur dosto ko invite karein.\n"
        "2. Jab bhi koi aapke referral link se join karega, aapka referral count badhega.\n"
        "3. **4 Referrals** complete karne par aapko premium group ka link milega.\n\n"
        "🛠 **Commands:**\n"
        "/start - Bot ko start karein aur apna referral link prapt karein.\n"
        "/help - Sahi istemal ka guide dekhein."
    )
    update.message.reply_text(help_text, parse_mode="Markdown")

# Error Handler
def error(update: Update, context: CallbackContext):
    logger.warning(f'Update {update} caused error {context.error}')

# Main Function
def main():
    updater = Updater(TOKEN)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda update, context: None))
    dispatcher.add_handler(CallbackQueryHandler(button_click))
    dispatcher.add_error_handler(error)
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
