# -*- coding: utf-8 -*-
"""
🚗 Qumtepa Karburator — oddiy bot (aiogram 3)

/start → majburiy obuna (1 ta kanal) → menyu:
  Karburator haqida | Ustaxona manzili | Barcha narxlar | Ish vaqti

Ishga tushirish:
  pip install aiogram
  BOT_TOKEN ni Secrets'ga (yoki muhitga) yozing, keyin: python bot.py
Muhim: bot CHANNEL kanalida ADMIN bo'lishi shart (obunani tekshirish uchun).
"""

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiohttp import web

# ===================== SOZLAMALAR =====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "BU_YERGA_TOKEN_YOZING")
CHANNEL = "@Qumtepa_karburator"        # majburiy obuna kanali (o'zgartiring)
LAT, LON = 40.453972, 71.663417        # ustaxona lokatsiyasi
KEEP_ALIVE = True                      # Replit uchun mini veb-server

# ===================== MATNLAR =====================
BTN_ABOUT = "🛠 Karburator haqida"
BTN_ADDRESS = "📍 Ustaxona manzili"
BTN_PRICES = "💰 Barcha narxlar"
BTN_HOURS = "⏰ Ish vaqti"

TEXT_ABOUT = (
    "🔥 <b>Damas va barcha karburatorli mashinalar uchun sifatli xizmat!</b>\n\n"
    "🛠 <b>Changan (Xitoy) karburatorini o'rnatish</b> — Damas va Labo uchun eng samarali yechim.\n\n"
    "⛽ Mashinangiz ko'p yoqilg'i yeyaptimi? Biz benzin rasxodini keskin kamaytirib beramiz!\n\n"
    "📊 <b>Real test va rasxod:</b>\n"
    "• To'g'ri o'rnatilgan Xitoy karburatori 100 km ga <b>5.5–6 litr</b> benzin sarflaydi\n"
    "• Amaliy testimiz: 1 litr benzin bilan <b>17 km</b> masofa bosib o'tildi\n\n"
    "🔧 <b>Barcha xizmatlarimiz:</b>\n"
    "• Karburator tozalash (to'liq demontaj bilan)\n"
    "• Igna-klapan almashtirish\n"
    "• Svecha almashtirish (narxi kelishiladi)\n"
    "• Avto elektrik xizmatlari\n"
    "• Xolostoy yurishni sozlash\n"
    "• Umumiy texnik ko'rik"
)

TEXT_ADDRESS = (
    "📍 <b>Manzil:</b> Marg'ilon shahri, Qumtepa bozori oldida\n\n"
    "🗺 Lokatsiya pastda 👇\n\n"
    "📞 Tel: +998 93 611 85 85\n"
    "✈️ Telegram: @Qumtepa_karburator"
)

TEXT_PRICES = (
    "💰 <b>Barcha narxlar:</b>\n\n"
    "🔹 Xitoy (Changan) karburatori: <b>350 000 so'm</b>\n"
    "🔹 O'rnatib berish (ustanovka): <b>150 000 so'm</b>\n"
    "🔹 Svecha almashtirish: narxi kelishiladi\n\n"
    "📞 Navbatga yozilish: +998 93 611 85 85\n"
    "✈️ Telegram: @Qumtepa_karburator"
)

TEXT_HOURS = (
    "⏰ <b>Ish vaqti:</b> 08:00 – 19:00\n"
    "❌ <b>Dam olish kuni:</b> Payshanba"
)

# ===================== BOT =====================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("bot")

bot: Bot = None
dp = Dispatcher()


def menu_kb() -> ReplyKeyboardMarkup:
    """Asosiy menyu tugmalari."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_ABOUT)],
            [KeyboardButton(text=BTN_ADDRESS), KeyboardButton(text=BTN_PRICES)],
            [KeyboardButton(text=BTN_HOURS)],
        ],
        resize_keyboard=True,
    )


def sub_kb():
    """Obuna bo'lish va tekshirish tugmalari."""
    b = InlineKeyboardBuilder()
    b.button(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL.lstrip('@')}")
    b.button(text="✅ Tekshirish", callback_data="check_sub")
    b.adjust(1)
    return b.as_markup()


async def is_subscribed(user_id: int) -> bool:
    """Foydalanuvchi kanalga obuna bo'lganini tekshiradi."""
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status not in ("left", "kicked")
    except Exception as e:
        # Odatda: bot kanalda admin emas yoki kanal nomi noto'g'ri
        log.error("Obunani tekshirib bo'lmadi (%s): %s", CHANNEL, e)
        return True


async def ask_subscription(message: Message):
    await message.answer(
        "🔒 <b>Botdan foydalanish uchun kanalimizga obuna bo'ling:</b>\n\n"
        f"📢 {CHANNEL}\n\n"
        "Obuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing.",
        reply_markup=sub_kb(),
    )


async def show_menu(message: Message):
    await message.answer(
        "🚗 <b>Qumtepa Karburator</b> avto ustaxonasi botiga xush kelibsiz!\n\n"
        "Kerakli bo'limni tanlang 👇",
        reply_markup=menu_kb(),
    )


@dp.message(CommandStart())
async def cmd_start(message: Message):
    if await is_subscribed(message.from_user.id):
        await show_menu(message)
    else:
        await ask_subscription(message)


@dp.callback_query(F.data == "check_sub")
async def cb_check(cb: CallbackQuery):
    if not await is_subscribed(cb.from_user.id):
        await cb.answer("❌ Siz hali obuna bo'lmadingiz!", show_alert=True)
        return
    await cb.answer("✅ Rahmat!")
    await show_menu(cb.message)
    try:
        await cb.message.delete()
    except Exception:
        pass


async def guard(message: Message) -> bool:
    """Har bir tugmada obunani qayta tekshiradi."""
    if await is_subscribed(message.from_user.id):
        return True
    await ask_subscription(message)
    return False


@dp.message(F.text == BTN_ABOUT)
async def about(message: Message):
    if await guard(message):
        await message.answer(TEXT_ABOUT)


@dp.message(F.text == BTN_ADDRESS)
async def address(message: Message):
    if await guard(message):
        await message.answer(TEXT_ADDRESS)
        await message.answer_location(LAT, LON)


@dp.message(F.text == BTN_PRICES)
async def prices(message: Message):
    if await guard(message):
        await message.answer(TEXT_PRICES)


@dp.message(F.text == BTN_HOURS)
async def hours(message: Message):
    if await guard(message):
        await message.answer(TEXT_HOURS)


@dp.message(F.text)
async def other(message: Message):
    """Boshqa matn yozilsa, menyuni eslatadi."""
    if await guard(message):
        await message.answer("👇 Iltimos, menyudagi tugmalardan birini tanlang.", reply_markup=menu_kb())


@dp.errors()
async def on_error(event):
    log.exception("Xatolik: %s", event.exception)
    return True


async def keep_alive():
    """Replit uchun: bot o'chib qolmasligi uchun mini veb-server."""
    async def alive(request):
        return web.Response(text="Bot ishlayapti ✅")

    app = web.Application()
    app.router.add_get("/", alive)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080))).start()


async def main():
    global bot
    if ":" not in BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN topilmadi. Uni Secrets'ga yoki fayl boshiga yozing.")
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    if KEEP_ALIVE:
        await keep_alive()
    await bot.delete_webhook(drop_pending_updates=True)
    me = await bot.me()
    log.info("Bot ishga tushdi: @%s", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
