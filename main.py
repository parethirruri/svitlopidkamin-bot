# main.py — @svitlopidkamin_bot (без /setchat, авто-сповіщення)
import logging, re, pytz, requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# ==================== НАЛАШТУВАННЯ ====================
BOT_TOKEN = "8289591969:AAH0QDO7dJhq0lwfn9HcarxloO8_GY9RQcU"
LOCATION = 'Підкамінь (Підкамінська ОТГ)'
GPV_QUEUE = '1.2'
GAV_QUEUE = '1'
SGAV_QUEUE = '1'
TZ = pytz.timezone('Europe/Kiev')

# Зберігаємо чати, де бот є адміном
ACTIVE_CHATS = set()
# =====================================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def get_outage_schedule():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get('https://poweron.loe.lviv.ua/', headers=headers, timeout=20)
        r.raise_for_status()
        text = BeautifulSoup(r.text, 'html.parser').get_text()

        gpv = re.findall(rf'Група\s*{re.escape(GPV_QUEUE)}\s*.*?немає.*?(\d{{2}}:\d{{2}})\s*до\s*(\d{{2}}:\d{{2}})', text, re.I)
        gav = bool(re.search(rf'ГАВ.*?{GAV_QUEUE}', text, re.I))
        sgav = bool(re.search(rf'СГАВ.*?{SGAV_QUEUE}', text, re.I))

        outages = [f"з {s} до {e}" for s, e in gpv]
        if gav: outages.append("Аварійне (ГАВ)")
        if sgav: outages.append("Спеціальне (СГАВ)")
        return outages or None
    except Exception as e:
        logging.error(f"Парсинг: {e}")
        return "ERROR"

def get_status_text():
    res = get_outage_schedule()
    if res == "ERROR":
        return "Не вдалося отримати графік (сайт недоступний або помилка)."
    if res is None:
        return "Протягом сьогоднішнього дня відключень світла не спостерігається."
    return "Заплановані відключення: " + "; ".join(res)

# === Авто-сповіщення ===
async def check_and_notify(context: ContextTypes.DEFAULT_TYPE):
    res = get_outage_schedule()
    if not res or res == "ERROR" or not ACTIVE_CHATS:
        return

    now = datetime.now(TZ)
    soon = now + timedelta(hours=1)

    for interval in res:
        if "з" not in interval: continue
        start_str = interval.split(" до ")[0].replace("з ", "")
        try:
            start = datetime.strptime(start_str, '%H:%M').replace(year=now.year, month=now.month, day=now.day)
            if now < start <= soon:
                msg = f"Через 1 годину не буде світла!\n\n{interval}"
                for chat_id in list(ACTIVE_CHATS):
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=msg)
                    except:
                        ACTIVE_CHATS.discard(chat_id)  # Видаляємо, якщо бот більше не адмін
        except: pass

# === Перевірка адмін-прав ===
async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type in ['group', 'supergroup']:
        try:
            member = await chat.get_member(context.bot.id)
            if member.status in ['administrator', 'creator']:
                ACTIVE_CHATS.add(chat.id)
            else:
                ACTIVE_CHATS.discard(chat.id)
        except: pass

# ==================== КОМАНДИ ====================
async def start(update: Update, context):
    await check_admin(update, context)
    text = (
        "👋 Слава Ісусу Христу! Я — *svitloЄ*\n\n"
        "📍 Підкамінь (Підкамінська ОТГ)\n"
        "🔌 ГПВ 1.2 | ГАВ 1 | СГАВ 1\n\n"
        "💡 Перевірити світло — `/svitlo`\n"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def svitlo(update: Update, context):
    await check_admin(update, context)
    await update.message.reply_text(get_status_text())
# ===============================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("svitlo", svitlo))

    # Перевірка адмін-прав при будь-якому повідомленні
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, check_admin))

    # Авто-сповіщення
    app.job_queue.run_repeating(check_and_notify, interval=3600, first=30)

    logging.info("БОТ ЗАПУЩЕНО (авто-сповіщення)")
    app.run_polling()

if __name__ == '__main__':
    main()
