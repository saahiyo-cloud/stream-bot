from hydrogram import Client, filters
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from bot.database.db import db
from bot.config import Config
from bot.utils import human_readable_size


def get_start_buttons():
    first_row = []
    if Config.UPDATES_CHANNEL:
        first_row.append(InlineKeyboardButton("🛠 Updates Channel", url=f"https://t.me/{Config.UPDATES_CHANNEL.lstrip('@')}"))
    first_row.append(InlineKeyboardButton("📖 Help", callback_data="help_data"))

    return [
        first_row,
        [InlineKeyboardButton("ℹ️ About", callback_data="about_data")]
    ]


@Client.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    user = message.from_user
    if user:
        await db.add_user(user.id, user.first_name, user.username or "")

    text = (
        f"👋 **Hello {message.from_user.mention if message.from_user else 'there'}!**\n\n"
        "⚡ I am a high-speed **Telegram File to Stream & Direct Download Link Bot**.\n\n"
        "📤 **Send or forward me any file, video, audio, or document**, and I will instantly generate:\n"
        "• 🎬 **Fast Web Video Stream Link** (with Range & Seek support)\n"
        "• 📥 **Direct Download Link** (ultra-fast multi-chunk acceleration)\n\n"
        "Try sending a file now!"
    )

    await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(get_start_buttons()),
        disable_web_page_preview=True
    )


@Client.on_message(filters.command("help") & filters.private)
async def help_handler(client: Client, message: Message):
    text = (
        "📖 **How to Use This Bot:**\n\n"
        "1. **Send or forward any media** (Video, Document, Audio, GIF, Photo) to this bot.\n"
        "2. The bot will automatically upload it to the cloud streaming server.\n"
        "3. You will receive an instant **Stream Link** and a **Direct Download Link**.\n"
        "4. Click **🚀 Download Now** to download or open the **🎬 Stream Link** to watch online in browser/VLC/MX Player without downloading.\n\n"
        "⚡ **Features:**\n"
        "• Direct RAM MTProto chunk streaming (no server disk limit)\n"
        "• Video seek & scrub support (HTTP 206 Partial Content)\n"
        "• Multi-client bandwidth acceleration"
    )

    buttons = [
        [InlineKeyboardButton("🔙 Back", callback_data="start_data")]
    ]

    await message.reply_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@Client.on_message(filters.command("stats") & filters.private)
async def stats_handler(client: Client, message: Message):
    stats = await db.get_stats()
    text = (
        "📊 **Bot System Statistics:**\n\n"
        f"📁 **Total Files Streamed:** `{stats['total_files']}`\n"
        f"👥 **Total Active Users:** `{stats['total_users']}`\n"
        f"📦 **Total Data Indexed:** `{human_readable_size(stats['total_size'])}`\n"
        f"⚡ **Multi-Client Pool:** `{len(Config.MULTI_TOKENS) + 1} Active Clients`"
    )
    await message.reply_text(text)


@Client.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    data = query.data

    if data == "start_data":
        text = (
            f"👋 **Hello {query.from_user.mention}!**\n\n"
            "⚡ I am a high-speed **Telegram File to Stream & Direct Download Link Bot**.\n\n"
            "📤 **Send or forward me any file, video, audio, or document**, and I will instantly generate:\n"
            "• 🎬 **Fast Web Video Stream Link**\n"
            "• 📥 **Direct Download Link**\n\n"
            "Try sending a file now!"
        )
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(get_start_buttons()))

    elif data == "help_data":
        text = (
            "📖 **How to Use This Bot:**\n\n"
            "1. **Send or forward any media** (Video, Document, Audio, GIF, Photo) to this bot.\n"
            "2. The bot will automatically process it.\n"
            "3. You will receive an instant **Stream Link** and a **Direct Download Link**.\n"
            "4. Open the link in browser, VLC, or MX Player to stream instantly!"
        )
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="start_data")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "about_data":
        channel_info = f"\n• **Channel:** {Config.UPDATES_CHANNEL}" if Config.UPDATES_CHANNEL else ""
        text = (
            "ℹ️ **About This Bot:**\n\n"
            "• **Name:** High-Speed Stream & Download Bot ⚡\n"
            "• **Engine:** Hydrogram MTProto & Async aiohttp Server\n"
            "• **Protocol:** HTTP 206 Partial Content (Byte-Range Streaming)\n"
            "• **Proxy:** Cloudflare Workers Edge CDN"
            f"{channel_info}"
        )
        buttons = [[InlineKeyboardButton("🔙 Back", callback_data="start_data")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "local_note":
        await query.answer("Click the stream or download link directly in the message text to open it in your browser!", show_alert=True)

    elif data == "close_data":
        await query.message.delete()
