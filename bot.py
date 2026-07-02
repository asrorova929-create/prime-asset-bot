import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import db
import config
from checker import check_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("loyiha_nazorat_bot")

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

STATUS_EMOJI = {"ok": "✅", "slow": "🟡", "down": "🔴", "unknown": "⚪️"}
STATUS_TEXT = {"ok": "Ishlayapti", "slow": "Sekin ishlayapti", "down": "Ishlamayapti", "unknown": "Noma'lum"}


def is_admin(user_id: int) -> bool:
    return not config.ADMIN_IDS or user_id in config.ADMIN_IDS


def fmt_project_line(p) -> str:
    emoji = STATUS_EMOJI.get(p["last_status"], "⚪️")
    rt = f'{p["last_response_time"]:.2f}s' if p["last_response_time"] else "-"
    checked = p["last_checked_at"] or "hali tekshirilmagan"
    line = f'{emoji} <b>{p["name"]}</b> (ID: {p["id"]})\n' \
           f'   🔗 {p["url"]}\n' \
           f'   Holat: {STATUS_TEXT.get(p["last_status"], p["last_status"])} | Javob vaqti: {rt}\n' \
           f'   Oxirgi tekshiruv: {checked}'
    if p["last_error"]:
        line += f'\n   ⚠️ Xato: {p["last_error"]}'
    return line


@dp.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        "👋 Salom! Men <b>Loyiha Nazorat Bot</b>man.\n\n"
        "Men sizning loyihalaringiz (sayt, API va h.k.) ishlab turganini "
        "doimiy tekshirib, xato chiqsa darhol kanalga xabar beraman.\n\n"
        "📋 <b>Buyruqlar:</b>\n"
        "/add <ism> | <url> — yangi loyiha qo'shish\n"
        "/list — barcha loyihalar va holati\n"
        "/check — hammasini hoziroq tekshirish\n"
        "/check_id <id> — bitta loyihani tekshirish\n"
        "/remove <id> — loyihani o'chirish\n"
        "/id — o'zingizning Telegram ID'ingizni ko'rish\n"
        "/contacts — ro'yxatdan o'tgan raqamlar (admin)\n"
        "/notify_phone <raqam> | <matn> — raqamga shaxsiy xabar (admin)\n\n"
        "📱 Shaxsiy xabarlar olish uchun pastdagi tugma orqali raqamingizni ulashing."
    )
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Raqamni ulashish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(text, reply_markup=kb)


@dp.message(F.contact)
async def handle_contact(message: Message):
    contact = message.contact

    if contact.user_id and contact.user_id != message.from_user.id:
        await message.answer(
            "⚠️ Iltimos, faqat o'zingizning raqamingizni ulashing.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    db.save_contact(
        user_id=message.from_user.id,
        phone=contact.phone_number,
        first_name=message.from_user.first_name or "",
        last_name=message.from_user.last_name or "",
        username=message.from_user.username or "",
    )
    await message.answer(
        f"✅ Raqamingiz saqlandi: <code>{contact.phone_number}</code>\n"
        "Endi shu raqamga bog'liq holda botdan shaxsiy xabarlar olasiz.",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"🆔 Sizning ID: <code>{message.from_user.id}</code>")


