import asyncio
import json
import os
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAnimation,
)
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

API_TOKEN = "8502921605:AAFdjoB5rWKFfFGVXdehfaHV3DbSKp37NKk"
GROUP_ID = -1003277592312
CHANNEL_ID = "@yz_confession"

DATA_FILE = "nicknames.json"

bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# --- Load/Save Nicknames ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(user_nicknames, f, indent=2, ensure_ascii=False)

# --- Persistent storage ---
user_nicknames = load_data()
used_nicknames = set(user_nicknames.values())
user_states = {}
message_counter = 0

# --- Keyboards ---
def main_keyboard():
    kb = [
        [KeyboardButton(text="📝 New Confession")],
        [KeyboardButton(text="🎭 Change Nickname")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- Start Command ---
@dp.message(CommandStart())
async def start_handler(message: Message):
    user_id = str(message.from_user.id)
    nickname = user_nicknames.get(user_id)

    if not nickname:
        await message.answer(
            "Welcome!\nPlease choose a nickname first by pressing 🎭 Change Nickname.",
            reply_markup=main_keyboard(),
        )
    else:
        await message.answer(
            f"Welcome back, <b>{nickname}</b>!\n"
            "You can anonymously send confessions\n"
            "Choose an option below:",
            reply_markup=main_keyboard(),
        )

# --- Change Nickname ---
@dp.message(F.text == "🎭 Change Nickname")
async def change_nickname_prompt(message: Message):
    user_id = str(message.from_user.id)
    user_states[user_id] = "changing"
    await message.answer("Please send me your new nickname (must be unique and 1–20 characters):")

# --- New Confession ---
@dp.message(F.text == "📝 New Confession")
async def new_confession_prompt(message: Message):
    user_id = str(message.from_user.id)
    nickname = user_nicknames.get(user_id)

    if not nickname:
        await message.answer("❗ You must set a nickname first using 🎭 Change Nickname.")
        return

    user_states[user_id] = "writing"
    await message.answer("Please write your confession:")

# --- Handle text and media input ---
@dp.message(F.content_type.in_({"text", "photo", "video", "animation"}))
async def handle_confession(message: Message):
    global message_counter
    user_id = str(message.from_user.id)

    # Nickname changing state
    if user_states.get(user_id) == "changing" and message.text:
        text = message.text.strip()
        if not re.match(r"^[A-Za-z0-9_]{1,20}$", text):
            await message.answer("❌ Invalid nickname. Use only letters, numbers, or underscores (max 20 chars).")
            return
        if text in used_nicknames:
            await message.answer("❌ That nickname is already taken. Please choose another one:")
            return

        old = user_nicknames.get(user_id)
        if old in used_nicknames:
            used_nicknames.remove(old)

        user_nicknames[user_id] = text
        used_nicknames.add(text)
        user_states.pop(user_id, None)
        save_data()

        await message.answer(f"✅ Your nickname has been set to <b>{text}</b>.", reply_markup=main_keyboard())
        return

    # Confession writing state
    if user_states.get(user_id) == "writing":
        nickname = user_nicknames.get(user_id, "000")
        inline_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Accept", callback_data=f"accept:{user_id}"),
                    InlineKeyboardButton(text="❌ Decline", callback_data=f"decline:{user_id}"),
                ]
            ]
        )

        # --- Send different media types to moderation group ---
        caption = f"<b>New Confession:</b>\n\n"
        if message.caption:
            caption += f"{message.caption}\n\n"
        elif message.text:
            caption += f"{message.text}\n\n"
        caption += f"<b>Nickname:</b> {nickname}"

        if message.photo:
            await bot.send_photo(
                GROUP_ID,
                photo=message.photo[-1].file_id,
                caption=caption,
                reply_markup=inline_kb
            )
        elif message.video:
            await bot.send_video(
                GROUP_ID,
                video=message.video.file_id,
                caption=caption,
                reply_markup=inline_kb
            )
        elif message.animation:
            await bot.send_animation(
                GROUP_ID,
                animation=message.animation.file_id,
                caption=caption,
                reply_markup=inline_kb
            )
        else:
            await bot.send_message(GROUP_ID, caption, reply_markup=inline_kb)

        user_states.pop(user_id, None)
        await message.answer("Your confession has been sent for review. ✅")
        return

# --- Accept / Decline Handlers ---
@dp.callback_query(F.data.startswith("accept:"))
async def accept_confession(callback: types.CallbackQuery):
    global message_counter
    msg = callback.message
    await callback.answer("Accepted ✅")

    message_counter += 1
    msg_id = str(message_counter).zfill(7)

    # Use the existing caption/text from moderator message
    base_caption = (msg.caption or msg.text or "").strip()

    # Clean up: remove "New Confession:" prefix and extra blank lines
    cleaned_caption = re.sub(r"<b>New Confession:</b>\s*\n*", "", base_caption).strip()

    # Append message ID only (no duplicate nickname)
    final_caption = f"{cleaned_caption}\n<b>Message id:</b> {msg_id}"

    try:
        # Send the confession to the channel with media handling
        if msg.photo:
            await bot.send_photo(
                CHANNEL_ID,
                msg.photo[-1].file_id,
                caption=final_caption
            )
        elif msg.video:
            await bot.send_video(
                CHANNEL_ID,
                msg.video.file_id,
                caption=final_caption
            )
        elif msg.animation:  # GIF
            await bot.send_animation(
                CHANNEL_ID,
                msg.animation.file_id,
                caption=final_caption
            )
        else:
            await bot.send_message(CHANNEL_ID, final_caption)

        # Mark moderator message as accepted
        if msg.caption:
            await msg.edit_caption(base_caption + f"\n\n✅ Sent to channel as message id {msg_id}.")
        else:
            await msg.edit_text(base_caption + f"\n\n✅ Sent to channel as message id {msg_id}.")
    except Exception as e:
        print(f"Send error: {e}")


@dp.callback_query(F.data.startswith("decline:"))
async def decline_confession(callback: types.CallbackQuery):
    msg = callback.message
    await callback.answer("Declined ❌")

    if msg.caption and "Declined by moderator" in msg.caption:
        return
    if msg.text and "Declined by moderator" in msg.text:
        return

    try:
        if msg.caption:
            await msg.edit_caption(msg.caption + "\n\n❌ Declined by moderator.")
        else:
            await msg.edit_text(msg.text + "\n\n❌ Declined by moderator.")
    except Exception as e:
        if "message is not modified" not in str(e):
            print(f"Edit error: {e}")

# --- Run Bot ---
async def main():
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
