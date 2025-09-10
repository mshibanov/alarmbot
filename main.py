import logging
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from form_handler import SimpleFormHandler
from config import BOT_TOKEN, FORM_URL

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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


def start(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    context.user_data['user_name'] = user.first_name or user.username
    context.user_data['user_answers'] = {}

    update.message.reply_text(f"👋🏻 Привет, {user.first_name}!\n\nЯ помогу тебе выбрать систему на твой автомобиль!")
    update.message.reply_text("🦾 Давай определимся с тем, что должна уметь ваша сигнализации")
    update.message.reply_text("1️⃣ Нужен ли вам автозапуск?")
    update.message.reply_text(
        "🥶 В условиях нашего климата необходимо прогревать двигатель перед поездкой... Какую систему выберете?",
        reply_markup=ReplyKeyboardMarkup(
            [["С Автозапуском", "БЕЗ Автозапуска"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return AUTO_START


def autostart_choice(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if text == "С Автозапуском":
        context.user_data['user_answers']['autostart'] = 1
    else:
        context.user_data['user_answers']['autostart'] = 0

    update.message.reply_text("2️⃣ Как вы планируете управлять системой? Брелок или GSM-модуль")
    update.message.reply_text(
        "🙄 Существует устаревший способ управления системы через брелок... Что выберете?",
        reply_markup=ReplyKeyboardMarkup(
            [["😎Приложение в телефоне", "📺Брелок"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return CONTROL


def control_choice(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if text == "😎Приложение в телефоне":
        context.user_data['user_answers']['control'] = 1
    else:
        context.user_data['user_answers']['control'] = 0

    update.message.reply_text("🔥Отлично, остался последний вопрос! 3️⃣ GPS- антенна")
    update.message.reply_text(
        "Если вы часто даете машину чужие руки и вам важно отслеживать... Ваш вариант?",
        reply_markup=ReplyKeyboardMarkup(
            [["😎 С GPS- антенны", "📺БЕЗ GPS- антенны"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return GPS


def gps_choice(update: Update, context: CallbackContext) -> int:
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

    update.message.reply_text(recommendation_text, parse_mode='HTML', disable_web_page_preview=True)
    update.message.reply_text(
        "Пожалуйста, поделитесь вашим номером телефона:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Отправить мой номер", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return PHONE


def get_phone(update: Update, context: CallbackContext) -> int:
    if update.message.contact:
        phone_number = update.message.contact.phone_number
    else:
        phone_number = update.message.text

    # Отправляем данные через форму
    form_handler = SimpleFormHandler(FORM_URL)
    success, message = form_handler.submit_phone_only(phone_number)

    if success:
        update.message.reply_text(
            "✅ Спасибо! Ваш номер и данные получены. Наш менеджер свяжется с вами!",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )
    else:
        logger.error(f"Ошибка отправки формы: {message}")
        update.message.reply_text(
            "✅ Спасибо! Ваш номер принят. Мы свяжемся с вами скоро.",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )

    context.user_data.clear()
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Диалог прерван. Чтобы начать заново, отправьте /start')
    context.user_data.clear()
    return ConversationHandler.END


def main() -> None:
    # Создаем Updater и передаем ему токен бота
    updater = Updater(BOT_TOKEN, use_context=True)

    # Получаем диспетчер для регистрации обработчиков
    dp = updater.dispatcher

    # Настраиваем обработчик диалога (ConversationHandler)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AUTO_START: [MessageHandler(Filters.text & ~Filters.command, autostart_choice)],
            CONTROL: [MessageHandler(Filters.text & ~Filters.command, control_choice)],
            GPS: [MessageHandler(Filters.text & ~Filters.command, gps_choice)],
            PHONE: [
                MessageHandler(Filters.contact, get_phone),
                MessageHandler(Filters.text & ~Filters.command, get_phone)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Добавляем обработчик в диспетчер
    dp.add_handler(conv_handler)

    # Запускаем бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()