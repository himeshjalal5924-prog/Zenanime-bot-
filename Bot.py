import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Get token from environment variable
TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        param = context.args[0]

        if param == "welcome":
            await update.message.reply_text(
                "🔥 Welcome to ZenAnime!\n\nEnjoy latest anime updates!"
            )

        elif param == "episode1":
            await update.message.reply_text(
                "🎬 Here is Episode 1!\n\nWatch now: https://example.com"
            )

        elif param == "vip":
            keyboard = [
                [InlineKeyboardButton("💎 Join VIP Channel", url="https://t.me/YourChannel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "🌟 Welcome VIP User!",
                reply_markup=reply_markup
            )

        else:
            await update.message.reply_text("Unknown link parameter.")

    else:
        await update.message.reply_text(
            "👋 Hello! Welcome to ZenAnime Bot!"
        )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

print("Bot is running...")
app.run_polling()
