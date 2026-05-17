import random
import time
import requests
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = "7995077935:AAGuO6Ig9yJl5CapjXOmCG3f80uXTzeUyGI"
FIREBASE_URL = "https://my-muhmad-default-rtdb.firebaseio.com"

CODE_LIFETIME = 5 * 60


def clean_phone(phone: str) -> str:
    return "".join(ch for ch in str(phone) if ch.isdigit())


def phone_variants(phone: str):
    phone = clean_phone(phone)
    variants = {phone}

    if phone.startswith("7") and len(phone) == 11:
        variants.add("8" + phone[1:])
        variants.add("+7" + phone[1:])

    if phone.startswith("8") and len(phone) == 11:
        variants.add("7" + phone[1:])
        variants.add("+7" + phone[1:])

    variants.add("+" + phone)
    return list(variants)


def firebase_get(path: str):
    url = f"{FIREBASE_URL}/{path}.json"
    r = requests.get(url, timeout=15)
    return r.json()


def firebase_put(path: str, data: dict):
    url = f"{FIREBASE_URL}/{path}.json"
    r = requests.put(url, json=data, timeout=15)
    return r.json()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = KeyboardButton(
        text="✅ Поделиться номером",
        request_contact=True
    )

    kb = ReplyKeyboardMarkup(
        [[btn]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

    await update.message.reply_text(
        "Чтобы получить код входа, нажми кнопку ниже.\n\n"
        "Номер нельзя вводить текстом — нужно именно поделиться контактом через Telegram.",
        reply_markup=kb
    )


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    user = update.effective_user

    if not contact:
        return

    if contact.user_id != user.id:
        await update.message.reply_text(
            "❌ Нельзя отправить чужой номер.\n"
            "Нажми кнопку «Поделиться номером» и отправь именно свой контакт."
        )
        return

    phone = clean_phone(contact.phone_number)

    ban = firebase_get(f"bannedPhones/{phone}")
    if ban:
        await update.message.reply_text("🚫 Этот номер заблокирован.")
        return

    code = str(random.randint(1000, 9999))
    now = int(time.time() * 1000)
    expires = now + CODE_LIFETIME * 1000

    data = {
        "code": code,
        "phone": phone,
        "telegram_id": user.id,
        "telegram_username": user.username or "",
        "first_name": user.first_name or "",
        "createdAt": now,
        "expires": expires,
        "used": False
    }

    for p in phone_variants(phone):
        firebase_put(f"loginCodes/{p}", data)

    await update.message.reply_text(
        f"✅ Код входа:\n\n{code}\n\n"
        "Действует 5 минут.\n"
        "Введи этот номер и код в Muhmadgram."
    )


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Номер нельзя вводить текстом.\n"
        "Нажми /start и используй кнопку «Поделиться номером»."
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newcode", start))
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
