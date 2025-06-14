import base64
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import StateFilter
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
from uuid import uuid4
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiohttp
from aiogram.filters import CommandStart
from config import BOT_TOKEN,  DEFAULT_LANGUAGE, ADMIN_ID
from database import (
    add_user, delete_movie, get_all_movies, get_language, search_movies, add_movie, get_all_users,
    get_movie_by_id, get_total_users_count, get_total_movies_count, update_movie_title
)

import asyncio

logging.basicConfig(level=logging.INFO)

BOT_USERNAME = "koronashops_bot"  # bu yerga botingiz username'ini yozing

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

DEFAULT_THUMB_URL = "https://i.ibb.co/XXXXXX/default.jpg"
# --- FSM States ---

class AddMovieState(StatesGroup):
    choosing_type = State()
    entering_title = State()
    entering_description = State()
    choosing_genre = State()
    choosing_year = State()
    choosing_duration = State()
    choosing_rating = State()
    uploading_video = State()
    uploading_poster = State()
    confirming = State()


class BroadcastStates(StatesGroup):
    waiting_for_broadcast_text = State()


class EditMovieStates(StatesGroup):
    waiting_for_movie_id = State()
    waiting_for_new_title = State()

class DeleteMovieStates(StatesGroup):
    waiting_for_movie_id = State()
# --- Keyboards ---
class EditState(StatesGroup):
    title = State()



def search_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Kino izlash", switch_inline_query_current_chat="")]
    ])


def type_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎬 Kino", callback_data="type_movie"),
                InlineKeyboardButton(text="📺 Serial", callback_data="type_serial"),
                InlineKeyboardButton(text="🎞 Multfilm", callback_data="type_cartoon"),
            ]
        ]
    )


def genre_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧨 Action", callback_data="genre_Action")],
            [InlineKeyboardButton(text="😂 Comedy", callback_data="genre_Comedy")],
            [InlineKeyboardButton(text="😢 Drama", callback_data="genre_Drama")],
        ]
    )


def year_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="2022", callback_data="year_2022"),
                InlineKeyboardButton(text="2023", callback_data="year_2023"),
                InlineKeyboardButton(text="2024", callback_data="year_2024"),
            ],
        ]
    )


def duration_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="90 min", callback_data="duration_90"),
                InlineKeyboardButton(text="120 min", callback_data="duration_120"),
            ],
        ]
    )


def rating_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐️ 7", callback_data="rating_7"),
                InlineKeyboardButton(text="⭐️ 8", callback_data="rating_8"),
                InlineKeyboardButton(text="⭐️ 9", callback_data="rating_9"),
            ],
        ]
    )


def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
            ],
        ]
    )




# --- Handlers ---


@router.message(lambda msg: msg.text and msg.text.startswith("/start movie_"))
async def start_movie_handler(msg: Message, state: FSMContext):
    try:
        movie_id = int(msg.text.split("_", 1)[1])
        movie = await get_movie_by_id(movie_id)
        if not movie:
            return await msg.answer("❌ Kino topilmadi.")

        # Ma'lumotlarni ajratib olish
        title = movie.get("title_uz", "Noma’lum nom")
        year = movie.get("year", "Noma’lum yil")
        genre = movie.get("genre", "Noma’lum janr")
        description = movie.get("description", "Tavsif mavjud emas")
        rating = movie.get("rating", "Noma’lum")


        caption = (
            f"🎬 <b>{title}</b> ({year})\n"
            f"⭐ Reyting: {rating}/10\n"
            f"🎭 Janr: {genre}\n"
            f"📝 <i>{description}</i>"
        )

        return await msg.answer_video(
            video=movie['file_id'],
            caption=caption,
            parse_mode="HTML"
        )
    except:
        return await msg.answer("❌ Noto‘g‘ri kino ID.")


# Faqatgina /start uchun
@router.message(CommandStart())
async def start_handler(msg: Message, state: FSMContext):
    await add_user(msg.from_user.id)
    banner_url = "https://i.ibb.co/JgzzxJQ/photo-2025-06-11-11-18-03.jpg"
    await msg.answer_photo(
        photo=banner_url,
        caption="👋 <b>Xush kelibsiz!</b>\n\n🔍 Kino izlash uchun pastga film nomini yozing.",
        parse_mode="HTML",
        reply_markup=search_keyboard()
    )


