from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 🔑 Replace with your Bot Token from BotFather
import os
TOKEN = os.environ.get("8737135652:AAFIsgZX5d3oL77KtcQTCSZ6jP3D2ZUgGWM")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        param = context.args[0]

        # If user clicks: ?start=welcome
        if param == "welcome":
            await update.message.reply_text(
                "🔥 Welcome to ZenAnime!\n\nEnjoy latest anime updates and episodes!"
            )

        # If user clicks: ?start=episode1
        elif param == "episode1":
            await update.message.reply_text(
                "🎬 Here is Episode 1!\n\nWatch now: https://example.com"
            )

        # If user clicks: ?start=vip
        elif param == "vip":
            keyboard = [
                [InlineKeyboardButton("💎 Join VIP Channel", url="https://t.me/YourChannel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                "🌟 Welcome VIP User!\nClick below to join premium anime channel.",
                reply_markup=reply_markup
            )

        else:
            await update.message.reply_text("Unknown link parameter.")

    else:
        await update.message.reply_text(
            "👋 Hello! Welcome to ZenAnime Bot.\nClick special links to get anime content!"
        )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

print("Bot is running...")
app.run_polling()
