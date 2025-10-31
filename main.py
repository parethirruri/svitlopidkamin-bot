# main.py — @svitlopidkamin_bot
import logging
import re
from datetime import datetime, timedelta
import pytz
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# === ТОКЕН ===
BOT_TOKEN = "8289591969:AAH0QDO7dJhq0lwfn9HcarxloO8_GY9RQcU
"

# === Параметри ===
LOCATION = 'Підкамінь (Підкамінська ОТГ)'
STREET = 'Молодіжна'
HOUSE = '6'
GPV_QUEUE = '1.2'
GAV_QUEUE = '1'
SGAV_QUEUE = '1'
TZ = pytz.timezone('Europe/Kiev')

# ID чату — встановлюється командою /setchat
CHAT_ID = None

logging.basicConfig(level=logging.INFO)

# === Парсинг графіка ===
def get_outage_schedule():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get('https://poweron.loe.lviv.ua/', headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text()

        # ГПВ: шукаємо "Група 1.2 ... немає з 16:00 до 18:00"
        gpv = re.findall(rf'Група\s*{re.escape(GPV_QUEUE)}\s*.*?немає.*?(\d{{2}}:\d{{2}})\s*до\s*(\d{{2}}:\d{{2}})', text, re.I)
        
        # Аварійні
        gav = bool(re.search(rf'ГАВ.*?черга.*?{GAV_QUEUE}', text, re.I))
        sgav = bool(re.search(rf'СГАВ.*?черга.*?{SGAV_QUEUE}', text, re.I))

        outages = []
        for s, e in gpv:
            outages.append(f"з {s} до {e}")
        if gav: outages.append("Аварійне (ГАВ)")
        if sgav: outages.append("Спеціальне (СГАВ)")

        return outages
    except Exception as e:
        logging.error(f"Помилка парсингу: {e}")
        return []

# === Форматована відповідь ===
def get_status_text():
    outages = get_outage_schedule()
    if not outages:
        return "Протягом сьогоднішнього дня відключень світла не спостерігається."
    
    return "Заплановані відключення: " + "; ".join(outages)

# === Автоповідомлення за 1 годину ===
async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    if not CHAT_ID:
        return

    outages = get_outage_schedule()
    now = datetime.now(TZ)
    in_one_hour = now + timedelta(hours=1)

    for interval in outages:
        if "з" not in interval:
            continue
        start_str = interval.split(" до ")[0]
        try:
            start_time = datetime.strptime(start_str, '%H:%M').replace(year=now.year, month=now.month, day=now.day)
            if now < start_time <= in_one_hour:
                msg = f"Через 1 годину не буде світла!\n\n{interval}"
                await context.bot.send_message(chat_id=CHAT_ID, text=msg)
                logging.info(f"Повідомлення: {msg}")
        except:
            continue

# === Команди ===
async def svitlo(update: Update, context):
    text = get_status_text()
    await update.message.reply_text(f"{text}")

async def setchat(update: Update, context):
    global CHAT_ID
    CHAT_ID = update.message.chat_id
    await update.message.reply_text("Сповіщення увімкнено! За годину до відключення — повідомлю.")

async def start(update: Update, context):
    await update.message.reply_text(
        "svitloЄ — @svitlopidkamin_bot\n\n"
        f"{LOCATION}, вул. {STREET}, {HOUSE}\n"
        "ГПВ 1.2 | ГАВ 1 | СГАВ 1\n\n"
        "Команда: /svitlo\n"
        "Увімкнути сповіщення: /setchat"
    )

# === Запуск ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("svitlo", svitlo))
    app.add_handler(CommandHandler("setchat", setchat))

    # Перевірка щогодини
    app.job_queue.run_repeating(check_and_notify, interval=3600, first=10)

    print("svitloЄ (@svitlopidkamin_bot) запущено!")
    app.run_polling()

if __name__ == '__main__':
    main()
