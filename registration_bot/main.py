import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# ---------------- BOT CONFIGURATION ----------------
BOT_TOKEN = "8235468495:AAG5XudwqBUQ5vH8N4ZV0U-FXyUYyUM_VoY"
GROUP_ID = -1003202502098  # Telegram group ID

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)

# ---------------- STATE MACHINE ----------------
class Registration(StatesGroup):
    role = State()
    full_name = State()
    phone_number = State()
    room_number = State()
    timetable_photo = State()  # New step for timetable upload

# ---------------- JSON HANDLING ----------------
FILE_NAME = "registration.json"


def load_data():
    if not os.path.exists(FILE_NAME):
        with open(FILE_NAME, "w") as f:
            json.dump({"teachers": [], "students": [], "messages": {}}, f)
    else:
        # File exists — check if empty or invalid
        try:
            with open(FILE_NAME, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, ValueError):
            # Reset corrupted or empty file
            data = {"teachers": [], "students": [], "messages": {}}
            with open(FILE_NAME, "w") as f:
                json.dump(data, f)
        return data

    # Default return if file just created
    with open(FILE_NAME, "r") as f:
        return json.load(f)


def save_data(data):
    with open(FILE_NAME, "w") as f:
        json.dump(data, f, indent=4)


# ---------------- GROUP MESSAGE MANAGEMENT ----------------
async def ensure_group_messages():
    """Ensure the main Teachers/Students messages exist and save their IDs."""
    data = load_data()
    if "messages" not in data:
        data["messages"] = {}

    msg_data = data["messages"]

    # Ensure Teachers message exists
    if "teachers" not in msg_data or not msg_data["teachers"]:
        msg = await bot.send_message(GROUP_ID, "🧑‍🏫 <b>Teachers</b>\nNo teachers registered yet.")
        msg_data["teachers"] = msg.message_id

    # Ensure Students message exists
    if "students" not in msg_data or not msg_data["students"]:
        msg = await bot.send_message(GROUP_ID, "🎹 <b>Students</b>\nNo students registered yet.")
        msg_data["students"] = msg.message_id

    data["messages"] = msg_data
    save_data(data)


async def update_group_messages(role: str):
    """Edit the Teachers or Students message instead of sending a new one."""
    data = load_data()
    msg_data = data.get("messages", {})

    if role == "teacher":
        text = "🧑‍🏫 <b>Teachers</b>\n"
        for t in data["teachers"]:
            text += f"{t['room_number']} — {t['full_name']} — {t['phone_number']}\n"
        if not data["teachers"]:
            text += "No teachers registered yet."

        msg_id = msg_data.get("teachers")
        if msg_id:
            try:
                await bot.edit_message_text(chat_id=GROUP_ID, message_id=msg_id, text=text)
            except Exception as e:
                print(f"[WARN] Could not edit Teachers message: {e}")
                msg = await bot.send_message(GROUP_ID, text)
                msg_data["teachers"] = msg.message_id
        else:
            msg = await bot.send_message(GROUP_ID, text)
            msg_data["teachers"] = msg.message_id

    elif role == "student":
        text = "🎹 <b>Students</b>\n"
        for s in data["students"]:
            text += f"{s['room_number']} — {s['full_name']} — {s['phone_number']}\n"
        if not data["students"]:
            text += "No students registered yet."

        msg_id = msg_data.get("students")
        if msg_id:
            try:
                await bot.edit_message_text(chat_id=GROUP_ID, message_id=msg_id, text=text)
            except Exception as e:
                print(f"[WARN] Could not edit Students message: {e}")
                msg = await bot.send_message(GROUP_ID, text)
                msg_data["students"] = msg.message_id
        else:
            msg = await bot.send_message(GROUP_ID, text)
            msg_data["students"] = msg.message_id

    data["messages"] = msg_data
    save_data(data)


# ---------------- HANDLERS ----------------
@router.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧑‍🏫 Teacher", callback_data="teacher")],
        [InlineKeyboardButton(text="🎹 Student", callback_data="student")]
    ])

    await message.answer(
        f"Hello {message.from_user.first_name}! 👋\nWelcome to the Piano Course Registration Bot.\nPlease choose your role:",
        reply_markup=kb
    )
    await state.set_state(Registration.role)


@router.callback_query(F.data.in_({"teacher", "student"}))
async def choose_role(callback: types.CallbackQuery, state: FSMContext):
    role = callback.data
    await state.update_data(role=role)
    await callback.message.answer("Please enter your full name:")
    await state.set_state(Registration.full_name)


@router.message(Registration.full_name)
async def get_full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    contact_btn = KeyboardButton(text="📱 Share Phone Number", request_contact=True)
    kb = ReplyKeyboardMarkup(keyboard=[[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
    await message.answer("Please share your phone number:", reply_markup=kb)
    await state.set_state(Registration.phone_number)


@router.message(Registration.phone_number, F.contact)
async def get_phone_number(message: types.Message, state: FSMContext):
    await state.update_data(phone_number=message.contact.phone_number)
    await message.answer("Please enter your room number (format 201A/B):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Registration.room_number)


@router.message(Registration.room_number)
async def get_room_number(message: types.Message, state: FSMContext):
    await state.update_data(room_number=message.text)
    await message.answer("Please send a screenshot of your timetable (from Intranet). 📅\n\n"
                         "This will help us choose the best lesson time for you.")
    await state.set_state(Registration.timetable_photo)


@router.message(Registration.timetable_photo, F.photo)
async def get_timetable_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id  # Use compressed version
    await state.update_data(timetable_photo=photo_id)

    user_data = await state.get_data()
    role = user_data["role"]

    entry = {
        "full_name": user_data["full_name"],
        "phone_number": user_data["phone_number"],
        "room_number": user_data["room_number"],
        "telegram_id": message.from_user.id,
        "telegram_name": message.from_user.full_name,
        "telegram_username": message.from_user.username or "N/A",
        "timetable_photo": photo_id
    }

    data = load_data()
    data[f"{role}s"].append(entry)
    save_data(data)

    # Update the group’s main message first
    await update_group_messages(role)

    # Then send the log entry with photo
    caption = (
        f"📋 <b>New {role.capitalize()} Registered!</b>\n\n"
        f"Room Number: {entry['room_number']}\n"
        f"Full Name: {entry['full_name']}\n"
        f"Phone Number: {entry['phone_number']}\n"
        f"Telegram Account Name: {entry['telegram_name']}\n"
        f"Telegram Account ID: <code>{entry['telegram_id']}</code>\n"
        f"Telegram Username: @{entry['telegram_username'] if entry['telegram_username'] != 'N/A' else '-'}"
    )

    await bot.send_photo(GROUP_ID, photo=photo_id, caption=caption)
    await message.answer("✅ Registration is complete! We will contact you soon with further details.")
    await state.clear()


@router.message(Command("getid"))
async def get_id(message: types.Message):
    await message.answer(f"Chat ID: <code>{message.chat.id}</code>")


# ---------------- RUN BOT ----------------
if __name__ == "__main__":
    import asyncio

    async def main():
        await ensure_group_messages()
        await dp.start_polling(bot)

    asyncio.run(main())