@dp.message(Command("add"))
async def cmd_add(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Bu buyruq faqat adminlar uchun.")
        return

    raw = message.text.split(maxsplit=1)
    if len(raw) < 2 or "|" not in raw[1]:
        await message.answer(
            "❗️ Format noto'g'ri. Namuna:\n"
            "<code>/add Mening saytim | https://example.com</code>"
        )
        return

    name_part, url_part = raw[1].split("|", maxsplit=1)
    name = name_part.strip()
    url = url_part.strip()

    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url

    project_id = db.add_project(name, url, message.from_user.id)
    await message.answer(f"✅ Loyiha qo'shildi (ID: {project_id}): <b>{name}</b>\n🔗 {url}")

    status, code, rt, err = await check_url(url)
    db.update_project_status(project_id, status, code, rt, err)


@dp.message(Command("remove"))
async def cmd_remove(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Bu buyruq faqat adminlar uchun.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("❗️ Namuna: <code>/remove 3</code>")
        return

    project_id = int(parts[1].strip())
    if db.remove_project(project_id):
        await message.answer(f"🗑 Loyiha (ID: {project_id}) o'chirildi.")
    else:
        await message.answer("❗️ Bunday ID topilmadi.")


@dp.message(Command("list"))
async def cmd_list(message: Message):
    projects = db.list_projects()
    if not projects:
        await message.answer("📭 Hozircha hech qanday loyiha qo'shilmagan. /add orqali qo'shing.")
        return

    lines = [fmt_project_line(p) for p in projects]
    await message.answer("📋 <b>Loyihalar ro'yxati:</b>\n\n" + "\n\n".join(lines))


@dp.message(Command("check"))
async def cmd_check(message: Message):
    projects = db.list_projects()
    if not projects:
        await message.answer("📭 Tekshiradigan loyiha yo'q.")
        return

    await message.answer(f"🔍 {len(projects)} ta loyiha tekshirilyapti...")
    results = await run_all_checks(notify_on_change=True)
    lines = [fmt_project_line(db.get_project(p["id"])) for p in results]
    await message.answer("✅ Tekshiruv yakunlandi:\n\n" + "\n\n".join(lines))


@dp.message(Command("check_id"))
async def cmd_check_id(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("❗️ Namuna: <code>/check_id 2</code>")
        return

    project_id = int(parts[1].strip())
    project = db.get_project(project_id)
    if not project:
        await message.answer("❗️ Bunday ID topilmadi.")
        return

    status, code, rt, err = await check_url(project["url"])
    db.update_project_status(project_id, status, code, rt, err)
    await message.answer(fmt_project_line(db.get_project(project_id)))


@dp.message(Command("contacts"))
async def cmd_contacts(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Bu buyruq faqat adminlar uchun.")
        return

    contacts = db.list_contacts()
    if not contacts:
        await message.answer(
            "📭 Hozircha hech kim raqamini ulashmagan.\n"
            "Odamlar botga /start bosib, tugma orqali raqamini ulashishi kerak."
        )
        return

    lines = []
    for c in contacts:
        full_name = f'{c["first_name"]} {c["last_name"]}'.strip()
        uname = f'@{c["username"]}' if c["username"] else "-"
        lines.append(f'📱 {c["phone"]} — {full_name} ({uname}) | ID: {c["user_id"]}')

    await message.answer("👥 <b>Ro'yxatdan o'tgan kontaktlar:</b>\n\n" + "\n".join(lines))


@dp.message(Command("notify_phone"))
async def cmd_notify_phone(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Bu buyruq faqat adminlar uchun.")
        return

    raw = message.text.split(maxsplit=1)
    if len(raw) < 2 or "|" not in raw[1]:
        await message.answer(
            "❗️ Format noto'g'ri. Namuna:\n"
            "<code>/notify_phone +998940683221 | Sizning matningiz</code>"
        )
        return

    phone_part, text_part = raw[1].split("|", maxsplit=1)
    phone = phone_part.strip()
    text = text_part.strip()

    contact = db.get_user_id_by_phone(phone)
    if not contact:
        await message.answer(
            f"❗️ <code>{phone}</code> raqami hali ro'yxatdan o'tmagan.\n\n"
            "Bu raqamga bog'liq odam avval botga /start bosib, "
            "\"📱 Raqamni ulashish\" tugmasini bosishi shart."
        )
        return

    try:
        await bot.send_message(contact["user_id"], f"📩 <b>Xabar:</b>\n\n{text}")
        await message.answer(f"✅ Xabar {phone} raqamiga (ID: {contact['user_id']}) yuborildi.")
    except Exception as e:
        await message.answer(f"❌ Xabar yuborilmadi: {e}")


async def run_all_checks(notify_on_change: bool = True):
    projects = db.list_projects()
    changed = []

    for p in projects:
        old_status = p["last_status"]
        status, code, rt, err = await check_url(p["url"])
        db.update_project_status(p["id"], status, code, rt, err)

        if notify_on_change and old_status != status and old_status != "unknown":
            await notify_channel(p["id"], p["name"], p["url"], old_status, status, err)

        changed.append({"id": p["id"], "old": old_status, "new": status})

    return changed


async def notify_channel(project_id, name, url, old_status, new_status, err):
    if not config.CHANNEL_ID:
        log.warning("CHANNEL_ID sozlanmagan, xabar yuborilmadi.")
        return

    emoji = STATUS_EMOJI.get(new_status, "⚪️")
    if new_status == "down":
        text = (
            f"🚨 <b>DIQQAT! Loyihada muammo aniqlandi</b>\n\n"
            f"{emoji} <b>{name}</b> (ID: {project_id})\n"
            f"🔗 {url}\n"
            f"Holat: {STATUS_TEXT[old_status]} ➜ {STATUS_TEXT[new_status]}\n"
        )
        if err:
            text += f"⚠️ Sabab: {err}\n"
    elif new_status == "ok" and old_status in ("down", "slow"):
        text = (
            f"✅ <b>Loyiha tiklandi</b>\n\n"
            f"{emoji} <b>{name}</b> (ID: {project_id})\n"
            f"🔗 {url}\n"
            f"Holat: {STATUS_TEXT[old_status]} ➜ {STATUS_TEXT[new_status]}\n"
        )
    else:
        text = (
            f"{emoji} <b>{name}</b> holati o'zgardi: "
            f"{STATUS_TEXT[old_status]} ➜ {STATUS_TEXT[new_status]}\n🔗 {url}"
        )

    try:
        await bot.send_message(config.CHANNEL_ID, text)
    except Exception as e:
        log.error(f"Kanalga xabar yuborishda xato: {e}")

    if new_status == "down" or (new_status == "ok" and old_status in ("down", "slow")):
        for c in db.list_contacts():
            try:
                await bot.send_message(c["user_id"], text)
            except Exception as e:
                log.error(f"{c['phone']} ga xabar yuborishda xato: {e}")


async def scheduled_job():
    log.info("Rejalashtirilgan tekshiruv boshlandi...")
    await run_all_checks(notify_on_change=True)
    log.info("Rejalashtirilgan tekshiruv tugadi.")


async def main():
    db.init_db()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_job, "interval", minutes=config.CHECK_INTERVAL_MINUTES)
    scheduler.start()

    log.info(f"Bot ishga tushdi. Har {config.CHECK_INTERVAL_MINUTES} daqiqada tekshiradi.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
