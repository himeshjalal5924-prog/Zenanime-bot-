import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from motor.motor_asyncio import AsyncIOMotorClient

# ==============================
# 🔐 ENV VARIABLES
# ==============================
TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_USERNAME = os.environ.get("CHANNEL_USERNAME")
MONGO_URI = os.environ.get("MONGO_URI")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

# ==============================
# 🗄 DATABASE
# ==============================
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["ZenAnimeBot"]
files_collection = db["files"]
settings_collection = db["settings"]

DEFAULT_EXPIRY = 120

# ==============================
# 🔔 FORCE JOIN
# ==============================
async def is_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        return True

    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ==============================
# 📂 GENERATE FILE LIST (REUSABLE)
# ==============================
async def generate_file_list():
    cursor = files_collection.find().limit(20)
    keyboard = []

    async for f in cursor:
        name = f.get("file_name", "Unknown")
        key = f.get("file_key")

        keyboard.append([
            InlineKeyboardButton(f"📥 {name}", callback_data=f"get_{key}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"del_{key}")
        ])

    return InlineKeyboardMarkup(keyboard)

# ==============================
# 🚀 START
# ==============================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id == ADMIN_ID:
        await update.message.reply_text(
            "<b>👑 Admin Panel</b>\n\n"
            "• Send file to upload\n"
            "• /files → View files UI\n"
            "• /delete file_key\n"
            "• /stats\n"
            "• /settime seconds",
            parse_mode="HTML"
        )
        return

    joined = await is_user_joined(update, context)
    if not joined:
        keyboard = [[InlineKeyboardButton(
            "🔔 Join Channel",
            url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}"
        )]]
        await update.message.reply_text(
            "⚠️ Join channel first!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text("👋 Welcome!")

# ==============================
# 📤 SAVE FILE (ADMIN)
# ==============================
async def save_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.document:
        file = update.message.document
        file_name = file.file_name
    elif update.message.video:
        file = update.message.video
        file_name = "Video File"
    elif update.message.photo:
        file = update.message.photo[-1]
        file_name = "Photo"
    else:
        return

    file_id = file.file_id
    file_key = str(file.file_unique_id)

    setting = await settings_collection.find_one({"type": "expiry"})
    expiry_time = setting["seconds"] if setting else DEFAULT_EXPIRY

    await files_collection.insert_one({
        "file_key": file_key,
        "file_id": file_id,
        "file_name": file_name,
        "expiry": expiry_time
    })

    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={file_key}"

    await update.message.reply_text(
        f"✅ Saved: {file_name}\n⏳ Expiry: {expiry_time}s\n🔗 {link}"
    )

# ==============================
# 📂 FILE LIST
# ==============================
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Not allowed.")
        return

    reply_markup = await generate_file_list()

    if not reply_markup.inline_keyboard:
        await update.message.reply_text("No files found.")
        return

    await update.message.reply_text("📂 Your Files:", reply_markup=reply_markup)

# ==============================
# 🎯 BUTTON HANDLER
# ==============================
async def file_button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()
    data = query.data

    # 📥 GET FILE
    if data.startswith("get_"):
        file_key = data.split("_")[1]

        file_data = await files_collection.find_one({"file_key": file_key})

        if file_data:
            msg = await query.message.reply_document(
                file_data["file_id"],
                caption=f"🔑 `{file_key}`",
                parse_mode="Markdown"
            )

            expiry = file_data.get("expiry", DEFAULT_EXPIRY)
            await asyncio.sleep(expiry)

            try:
                await msg.delete()
            except:
                pass

        else:
            await query.message.reply_text("❌ File not found.")

    # 🗑 ASK CONFIRM
    elif data.startswith("del_"):
        file_key = data.split("_")[1]

        if query.from_user.id != ADMIN_ID:
            return

        file_data = await files_collection.find_one({"file_key": file_key})
        name = file_data.get("file_name", "Unknown") if file_data else "Unknown"

        keyboard = [[
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{file_key}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]]

        await query.message.reply_text(
            f"⚠️ Delete this file?\n\n📄 {name}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ✅ CONFIRM DELETE
    elif data.startswith("confirm_"):
        file_key = data.split("_")[1]

        if query.from_user.id != ADMIN_ID:
            return

        result = await files_collection.delete_one({"file_key": file_key})

        if result.deleted_count:
            await query.message.reply_text("🗑 Deleted!")

            # 🔄 Refresh list
            reply_markup = await generate_file_list()

            if reply_markup.inline_keyboard:
                await query.message.reply_text("📂 Updated Files:", reply_markup=reply_markup)
            else:
                await query.message.reply_text("📂 No files remaining.")

        else:
            await query.message.reply_text("❌ Not found")

    # ❌ CANCEL
    elif data == "cancel":
        await query.message.reply_text("❌ Cancelled")

# ==============================
# ⏳ SET TIME
# ==============================
async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    try:
        seconds = int(context.args[0])

        await settings_collection.update_one(
            {"type": "expiry"},
            {"$set": {"seconds": seconds}},
            upsert=True
        )

        await update.message.reply_text(f"✅ Expiry set to {seconds}s")
    except:
        await update.message.reply_text("❌ Usage: /settime 300")

# ==============================
# 📊 STATS
# ==============================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    total = await files_collection.count_documents({})
    await update.message.reply_text(f"📊 Total files: {total}")

# ==============================
# 🏗 BUILD
# ==============================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("files", list_files))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("settime", set_time))

app.add_handler(CallbackQueryHandler(file_button))

app.add_handler(
    MessageHandler(
        filters.Document.ALL | filters.VIDEO | filters.PHOTO,
        save_file
    )
)

print("Bot running...")
app.run_polling()
