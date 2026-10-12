
# -*- coding: utf-8 -*-
"""
👑 admin.py — admin qismi (bot.py bilan bir papkada turishi kerak)

Imkoniyatlar: /admin → statistika, hammaga xabar yuborish, matnlarni o'zgartirish.
Admin ID raqami: ADMIN_ID (Secrets yoki shu fayl).
"""

import asyncio
import logging
import os
import sqlite3
import time
from datetime import datetime

from aiogram import BaseMiddleware, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ===================== SOZLAMALAR =====================
ADMIN_ID = os.getenv("ADMIN_ID", "123456789")   # bir nechta bo'lsa vergul bilan: 111,222
DB_PATH = "bot.db"
BTN_ADMIN = "👑 Admin panel"

ADMIN_IDS = [int(i) for i in ADMIN_ID.replace(" ", "").split(",") if i.isdigit()]

# bot.py shu lug'atni to'ldiradi: kalit -> (menyudagi nomi, standart matn)
TEXTS = {}

log = logging.getLogger("admin")

# ===================== BAZA =====================
db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.executescript("""
CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, joined INTEGER);
CREATE TABLE IF NOT EXISTS texts (key TEXT PRIMARY KEY, value TEXT);
""")
db.commit()


def get_text(key: str) -> str:
    """Admin o'zgartirgan matn bo'lsa shuni, bo'lmasa standartini qaytaradi."""
    row = db.execute("SELECT value FROM texts WHERE key=?", (key,)).fetchone()
    return row[0] if row else TEXTS[key][1]


def set_text(key: str, value: str):
    db.execute("INSERT OR REPLACE INTO texts VALUES (?,?)", (key, value))
    db.commit()


def reset_text(key: str):
    db.execute("DELETE FROM texts WHERE key=?", (key,))
    db.commit()


class RegisterMiddleware(BaseMiddleware):
    """Har bir foydalanuvchini bazaga yozib boradi (statistika va xabar yuborish uchun)."""
    async def __call__(self, handler, event, data):
        u = getattr(event, "from_user", None)
        if u:
            db.execute("INSERT OR IGNORE INTO users VALUES (?,?)", (u.id, int(time.time())))
            db.commit()
        return await handler(event, data)


# ===================== ADMIN =====================
admin_router = Router()
is_admin = F.from_user.id.in_(ADMIN_IDS)


class AdminFSM(StatesGroup):
    broadcast = State()
    new_text = State()


def admin_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📊 Statistika", callback_data="adm:stats")
    b.button(text="📢 Xabar yuborish", callback_data="adm:bc")
    b.button(text="✏️ Matnlarni o'zgartirish", callback_data="adm:edit")
    b.adjust(1)
    return b.as_markup()


@admin_router.message(Command("cancel"), is_admin)
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


@admin_router.message(Command("admin"), is_admin)
@admin_router.message(F.text == BTN_ADMIN, is_admin)
async def admin_panel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("👑 <b>Admin panel</b>", reply_markup=admin_kb())


@admin_router.callback_query(F.data.startswith("adm:"), is_admin)
async def admin_actions(cb: CallbackQuery, state: FSMContext):
    action = cb.data.split(":")[1]
    await cb.answer()
    if action == "stats":
        total = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        today = db.execute("SELECT COUNT(*) FROM users WHERE joined>=?", (midnight,)).fetchone()[0]
        await cb.message.answer(
            f"📊 <b>Statistika</b>\n\n👥 Jami foydalanuvchilar: <b>{total}</b>\n🆕 Bugun qo'shilgan: <b>{today}</b>")
    elif action == "bc":
        await state.set_state(AdminFSM.broadcast)
        await cb.message.answer("📢 Hammaga yuboriladigan xabarni yuboring (matn, rasm yoki video).\n\nBekor qilish: /cancel")
    elif action == "edit":
        b = InlineKeyboardBuilder()
        for key, (label, _) in TEXTS.items():
            b.button(text=label, callback_data=f"edit:{key}")
        b.adjust(2)
        await cb.message.answer("✏️ Qaysi matnni o'zgartiramiz?", reply_markup=b.as_markup())


@admin_router.callback_query(F.data.startswith("edit:"), is_admin)
async def edit_choose(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":")[1]
    await cb.answer()
    if key not in TEXTS:
        return
    await state.set_state(AdminFSM.new_text)
    await state.update_data(key=key)
    b = InlineKeyboardBuilder()
    b.button(text="♻️ Asl holatiga qaytarish", callback_data=f"reset:{key}")
    await cb.message.answer("Hozirgi matn 👇")
    await cb.message.answer(get_text(key))
    await cb.message.answer(
        "✏️ Yangi matnni yuboring (qalin/kursiv formatlash saqlanadi).\n\nBekor qilish: /cancel",
        reply_markup=b.as_markup())


@admin_router.callback_query(F.data.startswith("reset:"), is_admin)
async def edit_reset(cb: CallbackQuery, state: FSMContext):
    key = cb.data.split(":")[1]
    if key in TEXTS:
        reset_text(key)
    await state.clear()
    await cb.answer("♻️ Asl holatiga qaytarildi", show_alert=True)


@admin_router.message(AdminFSM.new_text, F.text, ~F.text.startswith("/"), is_admin)
async def edit_save(message: Message, state: FSMContext):
    key = (await state.get_data())["key"]
    set_text(key, message.html_text)
    await state.clear()
    log.info("Admin %s matnni o'zgartirdi: %s", message.from_user.id, key)
    await message.answer("✅ Matn yangilandi!")


@admin_router.message(AdminFSM.broadcast, is_admin)
async def do_broadcast(message: Message, state: FSMContext):
    await state.clear()
    ids = [r[0] for r in db.execute("SELECT user_id FROM users").fetchall()]
    await message.answer(f"📤 Yuborilmoqda... ({len(ids)} ta)")
    ok = fail = 0
    for uid in ids:
        try:
            await message.copy_to(uid)
            ok += 1
        except Exception:
            fail += 1
        await asyncio.sleep(0.05)
    log.info("Broadcast: %s ok, %s fail", ok, fail)
    await message.answer(f"✅ Yuborildi: <b>{ok}</b>\n❌ Yetmadi: <b>{fail}</b>")
  