# Callback orqali kino yuborish
@router.callback_query(F.data.startswith("movie_"))
async def send_selected_movie(callback: CallbackQuery, state: FSMContext):
    movie_id = int(callback.data.split("_", 1)[1])
    movie = await get_movie_by_id(movie_id)
    if not movie:
        await callback.message.answer("Kino topilmadi.")
        return

    await callback.message.answer_chat_action("upload_video")
    await callback.message.answer_video(
        video=movie["file_id"],
        caption=f"🎬 {movie['title_uz']} ({movie['year']})\nReyting: {movie['rating']}/10",
        parse_mode="HTML"
    )
    info = (
        f"<b>{movie['title_uz']}</b>\n\n"
        f"{movie['description_uz']}\n\n"
        f"Yil: {movie['year']}\n"
        f"Davomiyligi: {movie['duration']} daqiqa\n"
        f"Reyting: {movie['rating']}/10"
    )
    await callback.message.answer(info, parse_mode="HTML")
    await callback.answer()

async def send_movie_details(message, movie):
    title = movie.get("title_uz") or movie.get("title") or "Nomaʼlum"
    year = movie.get("year", "----")
    rating = movie.get("rating", "Nomaʼlum")
    genre = movie.get("genre", "Nomaʼlum janr")
    description = movie.get("description") or movie.get("description_uz") or "Tavsif mavjud emas"
    file_id = movie.get("file_id")

    caption = (
        f"🎬 <b>{title}</b> ({year})\n"
        f"⭐ Reyting: {rating}/10\n"
        f"🎭 Janr: {genre}\n"
        f"📝 <i>{description}</i>"
    )

    if file_id:
        await message.answer_video(file_id, caption=caption, parse_mode="HTML")
    else:
        await message.answer(caption, parse_mode="HTML")




# Callback orqali birini tanlash
@router.callback_query(lambda c: c.data and c.data.startswith("select_movie_"))
async def process_movie_selection(callback: CallbackQuery):
    movie_id = int(callback.data.split("_", 2)[2])
    movie = await get_movie_by_id(movie_id)
    if not movie:
        await callback.answer("Kino topilmadi.", show_alert=True)
        return

    await send_movie_details(callback.message, movie)
    await callback.answer()

@router.message()
async def handle_text_search(message: Message, state: FSMContext):
    text = message.text.strip()

    # Agar matn "/start movie_" bilan boshlansa yoki buyrug‘ bo‘lsa — qaytamiz
    if text.startswith("/start movie_") or text.startswith("/"):
        return

    lang = await get_language(message.from_user.id) or DEFAULT_LANGUAGE
    movies = await search_movies(text, lang)

    if not movies:
        return await message.answer("❌ Hech qanday kino topilmadi.")

    if len(movies) == 1:
        return await send_movie_details(message, movies[0])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🔍 Natijalarni ko‘rish",
            switch_inline_query_current_chat=text
        )
    ]])

    await message.answer(
        f"🔍 “<b>{text}</b>” bo‘yicha bir nechta kino topildi. Quyidagi tugmani bosing:",
        parse_mode="HTML",
        reply_markup=keyboard
    )



# Inline qidiruv
@router.inline_query()
async def inline_search(query: InlineQuery):
    text = query.query.strip()
    if not text:
        return await query.answer([], cache_time=1)

    lang = await get_language(query.from_user.id) or DEFAULT_LANGUAGE
    movies = await search_movies(text, lang)

    results = []
    for m in movies:
        poster_url = m.get("poster", DEFAULT_THUMB_URL)
        if not poster_url.startswith("https://") or "api.telegram.org" in poster_url:
            poster_url = DEFAULT_THUMB_URL

        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"{m['title']} ({m['year']})",
                description=f"Reyting: {m['rating']}/10 • Yuklashlar: {m.get('views', 0)}",
                thumb_url=poster_url,
                input_message_content=InputTextMessageContent(
                    message_text=f"/start movie_{m['id']}"
                )
            )
        )

    await query.answer(results[:50], cache_time=5)

def admin_panel_keyboard():
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="/xabar"), KeyboardButton(text="/statistika")],
            [KeyboardButton(text="/addmovie")],[KeyboardButton(text="/manage")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ]
    )
  


@dp.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("❌ Siz admin emassiz.")
        return

    await message.answer("✅ Admin panelga xush kelibsiz!", reply_markup=admin_panel_keyboard())

