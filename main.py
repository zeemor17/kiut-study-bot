import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

from config import BOT_TOKEN, GEMINI_API_KEY, ADMIN_USERNAMES, ADMIN_IDS
from ai_service import analyze_board_image
from tts_service import generate_speech
from database import (
    save_or_update_user,
    log_activity,
    get_statistics,
    get_recent_users,
    get_all_user_ids,
    save_flashcards,
    get_flashcard
)

logging.basicConfig(level=logging.INFO)

if not BOT_TOKEN:
    print("\n[OGOHLANTIRISH] BOT_TOKEN kiritilmagan! Iltimos, .env faylini to'ldiring.\n")

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher()

TEMP_DIR = "temp_media"
os.makedirs(TEMP_DIR, exist_ok=True)

FLASHCARD_STORE = {}

class BroadcastState(StatesGroup):
    waiting_for_message = State()

def is_admin(user: types.User) -> bool:
    """Foydalanuvchi admin ekanligini 100% ishonchli tekshiradi."""
    if user.id in ADMIN_IDS:
        return True
    if user.username and user.username.lower() in [u.lower() for u in ADMIN_USERNAMES]:
        return True
    return False

def get_admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Umumiy Statistika", callback_data="admin_stats"))
    builder.row(InlineKeyboardButton(text="👥 So'nggi foydalanuvchilar", callback_data="admin_users"))
    builder.row(InlineKeyboardButton(text="📢 Barchaga xabar yuborish", callback_data="admin_broadcast"))
    return builder.as_markup()

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    # Bazaga foydalanuvchini qayd etish
    save_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )
    log_activity(message.from_user.id, "start")

    welcome_text = (
        "👋 **Assalomu alaykum! Men Board2Audio botiman.**\n\n"
        "Men universitet talabalariga darslarni oson o'zlashtirishda yordam beraman.\n\n"
        "🎯 **Qanday ishlayman?**\n"
        "1. Darsdagi **doska (doskadagi yozuvlar)** yoki **slayd** rasmini menga yuborasiz.\n"
        "2. Men doskani o'rganib chiqib:\n"
        "   • 🎧 **1 daqiqalik mini-podkast (ovozli xabar)** tayyorlayman;\n"
        "   • 📝 Toza va tushunarli **konspekt** yozib beraman;\n"
        "   • ❓ Imtihonga tayyorlanish uchun **interaktiv savol-javoblar (kartochkalar)** tuzaman.\n\n"
        "📸 *Sinab ko'rish uchun hoziroq doska yoki slayd rasmini yuboring!*"
    )
    await message.answer(welcome_text, parse_mode="Markdown")

