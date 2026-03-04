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

# ==============================
# 🔐 ENV VARIABLES (RAILWAY)
# ==============================
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")
MONGO_URI = os.environ.get("MONGO_URI")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# ==============================
# 🗄 DATABASE SETUP
# ==============================
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["ZenAnimeBot"]
files_collection = db["files"]

# ==============================
# 🔔 FORCE JOIN CHECK
# ==============================
async def is_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Admin bypass
    if user_id == ADMIN_ID:
        return True

    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ==============================
# 🚀 START COMMAND
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # 👑 ADMIN VIEW
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "<b>👑 Admin Panel</b>\n\n"
            "• Send file to upload\n"
            "• /delete file_key → Delete file\n"
            "• /stats → View total files",
            parse_mode="HTML"
        )
        return

    # 👤 NORMAL USER VIEW
    joined = await is_user_joined(update, context)
    if not joined:
        keyboard = [[InlineKeyboardButton(
            "🔔 Join Channel",
            url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
        )]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚠️ You must join our channel to use this bot!",
            reply_markup=reply_markup,
        )
        return

    # If file link opened
    if context.args:
        file_key = context.args[0]
        file_data = await files_collection.find_one({"file_key": file_key})

        if file_data:
            msg = await update.message.reply_document(file_data["file_id"])

            # Auto delete after 2 minutes
            await asyncio.sleep(120)
            try:
                await msg.delete()
            except:
                pass
        else:
            await update.message.reply_text("❌ File not found.")
    else:
        await update.message.reply_text(
            "👋 Welcome! Click file link to download."
        )

# ==============================
# 📤 SAVE FILE (ADMIN ONLY)
# ==============================
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Only admin can upload files.")
        return

    # Detect file type
    if update.message.document:
        file = update.message.document
    elif update.message.video:
        file = update.message.video
    elif update.message.photo:
        file = update.message.photo[-1]
    else:
        return

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
        f"✅ File Saved Permanently!\n\n🔗 {link}"
    )

# ==============================
# 🗑 DELETE FILE (ADMIN ONLY)
# ==============================
async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not allowed.")
        return

    if not context.args:
        await update.message.reply_text("Usage:\n/delete file_key")
        return

    file_key = context.args[0]

    result = await files_collection.delete_one({"file_key": file_key})

    if result.deleted_count:
        await update.message.reply_text("✅ File deleted successfully.")
    else:
        await update.message.reply_text("❌ File not found.")

# ==============================
# 📊 STATS (ADMIN ONLY)
# ==============================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    total = await files_collection.count_documents({})
    await update.message.reply_text(f"📊 Total Files Stored: {total}")

# ==============================
# 🏗 BUILD APP
# ==============================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("delete", delete_file))
app.add_handler(CommandHandler("stats", stats))

app.add_handler(
    MessageHandler(
        filters.Document.ALL | filters.VIDEO | filters.PHOTO,
        save_file
    )
)

print("Bot is running...")
app.run_polling()
