# -*- coding: utf-8 -*-
"""
🚗 user.py — foydalanuvchi qismi (bot.py va admin.py bilan bir papkada)
"""

import logging
from aiogram import Bot, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, KeyboardButton, Message, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from admin import ADMIN_IDS, BTN_ADMIN, get_text

# ===================== SOZLAMALAR =====================
CHANNEL = "@Qumtepa_karburator"        # Majburiy obuna kanali
LAT, LON = 40.453972, 71.663417        # Ustaxona lokatsiyasi

BTN_ABOUT = "🛠 Karburator haqida"
BTN_ADDRESS = "📍 Ustaxona manzili"
BTN_PRICES = "💰 Barcha narxlar"
BTN_HOURS = "⏰ Ish vaqti"

user_router = Router()
log = logging.getLogger("user")


def menu_kb(user_id: int) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_ABOUT)],
        [KeyboardButton(text=BTN_ADDRESS), KeyboardButton(text=BTN_PRICES)],
        [KeyboardButton(text=BTN_HOURS)],
    ]
    if user_id in ADMIN_IDS:
        rows.append([KeyboardButton(text=BTN_ADMIN)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def sub_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL.lstrip('@')}")
    b.button(text="✅ Tekshirish", callback_data="check_sub")
    b.adjust(1)
    return b.as_markup()


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    if user_id in ADMIN_IDS:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status not in ("left", "kicked")
    except Exception as e:
        log.error("Obunani tekshirib bo'lmadi (%s): %s", CHANNEL, e)
        return True


async def ask_subscription(message: Message):
    await message.answer(
        "🔒 <b>Botdan foydalanish uchun kanalimizga obuna bo'ling:</b>\n\n"
        f"📢 {CHANNEL}\n\nObuna bo'lgach, <b>✅ Tekshirish</b> tugmasini bosing.",
        reply_markup=sub_kb())


async def show_menu(message: Message, user_id: int):
    await message.answer(
        "🚗 <b>Qumtepa Karburator</b> avto ustaxonasi botiga xush kelibsiz!\n\n"
        "Kerakli bo'limni tanlang 👇", reply_markup=menu_kb(user_id))


async def guard(message: Message) -> bool:
    bot = message.bot
    if await is_subscribed(bot, message.from_user.id):
        return True
    await ask_subscription(message)
    return False


@user_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    bot = message.bot
    if await is_subscribed(bot, message.from_user.id):
        await show_menu(message, message.from_user.id)
    else:
        await ask_subscription(message)


@user_router.callback_query(F.data == "check_sub")
async def cb_check(cb: CallbackQuery):
    bot = cb.bot
    if not await is_subscribed(bot, cb.from_user.id):
        await cb.answer("❌ Siz hali obuna bo'lmadingiz!", show_alert=True)
        return
    await cb.answer("✅ Rahmat!")
    await show_menu(cb.message, cb.from_user.id)
    try:
        await cb.message.delete()
    except Exception:
        pass


@user_router.message(F.text == BTN_ABOUT)
async def about(message: Message):
    if await guard(message):
        await message.answer(get_text("about"))


@user_router.message(F.text == BTN_ADDRESS)
async def address(message: Message):
    if await guard(message):
        await message.answer(get_text("address"))
        await message.answer_location(LAT, LON)


@user_router.message(F.text == BTN_PRICES)
async def prices(message: Message):
    if await guard(message):
        await message.answer(get_text("prices"))


@user_router.message(F.text == BTN_HOURS)
async def hours(message: Message):
    if await guard(message):
        await message.answer(get_text("hours"))


@user_router.message(F.text)
async def other(message: Message):
    if await guard(message):
        await message.answer("👇 Iltimos, menyudagi tugmalardan birini tanlang.",
                             reply_markup=menu_kb(message.from_user.id))
