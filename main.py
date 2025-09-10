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
# Функция для сопоставления ответов и рекомендаций
def recommend_systems(answers):
    systems = [
        # Pandora системы с точными ценами
        {"name": "Pandora DX-40R", "brand": "pandora", "autostart": 0, "brelok": 1, "gsm": 0, "gps": 0,
         "price": "10 500 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-dx-40r/"},
        {"name": "Pandora DX-40RS", "brand": "pandora", "autostart": 1, "brelok": 1, "gsm": 0, "gps": 0,
         "price": "13 200 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-dx-40rs/"},
        {"name": "PanDECT X-1800L v4 Light", "brand": "pandora", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 0,
         "price": "18 900 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/pandect-x-1800l-v4-light/"},
        {"name": "Pandora VX 4G Light", "brand": "pandora", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 0,
         "price": "21 500 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-vx-4g-light/"},
        {"name": "Pandora VX-4G GPS v2", "brand": "pandora", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 1,
         "price": "26 800 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-vx-4g-gps-v2/"},
        {"name": "Pandora VX 3100", "brand": "pandora", "autostart": 1, "brelok": 1, "gsm": 1, "gps": 1,
         "price": "29 500 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/pandora-vx-3100/"},

        # Starline системы с точными ценами
        {"name": "StarLine A63 v2 ECO", "brand": "starline", "autostart": 0, "brelok": 1, "gsm": 0, "gps": 0,
         "price": "9 800 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/starline-a63-v2-eco/"},
        {"name": "StarLine А93 v2 ECO", "brand": "starline", "autostart": 1, "brelok": 1, "gsm": 0, "gps": 0,
         "price": "12 900 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/starline-a93-v2-eco/"},
        {"name": "StarLine S96 v2 ECO", "brand": "starline", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 0,
         "price": "17 200 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/starline-s96-v2-eco/"},
        {"name": "StarLine S96 V2 LTE GPS", "brand": "starline", "autostart": 1, "brelok": 0, "gsm": 1, "gps": 1,
         "price": "23 700 ₽", "link": "https://ya7auto.ru/auto-security/car-alarms/starline-s96-v2-lte-gps/"}
    ]

    # Сначала ищем строго подходящие системы по всем характеристикам
    perfect_matches = []
    for system in systems:
        if (system['autostart'] == answers.get('autostart') and
                (system['brelok'] == answers.get('control') or system['gsm'] == answers.get('control')) and
                system['gps'] == answers.get('gps')):
            perfect_matches.append(system)

    # Если нашли подходящие системы - возвращаем их
    if perfect_matches:
        return perfect_matches

    # Если нет строго подходящих, игнорируем GPS характеристику
    matches_without_gps = []
    for system in systems:
        if (system['autostart'] == answers.get('autostart') and
                (system['brelok'] == answers.get('control') or system['gsm'] == answers.get('control'))):
            matches_without_gps.append(system)

    return matches_without_gps


def autostart_choice(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if text == "😉 С Автозапуском":
        context.user_data['user_answers']['autostart'] = 1
    else:
        context.user_data['user_answers']['autostart'] = 0

    # Сообщение 2.1
    update.message.reply_text("2️⃣ Как планируешь управлять системой? Брелок или GSM-модуль")

    # Сообщение 2.2
    update.message.reply_text(
        "Можно управлять через брелок, но проблема в том, что сигнал тревоги от автомобиля до брелка не всегда стабилен и есть шанс не получить сигнал тревоги ⛔️\n\n"
        "Через приложение в телефоне в независимости от вашего местоположения вы получите сообщение в случае тревоги и сможете отправить команду на автозапуск 👏\n\n"
        "Что выберете❓",
        reply_markup=ReplyKeyboardMarkup(
            [["😎 Приложение в телефоне", "📵 Брелок"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return CONTROL


def control_choice(update: Update, context: CallbackContext) -> int:
    text = update.message.text
    if text == "😎 Приложение в телефоне":
        context.user_data['user_answers']['control'] = 1
    else:
        context.user_data['user_answers']['control'] = 0

    # Сообщение 3.1
    update.message.reply_text("🔥Отлично, остался последний вопрос! 3️⃣ GPS-антенна")

    # Сообщение 3.2
    update.message.reply_text(
        "🗺️Если вы часто даете машину чужие руки и вам важно отслеживать точное местоположение автомобиля, то вам необходимо выбрать систему с GPS.\n\n"
        "Ваш вариант❓",
        reply_markup=ReplyKeyboardMarkup(
            [["🕵🏻‍♂️ С GPS- антенны", "🙈 БЕЗ GPS- антенны"]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return GPS


# Добавляем рекомендованные системы с характеристиками и точными ценами
for system in recommended:
    brand_icon = "🐼" if system['brand'] == 'pandora' or 'pandect' in system['name'].lower() else "⭐"

    # Формируем характеристики
    characteristics = []
    if system['autostart'] == 1:
        characteristics.append("автозапуск")
    if system['brelok'] == 1:
        characteristics.append("брелок")
    if system['gsm'] == 1:
        characteristics.append("GSM-управление")
    if system['gps'] == 1:
        characteristics.append("GPS")

    functionality_text += (
        f"{brand_icon} <b>{system['name']}</b>\n"
        f"• Характеристики: {', '.join(characteristics)}\n"
        f"• Стоимость: {system['price']}\n"
        f"• Ссылка: {system['link']}\n\n"
    )


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