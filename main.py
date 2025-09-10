import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters
import requests

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')

# Данные для отправки на сайт
WEBFORM_URL = "https://ya7auto.ru/crm/form/iframe/3/"
FORM_FIELD_NAME = "firstname"
FORM_FIELD_PHONE = "phone"
FORM_FIELD_DATA = "about"
# ==================================

# Определяем состояния для ConversationHandler
AUTO_START, CONTROL, GPS, PHONE = range(4)


# Функция для сопоставления ответов и рекомендаций
def recommend_systems(answers):
    systems = [
        {"name": "Pandora DX-40R", "autostart": 0, "brelok": 1, "gsm": 0, "gps": 0,
         "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-dx-40r/"},
        {"name": "Pandora DX-40RS", "autostart": 1, "brelok": 1, "gsm": 0, "gps": 0,
         "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-dx-40rs/"},
        {"name": "PanDECT X-1800L v4 Light", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 0,
         "link": "https://ya7auto.ru/auto-security/car-alarms/pandect-x-1800l-v4-light/"},
        {"name": "Pandora VX 4G Light", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 0,
         "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-vx-4g-light/"},
        {"name": "Pandora VX-4G GPS v2", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 1,
         "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-vx-4g-gps-v2/"},
        {"name": "Pandora VX 3100", "autostart": 1, "brelok": 1, "gsm": 1, "gps": 1,
         "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-vx-3100/"},
        {"name": "StarLine A63 v2 ECO", "autostart": 0, "brelok": 1, "gsm": 0, "gps": 0,
         "link": "https://ya7auto.ru/auto-security/car-alarms/starline-a63-v2-eco/"},
        {"name": "StarLine А93 v2 ECO", "autostart": 1, "brelok": 1, "gsm": 0, "gps": 0,
         "link": "https://ya7auto.ru/auto-security/car-alarms/starline-a93-v2-eco/"},
        {"name": "StarLine S96 v2 ECO", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 0,
         "link": "https://ya7auto.ru/auto-security/car-alarms/starline-s96-v2-eco/"},
        {"name": "StarLine S96 V2 LTE GPS", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 1,
         "link": "https://ya7auto.ru/auto-security/car-alarms/starline-s96-v2-lte-gps/"}
    ]

    matched_systems = []
    for system in systems:
        if (system['autostart'] == answers.get('autostart') and
                (system['brelok'] == answers.get('control') or system['gsm'] == answers.get('control')) and
                system['gps'] == answers.get('gps')):
            matched_systems.append(system)

    return matched_systems[:2]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    context.user_data['user_name'] = user.first_name or user.username
    context.user_data['user_answers'] = {}

    await update.message.reply_text(
        f"👋🏻 Привет, {user.first_name}!\n\nЯ помогу тебе выбрать систему на твой автомобиль!")
    await update.message.reply_text("🦾 Давай определимся с тем, что должна уметь ваша сигнализации")
    await update.message.reply_text("1️⃣ Нужен ли вам автозапуск?")
    await update.message.reply_text(
        "🥶 В условиях нашего климата необходимо прогревать двигатель перед поездкой... Какую систему выберете?",
        reply_markup=ReplyKeyboardMarkup(
            [["С Автозапуском", "БЕЗ Автозапуском"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return AUTO_START


async def autostart_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "С Автозапуском":
        context.user_data['user_answers']['autostart'] = 1
    else:
        context.user_data['user_answers']['autostart'] = 0

    await update.message.reply_text("2️⃣ Как вы планируете управлять системой? Брелок или GSM-модуль")
    await update.message.reply_text(
        "🙄 Существует устаревший способ управления системы через брелок... Что выберете?",
        reply_markup=ReplyKeyboardMarkup(
            [["😎Приложение в телефоне", "📺Брелок"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return CONTROL


async def control_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "😎Приложение в телефоне":
        context.user_data['user_answers']['control'] = 1
    else:
        context.user_data['user_answers']['control'] = 0

    await update.message.reply_text("🔥Отлично, остался последний вопрос! 3️⃣ GPS- антенна")
    await update.message.reply_text(
        "Если вы часто даете машину чужие руки и вам важно отслеживать... Ваш вариант?",
        reply_markup=ReplyKeyboardMarkup(
            [["😎 С GPS- антенны", "📺БЕЗ GPS- антенны"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return GPS


async def gps_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "😎 С GPS- антенны":
        context.user_data['user_answers']['gps'] = 1
    else:
        context.user_data['user_answers']['gps'] = 0

    recommended = recommend_systems(context.user_data['user_answers'])
    recommendation_text = "🔍 Исходя из ваших ответов, я рекомендую рассмотреть следующие системы:\n\n"

    for system in recommended:
        recommendation_text += f"• <b>{system['name']}</b>\nСсылка: {system['link']}\n\n"

    recommendation_text += (
        "Оставьте ваш номер телефона и наш мастер свяжется с вами, чтобы назвать точную стоимость установки на ваш авто.\n\n"
        "📍ул. Фадеева, 51А\n"
        "@ya7fadeeva_bot\n\n"
        "📍Московское ш., 16 км, 1А\n"
        "@ya7moskva_bot"
    )

    context.user_data['bot_data'] = ", ".join([sys['name'] for sys in recommended])

    await update.message.reply_text(recommendation_text, parse_mode='HTML', disable_web_page_preview=True)
    await update.message.reply_text(
        "Пожалуйста, поделитесь вашим номером телефона:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Отправить мой номер", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.contact:
        phone_number = update.message.contact.phone_number
    else:
        phone_number = update.message.text

    form_data = {
        FORM_FIELD_NAME: context.user_data.get('user_name', 'Неизвестно'),
        FORM_FIELD_PHONE: phone_number,
        FORM_FIELD_DATA: context.user_data.get('bot_data', 'Данные не сформированы')
    }

    try:
        response = requests.post(WEBFORM_URL, data=form_data)
        if response.status_code == 200:
            await update.message.reply_text(
                "✅ Спасибо! Ваш номер и данные получены. Наш менеджер свяжется с вами!",
                reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
            )
        else:
            logger.error(f"Ошибка при отправке формы: {response.status_code}")
            await update.message.reply_text("✅ Спасибо! Ваши данные приняты. Мы свяжемся с вами скоро.")
    except Exception as e:
        logger.error(f"Исключение при отправке формы: {e}")
        await update.message.reply_text("✅ Спасибо! Ваш номер принят. Мы свяжемся с вами скоро.")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Диалог прерван. Чтобы начать заново, отправьте /start')
    context.user_data.clear()
    return ConversationHandler.END


def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AUTO_START: [MessageHandler(filters.TEXT & ~filters.COMMAND, autostart_choice)],
            CONTROL: [MessageHandler(filters.TEXT & ~filters.COMMAND, control_choice)],
            GPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, gps_choice)],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    main()