@dp.message(Command("admin"))
async def handle_admin(message: types.Message):
    if not is_admin(message.from_user):
        await message.answer("⛔ Sizda ushbu bo'limga kirish huquqi yo'q.")
        return

    admin_text = (
        "👑 **Boshqaruv Paneli (Admin Panel)**\n\n"
        "Xush kelibsiz! Quyidagi tugmalar orqali bot foydalanuvchilari statistikasi "
        "va faollikni kuzatishingiz mumkin:"
    )
    await message.answer(admin_text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Ruxsat berilmagan", show_alert=True)
        return

    stats = get_statistics()
    text = (
        "📊 **Bot Statistikasi:**\n\n"
        f"👤 **Jami foydalanuvchilar:** {stats['total_users']} ta\n"
        f"📸 **Tahlil qilingan darslar soni:** {stats['total_lessons']} ta\n"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_users")
async def cb_admin_users(callback: CallbackQuery):
    if not is_admin(callback.from_user):
        await callback.answer("Ruxsat berilmagan", show_alert=True)
        return

    users = get_recent_users(limit=10)
    if not users:
        text = "Hozircha foydalanuvchilar yo'q."
    else:
        text = "👥 **So'nggi 10 ta foydalanuvchi:**\n\n"
        for idx, u in enumerate(users, 1):
            uid, uname, fname, grp, last = u
            username_str = f"@{uname}" if uname else "Mavjud emas"
            text += f"{idx}. **{fname}** ({username_str})\n   🕒 Oxirgi faollik: `{last}`\n\n"

    await callback.message.edit_text(text, reply_markup=get_admin_keyboard(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user):
        await callback.answer("Ruxsat berilmagan", show_alert=True)
        return

    await state.set_state(BroadcastState.waiting_for_message)
    await callback.message.answer("✍️ Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:")
    await callback.answer()

@dp.message(BroadcastState.waiting_for_message)
async def handle_broadcast_message(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user):
        await state.clear()
        return

    user_ids = get_all_user_ids()
    sent_count = 0

    status_msg = await message.answer(f"📢 Xabar {len(user_ids)} ta foydalanuvchiga yuborilmoqda...")

    for uid in user_ids:
        try:
            await bot.send_message(uid, f"📢 **Universitet e'loni:**\n\n{message.text}", parse_mode="Markdown")
            sent_count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await state.clear()
    await status_msg.edit_text(f"✅ Xabar muvaffaqiyatli {sent_count} ta talabaga yetkazildi!")

@dp.message(F.photo)
async def handle_board_photo(message: types.Message):
    if not GEMINI_API_KEY:
        await message.answer("⚠️ Tizimda GEMINI_API_KEY ulanmagan.")
        return

    user_id = message.from_user.id
    save_or_update_user(
        user_id=user_id,
        username=message.from_user.username,
        full_name=message.from_user.full_name
    )

    status_msg = await message.answer("🔍 *Doska rasmi tahlil qilinmoqda...* (1/2)", parse_mode="Markdown")

    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    
    image_path = os.path.join(TEMP_DIR, f"{user_id}_{photo.file_unique_id}.jpg")
    audio_path = os.path.join(TEMP_DIR, f"{user_id}_{photo.file_unique_id}.mp3")

    try:
        await bot.download_file(file_info.file_path, image_path)

        loop = asyncio.get_running_loop()
        analysis = await loop.run_in_executor(None, analyze_board_image, image_path)

        podcast_script = analysis.get("podcast_script", "")
        code_snippet = (analysis.get("code_snippet") or "").strip()
        clean_notes = analysis.get("clean_notes", "")
        flashcards = analysis.get("flashcards", [])

        # DBga dars tahlili saqlash
        log_activity(user_id, "photo_processed", summary=podcast_script[:200])

        await status_msg.edit_text("🎙️ *Ovozli mini-podkast yozilmoqda...* (2/2)", parse_mode="Markdown")
        await generate_speech(podcast_script, audio_path)

        voice_file = FSInputFile(audio_path)
        await message.answer_voice(
            voice=voice_file,
            caption="🎧 **Darsning 1 daqiqalik mini-podkasti** (Do'stingiz kabi tushuntirish)",
            parse_mode="Markdown"
        )

        # Agar darsda kod bo'lsa, terminal uslubida alohida chiroyli ko'rsatish
        if code_snippet:
            formatted_code = code_snippet
            if not formatted_code.startswith("```"):
                formatted_code = f"```java\n{formatted_code}\n```"
            await message.answer(
                f"💻 **Dasturlash Kodi (Terminal / IDE):**\n\n{formatted_code}\n\n👆 *Kodni to'liq nusxalash (copy) uchun uning ustiga bir marta bosing.*",
                parse_mode="Markdown"
            )

        if clean_notes:
            await message.answer(f"📝 **Dars konspekti:**\n\n{clean_notes}")

        if flashcards:
            saved_ids = save_flashcards(user_id, flashcards)
            builder = InlineKeyboardBuilder()
            for idx, card_id in enumerate(saved_ids):
                card = flashcards[idx]
                q_text = card.get('question', f'Savol {idx+1}')
                builder.row(InlineKeyboardButton(
                    text=f"❓ {idx+1}-savol: {q_text[:35]}...",
                    callback_data=f"fc_{card_id}"
                ))
            await message.answer(
                "🗂️ **O'zingizni sinab ko'ring (Flashcardlar):**\nSavol ustiga bosing va javobni ko'ring:",
                reply_markup=builder.as_markup()
            )

        await status_msg.delete()

    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)[:200]}")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)

@dp.callback_query(F.data.startswith("fc_"))
async def handle_flashcard_click_db(callback: CallbackQuery):
    try:
        card_id = int(callback.data.replace("fc_", ""))
        card = get_flashcard(card_id)
        if card:
            text = f"❓ **Savol:** {card['question']}\n\n💡 **Javob:** {card['answer']}"
            await callback.answer()
            await callback.message.reply(text, parse_mode="Markdown")
        else:
            await callback.answer("Savol topilmadi.", show_alert=True)
    except Exception:
        await callback.answer("Savol topilmadi.", show_alert=True)

async def handle_ping(request):
    return web.Response(text="KIUT Study Bot is running 24/7!")

async def start_web_server():
    port = int(os.getenv("PORT", 8080))
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    if not bot:
        print("[XATO] Bot ishga tusha olmaydi. BOT_TOKEN mavjud emas.")
        return
        
    # Agar bulutli serverda (Render, Railway) bo'lsa, port ochish
    if os.getenv("PORT"):
        await start_web_server()
        print(f"🌐 Healthcheck web server ishga tushdi: port {os.getenv('PORT')}")

    print("🚀 Bot Admin Panel bilan muvaffaqiyatli ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
