import json
import os
import difflib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, Filters, CallbackContext
from keep_alive import keep_alive

# === Configuration ===
keep_alive()

TOKEN = '7932683981:AAFgYo_xLje6dIpMvNsBN4XRwpU677SValk'  # Replace with your bot token
ADMIN_ID = 1156299794     # Replace with your Telegram user ID
MOVIE_DB = 'movies.json'  # Local movie data file

# === Utilities ===

def load_movies():
    if not os.path.exists(MOVIE_DB):
        return {}
    with open(MOVIE_DB, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_movies(movies):
    with open(MOVIE_DB, 'w', encoding='utf-8') as f:
        json.dump(movies, f, indent=2, ensure_ascii=False)

def format_quality_label(q):
    return q.upper() if q.lower() in ['hd', 'sd'] else q.capitalize()

# === Bot Command Handlers ===

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "🎬 *Welcome to the Movie Bot!*\n\n"
        "Use `/get Movie Name` to search.\n"
        "Admins can add movies with:\n"
        "`/add Title | ImageURL | FileSize | Year | 720p:link,1080p:link,...`",
        parse_mode='Markdown')

def add_movie(update: Update, context: CallbackContext):
    if update.effective_user.id != ADMIN_ID:
        update.message.reply_text("🚫 You are not authorized to add movies.")
        return

    try:
        args = update.message.text.split(' ', 1)[1]
        parts = args.split('|')
        if len(parts) != 5:
            raise ValueError

        title, image, size, year, quality_block = [p.strip() for p in parts]
        quality_links = {}

        for q in quality_block.split(','):
            if ':' in q:
                quality, link = q.split(':', 1)
                quality_links[quality.strip().lower()] = link.strip()

        if not quality_links:
            update.message.reply_text("❗ No valid quality links provided.")
            return

        title_key = f"{title.strip()} ({year.strip()})".lower()
        movies = load_movies()
        movies[title_key] = {
            'title': title.strip(),
            'image': image,
            'size': size,
            'year': year,
            'links': quality_links
        }
        save_movies(movies)
        update.message.reply_text(
            f"✅ Movie *'{title}'* ({year}) added with {len(quality_links)} links.",
            parse_mode="Markdown")
    except Exception:
        update.message.reply_text(
            "❗ Usage:\n"
            "/add Title | ImageURL | FileSize | Year | 720p:link,1080p:link,..."
        )

def get_movie(update: Update, context: CallbackContext):
    if len(context.args) == 0:
        update.message.reply_text("❗ Usage: `/get Movie Name`", parse_mode="Markdown")
        return

    query = " ".join(context.args).lower()
    movies = load_movies()

    matches = [key for key in movies if query in key.lower() or query in movies[key]['title'].lower()]

    if not matches:
        update.message.reply_text("❌ No movie found. Try a different name.")
    elif len(matches) == 1:
        send_movie(update, context, movies[matches[0]])
    else:
        keyboard = [[
            InlineKeyboardButton(f"{movies[m]['title']} ({movies[m].get('year', 'Unknown')})",
                                 callback_data=f"choose::{m}")
        ] for m in matches]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "🎯 Multiple matches found. Please choose one:",
            reply_markup=reply_markup)

def send_movie(update: Update, context: CallbackContext, movie):
    keyboard = [[
        InlineKeyboardButton(f"🎥 Download {format_quality_label(q)}", url=link)
    ] for q, link in movie["links"].items()]
    reply_markup = InlineKeyboardMarkup(keyboard)

    caption = (f"🎬 *{movie['title']}*\n"
               f"📅 Release: {movie.get('year', 'Unknown')}\n"
               f"📦 Size: {movie['size']}")

    if update.callback_query:
        update.callback_query.answer()
        update.callback_query.edit_message_text("✅ Loading movie details...")
        context.bot.send_photo(chat_id=update.effective_chat.id,
                               photo=movie["image"],
                               caption=caption,
                               parse_mode="Markdown",
                               reply_markup=reply_markup)
    else:
        update.message.reply_photo(photo=movie["image"],
                                   caption=caption,
                                   parse_mode="Markdown",
                                   reply_markup=reply_markup)

def handle_callback(update: Update, context: CallbackContext):
    query_data = update.callback_query.data
    if query_data.startswith("choose::"):
        key = query_data.split("::")[1]
        movies = load_movies()
        movie = movies.get(key)
        if movie:
            send_movie(update, context, movie)

def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text("❓ Unknown command. Use `/get Movie Name`", parse_mode="Markdown")

# === Main ===

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    print(f"🤖 Movie Bot is running as @{updater.bot.get_me().username}")

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("add", add_movie))
    dp.add_handler(CommandHandler("get", get_movie))
    dp.add_handler(CallbackQueryHandler(handle_callback))
    dp.add_handler(MessageHandler(Filters.command, unknown_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, lambda u, c: None))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
