import logging
import json
import os
import qrcode
import io

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Telegram токен
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Google Sheets ключ
SPREADSHEET_ID = os.getenv("GSHEET_KEY")

# Получаем Google creds из переменной окружения
creds_json = json.loads(os.getenv("GOOGLE_CREDS_JSON"))

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
gc = gspread.authorize(credentials)

sheet = gc.open_by_key(SPREADSHEET_ID).worksheet("loyalty_users")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# Кнопки
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("📈 Мой уровень"), KeyboardButton("💰 Баланс"))
main_kb.add(KeyboardButton("🧾 Внести покупку"))

@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = str(message.from_user.id)
    user = sheet.findall(user_id)
    if not user:
        # Регистрируем пользователя
        sheet.append_row([
            user_id,
            message.from_user.first_name,
            "",
            "",
            "0", "Новичок", "3", "0", "", message.date.isoformat()
        ])
        await message.answer("👋 Привет! Ты зарегистрирован в программе лояльности ☕️", reply_markup=main_kb)

        # Генерируем QR
        img = qrcode.make(user_id)
        buf = io.BytesIO()
        img.save(buf)
        buf.seek(0)
        await message.answer_photo(buf, caption="📱 Покажи этот QR бариста при покупке")
    else:
        await message.answer("👋 Ты уже зарегистрирован!", reply_markup=main_kb)

@dp.message_handler(lambda msg: msg.text == "📈 Мой уровень")
async def level(message: types.Message):
    user_id = str(message.from_user.id)
    users = sheet.col_values(1)
    if user_id in users:
        row = users.index(user_id) + 1
        data = sheet.row_values(row)
        await message.answer(f"☕️ Уровень: *{data[5]}*\n💸 Скидка: *{data[6]}%*\nОбщая сумма покупок: *{data[4]}₽*", parse_mode="Markdown")
    else:
        await message.answer("Ты не зарегистрирован. Нажми /start")

@dp.message_handler(lambda msg: msg.text == "💰 Баланс")
async def balance(message: types.Message):
    user_id = str(message.from_user.id)
    users = sheet.col_values(1)
    if user_id in users:
        row = users.index(user_id) + 1
        data = sheet.row_values(row)
        await message.answer(f"💼 Баланс: {data[7]} баллов")
    else:
        await message.answer("Ты не зарегистрирован. Нажми /start")

@dp.message_handler(lambda msg: msg.text == "🧾 Внести покупку")
async def purchase(message: types.Message):
    await message.answer("🔢 Введи сумму покупки (только цифры):")
    @dp.message_handler(lambda m: m.text.isdigit())
    async def handle_amount(m: types.Message):
        amount = int(m.text)
        user_id = str(m.from_user.id)
        users = sheet.col_values(1)
        if user_id in users:
            row = users.index(user_id) + 1
            data = sheet.row_values(row)
            total = float(data[4]) + amount
            if total >= 14444:
                tier = "Ценитель"
                percent = 7
            elif total >= 7777:
                tier = "Любитель"
                percent = 5
            else:
                tier = "Новичок"
                percent = 3
            cashback = amount * percent / 100
            balance = float(data[7]) + cashback
            sheet.update(f"E{row}", str(total))
            sheet.update(f"F{row}", tier)
            sheet.update(f"G{row}", str(percent))
            sheet.update(f"H{row}", str(round(balance, 2)))
            await m.answer(f"✅ Покупка учтена\n💰 Начислено: {round(cashback, 2)} баллов")
        else:
            await m.answer("Ты не зарегистрирован. Нажми /start")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