@dp.message(Command("addmovie"))
async def cmd_addmovie(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("❌ Siz admin emassiz.")
        return
    await message.answer("🎬 Iltimos, video turini tanlang:", reply_markup=type_keyboard())
    await state.set_state(AddMovieState.choosing_type)


@dp.callback_query(AddMovieState.choosing_type)
async def choose_type(callback: CallbackQuery, state: FSMContext):
    video_type = callback.data.split("_")[1]
    await state.update_data(video_type=video_type)
    await callback.message.answer("📌 Endi kino nomini kiriting (UZ):")
    await state.set_state(AddMovieState.entering_title)
    await callback.answer()


@dp.message(AddMovieState.entering_title)
async def enter_title(message: Message, state: FSMContext):
    await state.update_data(title_uz=message.text)
    await message.answer("📝 Kino tavsifini kiriting (UZ):")
    await state.set_state(AddMovieState.entering_description)


@dp.message(AddMovieState.entering_description)
async def enter_description(message: Message, state: FSMContext):
    await state.update_data(description_uz=message.text)
    await message.answer("🎭 Janrni tanlang:", reply_markup=genre_keyboard())
    await state.set_state(AddMovieState.choosing_genre)


@dp.callback_query(AddMovieState.choosing_genre)
async def choose_genre(callback: CallbackQuery, state: FSMContext):
    genre = callback.data.split("_")[1]
    await state.update_data(genre=genre)
    await callback.message.edit_reply_markup()  # eski tugmalarni yo'q qilish
    await callback.message.answer("📅 Kinoning yilini tanlang:", reply_markup=year_keyboard())
    await state.set_state(AddMovieState.choosing_year)
    await callback.answer()


@dp.callback_query(AddMovieState.choosing_year)
async def choose_year(callback: CallbackQuery, state: FSMContext):
    year = callback.data.split("_")[1]
    await state.update_data(year=year)
    await callback.message.edit_reply_markup()
    await callback.message.answer("⏱ Davomiylikni tanlang:", reply_markup=duration_keyboard())
    await state.set_state(AddMovieState.choosing_duration)
    await callback.answer()


@dp.callback_query(AddMovieState.choosing_duration)
async def choose_duration(callback: CallbackQuery, state: FSMContext):
    duration = callback.data.split("_")[1]
    await state.update_data(duration=duration)
    await callback.message.edit_reply_markup()
    await callback.message.answer("⭐️ Reytingni tanlang:", reply_markup=rating_keyboard())
    await state.set_state(AddMovieState.choosing_rating)
    await callback.answer()


@dp.callback_query(AddMovieState.choosing_rating)
async def choose_rating(callback: CallbackQuery, state: FSMContext):
    rating = callback.data.split("_")[1]
    await state.update_data(rating=rating)
    await callback.message.edit_reply_markup()
    await callback.message.answer("📤 Iltimos, kinoning video faylini yuboring:")
    await state.set_state(AddMovieState.uploading_video)
    await callback.answer()


@dp.message(AddMovieState.uploading_video, F.content_type == "video")
async def receive_video(message: Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await message.answer("🖼 Iltimos, kinoning posteri (rasmini) yuboring:")
    await state.set_state(AddMovieState.uploading_poster)


@dp.message(AddMovieState.uploading_video)
async def invalid_video(message: Message):
    await message.answer("❌ Iltimos, video yuboring.")


@dp.callback_query(AddMovieState.choosing_rating)
async def choose_rating(callback: CallbackQuery, state: FSMContext):
    rating = callback.data.split("_")[1]
    await state.update_data(rating=rating)
    await callback.message.edit_reply_markup()
    await callback.message.answer("📤 Iltimos, kinoning video faylini yuboring:")
    await state.set_state(AddMovieState.uploading_video)
    await callback.answer()


@dp.message(AddMovieState.uploading_video, F.content_type == "video")
async def receive_video(message: Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    await message.answer("🖼 Iltimos, kinoning posteri (rasm yoki rasm havolasi) yuboring:")
    await state.set_state(AddMovieState.uploading_poster)


@dp.message(AddMovieState.uploading_video)
async def invalid_video(message: Message):
    await message.answer("❌ Iltimos, faqat video fayl yuboring.")


async def upload_to_imgbb(file_bytes, file_name="poster.jpg"):
    url = "https://api.imgbb.com/1/upload"
    api_key = "efd2d33392fa80ed26a12cdeac565041"  # Siz ro'yxatdan o'tgan API key

    # Faylni base64 formatga o‘girish (shart)
    encoded_image = base64.b64encode(file_bytes).decode('utf-8')
    payload = {
        "key": api_key,
        "image": encoded_image
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload) as resp:
            result = await resp.json()
            if result.get("success"):
                return result["data"]["url"]
            else:
                raise Exception(result.get("error", {}).get("message", "Noma'lum xato"))

@dp.message(AddMovieState.uploading_poster)
async def receive_poster(message: Message, state: FSMContext):
    poster_url = None

    if message.photo:
        # Rasmni olish
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"

        try:
            # Rasmni byte ko‘rinishda olish
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as resp:
                    file_bytes = await resp.read()

            # ImgBB ga yuklash
            poster_url = await upload_to_imgbb(file_bytes)

        except Exception as e:
            return await message.answer(f"❌ Rasmni yuklab bo‘lmadi: {e}")

    elif message.text and message.text.startswith("http"):
        poster_url = message.text.strip()
    else:
        return await message.answer("❌ Iltimos, rasm yoki rasm havolasini yuboring.")

    await state.update_data(poster=poster_url)
    data = await state.get_data()

    caption = (
        f"🎬 <b>Kino haqida ma'lumot:</b>\n\n"
        f"📝 Nomi: {data['title_uz']}\n"
        f"📖 Tavsif: {data['description_uz']}\n"
        f"🎭 Janr: {data['genre']}\n"
        f"📅 Yil: {data['year']}\n"
        f"⏱ Davomiyligi: {data['duration']} daqiqa\n"
        f"⭐️ Reyting: {data['rating']}/10\n\n"
        f"✅ Tasdiqlaysizmi?"
    )

    try:
        await message.answer_photo(
            photo=poster_url,
            caption=caption,
            parse_mode="HTML",
            reply_markup=confirm_keyboard()
        )
    except Exception as e:
        return await message.answer(f"❌ Rasmni ko‘rsatib bo‘lmadi. Iltimos, boshqa rasm yuboring.\n\n{e}")

    await state.set_state(AddMovieState.confirming)


@dp.message(AddMovieState.uploading_poster)
async def invalid_poster(message: Message):
    await message.answer("❌ Iltimos, rasm yuboring.")


@dp.callback_query(AddMovieState.confirming, F.data == "confirm")
async def confirm_add_movie(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    movie_id = await add_movie(
        video_type=data["video_type"],
        title_uz=data["title_uz"],
        description_uz=data["description_uz"],
        genre=data["genre"],
        year=int(data["year"]),
        duration=int(data["duration"]),
        rating=int(data["rating"]),
        file_id=data["file_id"],
        poster=data["poster"]
    )

    await callback.message.edit_caption(
        f"✅ Kino muvaffaqiyatli qo‘shildi!\n\n🆔 Kino ID: <code>{movie_id}</code>",
        parse_mode="HTML",
        reply_markup=None
    )
    await state.clear()
    await callback.answer()

@dp.callback_query(AddMovieState.confirming, F.data == "cancel")
async def cancel_add_movie(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_caption("❌ Kino qo‘shish bekor qilindi.", reply_markup=None)
    await state.clear()
    await callback.answer()









@dp.message(Command("statistika"))
async def show_stats(message: Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("❌ Siz admin emassiz.")
        return

    users_count = await get_total_users_count()
    movies_count = await get_total_movies_count()

    await message.answer(f"👥 Foydalanuvchilar soni: {users_count}\n🎬 Kinolar soni: {movies_count}")


@dp.message(Command("xabar"))
async def broadcast_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("❌ Siz admin emassiz.")
        return
    await message.answer("Xabar matnini kiriting:")
    await state.set_state(BroadcastStates.waiting_for_broadcast_text)


@dp.message(BroadcastStates.waiting_for_broadcast_text)
async def broadcast_send(message: Message, state: FSMContext):
    text = message.text
    users = await get_all_users()
    count = 0
    for user_id in users:
        try:
            await bot.send_message(chat_id=user_id, text=text)
            count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logging.error(f"Xabar yuborishda xato: {e}")
            continue

    await message.answer(f"Xabar {count} foydalanuvchiga yuborildi.")
    await state.clear()

# --- MANAGE KINOLAR ---
@dp.message(Command("manage"))
async def manage_movies(message: Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("⛔ Siz bu buyruqdan foydalana olmaysiz.")
        return

    movies = await get_all_movies()
    if not movies:
        await message.answer("🎬 Hozircha kinolar yo‘q.")
        return

    for movie in movies:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"edit_{movie['id']}"),
                InlineKeyboardButton(text="🗑 O‘chirish", callback_data=f"delete_{movie['id']}")
            ]
        ])
        await message.answer(f"<b>{movie['title_uz']}</b>", reply_markup=keyboard, parse_mode=ParseMode.HTML)


@router.callback_query(F.data.startswith("delete_"))
async def delete_movie_callback(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_ID:
        await callback.answer("⛔ Siz admin emassiz.", show_alert=True)
        return

    movie_id = int(callback.data.split("_")[1])
    await delete_movie(movie_id)
    await callback.message.edit_text("🗑 Kino o‘chirildi.")


@router.callback_query(F.data.startswith("edit_"))
async def edit_movie_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_ID:
        await callback.answer("⛔ Siz admin emassiz.", show_alert=True)
        return

    movie_id = int(callback.data.split("_")[1])
    await state.update_data(movie_id=movie_id)
    await state.set_state(EditState.title)
    await callback.message.answer("✏️ Yangi sarlavhani kiriting:")


@router.message(EditState.title)
async def update_title_handler(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("⛔ Siz admin emassiz.")
        return

    data = await state.get_data()
    movie_id = data.get("movie_id")
    new_title = message.text
    await update_movie_title(movie_id, new_title)
    await message.answer("✅ Kino nomi yangilandi.")
    await state.clear()
# --- Main ---

async def main():
    await bot.delete_webhook(drop_pending_updates=True)  # Eski webhooklarni o‘chirish
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

