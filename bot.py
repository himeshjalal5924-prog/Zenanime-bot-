import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from motor.motor_asyncio import AsyncIOMotorClient

# Environment Variables
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")
MONGO_URI = os.environ.get("MONGO_URI")

# MongoDB Setup
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["ZenAnimeBot"]
files_collection = db["files"]

# Force Join Check
async def is_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await is_user_joined(update, context)
    if not joined:
        keyboard = [[InlineKeyboardButton("🔔 Join Channel",
                    url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚠️ You must join our channel to use this bot!",
            reply_markup=reply_markup,
        )
        return

    if context.args:
        file_key = context.args[0]
        file_data = await files_collection.find_one({"file_key": file_key})

        if file_data:
            msg = await update.message.reply_document(file_data["file_id"])

            # Auto delete after 2 minutes
            await asyncio.sleep(120)
            await msg.delete()
        else:
            await update.message.reply_text("❌ File not found.")
    else:
        await update.message.reply_text("👋 Send me a file to generate permanent link!")

# Save File
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await is_user_joined(update, context)
    if not joined:
        await update.message.reply_text("⚠️ Join channel first!")
        return

    file = update.message.document or update.message.video
    file_id = file.file_id

    file_key = str(file.file_unique_id)

    # Save in MongoDB
    await files_collection.insert_one({
        "file_key": file_key,
        "file_id": file_id
    })

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={file_key}"

    await update.message.reply_text(
        f"✅ File Saved Permanently!\n\n🔗 Shareable Link:\n{link}"
    )

# Build App
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.ALL | filters.VIDEO, save_file))

print("Bot is running...")
app.run_polling()
