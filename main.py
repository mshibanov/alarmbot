import os
import logging
import re
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from telegram.error import TelegramError
import requests
from bs4 import BeautifulSoup

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Проверяем токен
if not BOT_TOKEN:
    logger.error("❌ Токен бота не найден! Установите переменную окружения BOT_TOKEN")
    exit(1)

# Состояния диалога
AUTOSTART, CONTROL, GPS, PHONE = range(4)
user_data = {}

# Список продуктов
PRODUCTS_DATA = [
    {'name': 'Pandora DX-40R', 'autostart': 0, 'remote': 1, 'gsm': 0, 'gps': 0,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/pandora-dx-40r/'},
    {'name': 'Pandora DX-40RS', 'autostart': 1, 'remote': 1, 'gsm': 0, 'gps': 0,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/pandora-dx-40rs/'},
    {'name': 'PanDECT X-1800L v4 Light', 'autostart': 1, 'remote': 0, 'gsm': 1, 'gps': 0,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/pandect-x-1800l-v4-light/'},
    {'name': 'Pandora VX 4G Light', 'autostart': 1, 'remote': 0, 'gsm': 1, 'gps': 0,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/pandora-vx-4g-light/'},
    {'name': 'Pandora VX-4G GPS v2', 'autostart': 1, 'remote': 0, 'gsm': 1, 'gps': 1,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/pandora-vx-4g-gps-v2/'},
    {'name': 'Pandora VX 3100', 'autostart': 1, 'remote': 1, 'gsm': 1, 'gps': 1,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/pandora-vx-3100/'},
    {'name': 'StarLine A63 v2 ECO', 'autostart': 0, 'remote': 1, 'gsm': 0, 'gps': 0,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/starline-a63-v2-eco/'},
    {'name': 'StarLine А93 v2 ECO', 'autostart': 1, 'remote': 1, 'gsm': 0, 'gps': 0,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/starline-a93-v2-eco/'},
    {'name': 'StarLine S96 v2 ECO', 'autostart': 1, 'remote': 0, 'gsm': 1, 'gps': 0,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/starline-s96-v2-eco/'},
    {'name': 'StarLine S96 V2 LTE GPS', 'autostart': 1, 'remote': 0, 'gsm': 1, 'gps': 1,
     'link': 'https://ya7auto.ru/auto-security/car-alarms/starline-s96-v2-lte-gps/'}
]


def send_to_crm(phone_number, user_name=None):
    """Отправляет данные в CRM через веб-форму с правильными ID полей"""
    url = "https://ya7auto.ru/crm/form/iframe/3/"

    # Если имя не указано, используем "Клиент из Telegram"
    if not user_name:
        user_name = "Клиент из Telegram"

    # Подготавливаем данные формы с правильными ID полей
    form_data = {
        'firstname': user_name,  # ID поля для имени
        'phone': phone_number,  # ID поля для телефона
        'form_id': '3',  # ID формы из URL
        'utm_source': 'telegram_bot',
        'utm_medium': 'bot',
        'utm_campaign': 'auto_selection',
        'comment': 'Заявка из Telegram-бота по подбору автосигнализаций'
    }

    # Заголовки как у браузера
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'https://ya7auto.ru/',
    }

    try:
        logger.info(f"Отправка данных в CRM: {form_data}")

        # Отправляем POST запрос с данными формы
        response = requests.post(url, data=form_data, headers=headers, timeout=15)

        logger.info(f"Ответ CRM: {response.status_code}")

        # Проверяем успешность по статусу коду
        if response.status_code == 200:
            logger.info(f"✅ Данные успешно отправлены в CRM")
            return True
        else:
            logger.error(f"❌ Ошибка отправки формы: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"💥 Исключение при отправке в CRM: {str(e)}")
        return False


def validate_phone_number(phone):
    """Проверяет и форматирует номер телефона"""
    digits = re.sub(r'\D', '', str(phone))

    if len(digits) == 11:
        if digits.startswith('7'):
            return f"+7{digits[1:]}"
        elif digits.startswith('8'):
            return f"+7{digits[1:]}"
    elif len(digits) == 10:
        return f"+7{digits}"

    return None


def start(update: Update, context: CallbackContext) -> int:
    """Начинает опрос, задает первый вопрос."""
    user = update.message.from_user
    update.message.reply_text(
        f"👋🏻 Приветствуем, {user.first_name}!\n\n"
        "Готов помочь подобрать идеальную систему для твоего автомобиля!\n\n"
        "🦾 Давай определимся с ключевыми функциями\n\n"
        "☀️ Подавляющее большинство наших клиентов выбирают систему с главной целью — реализовать дистанционный запуск двигателя.\n\n"
        "В нашем климате прогрев двигателя перед поездкой — это необходимость. Даже при небольшом минусе это значительно снижает износ мотора.\n\n"
        "Ну и конечно, садиться в уже тёплый и комфортный салон — это просто приятно.\n\n"
        "Какая функция для вас в приоритете?",
        reply_markup=ReplyKeyboardMarkup(
            [["С автозапуском", "БЕЗ автозапуска"]],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return AUTOSTART


def autostart_choice(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор автозапуска и задает второй вопрос."""
    choice = update.message.text
    user_id = update.message.from_user.id
    user_data[user_id] = {'autostart': 1 if choice == 'С автозапуском' else 0}

    update.message.reply_text(
        "📡 Теперь давай выберем способ управления\n\n"
        "🙄 Есть устаревший метод — управление с брелока сигнализации. Его минус в нестабильном сигнале: есть риск не получить оповещение о тревоге. Поэтому мы рекомендуем более современный вариант — управление со смартфона.\n\n"
        "☺️ Через мобильное приложение ты сможешь дистанционно открывать и закрывать авто, отслеживать его местоположение и статус, настраивать датчики и многое другое. Главное — ты гарантированно получишь пуш-уведомление о любом происшествии, где бы ты ни был.\n\n"
        "Как вам удобнее управлять системой?",
        reply_markup=ReplyKeyboardMarkup(
            [["😎 Приложение в телефоне", "📺 Брелок"]],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return CONTROL


def control_choice(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор управления и задает третий вопрос."""
    choice = update.message.text
    user_id = update.message.from_user.id
    user_data[user_id]['control'] = 'app' if 'Приложение' in choice else 'remote'

    update.message.reply_text(
        "🔥 Отлично! Мы почти подобрали твою идеальную систему. Остался последний шаг.\n\n"
        "Если ты часто передаешь ключи другим людям или тебе критично важно отслеживать каждое перемещение автомобиля, то тебе нужна система со встроенным GPS-модулем.\n\n"
        "Он позволит тебе в реальном времени видеть точное местоположение машины, а в приложении можно будет посмотреть детальный маршрут ее поездки.\n\n"
        "Нужен ли вам GPS-модуль для отслеживания?",
        reply_markup=ReplyKeyboardMarkup(
            [["Да, нужен GPS", "Нет, не нужен"]],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return GPS


def gps_choice(update: Update, context: CallbackContext) -> int:
    """Обрабатывает выбор GPS, показывает рекомендацию и запрашивает телефон."""
    choice = update.message.text
    user_id = update.message.from_user.id
    user_data[user_id]['gps'] = 1 if 'Да' in choice else 0

    user_prefs = user_data[user_id]
    recommended_products = []

    # Логика подбора
    for product in PRODUCTS_DATA:
        if user_prefs['autostart'] == 1 and product['autostart'] == 0:
            continue
        if user_prefs['control'] == 'app' and product['gsm'] == 0:
            continue
        if user_prefs['gps'] == 1 and product['gps'] == 0:
            continue

        recommended_products.append(product)
        if len(recommended_products) == 2:
            break

    # Формируем сообщение с рекомендациями
    if recommended_products:
        message_text = "Вот отличные варианты для вас:\n\n"
        for prod in recommended_products:
            message_text += f"• <a href='{prod['link']}'>{prod['name']}</a>\n"
        message_text += "\nДля подробного обсуждения и оформления заказа оставьте, пожалуйста, ваш номер телефона. Наш специалист свяжется с вами в ближайшее время."
    else:
        message_text = "К сожалению, по вашим запросам не найдено подходящих систем. Оставьте ваш номер телефона, и наш специалист поможет вам с подбором вручную."

    update.message.reply_text(message_text, parse_mode='HTML', disable_web_page_preview=True)

    update.message.reply_text(
        "Пожалуйста, отправьте ваш номер телефона. Используйте кнопку ниже для удобства.",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Отправить мой номер", request_contact=True)], ["Ввести номер вручную"]],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return PHONE


def get_phone(update: Update, context: CallbackContext) -> int:
    """Обрабатывает полученный контакт и отправляет его в CRM."""
    phone_number = None
    user = update.message.from_user
    user_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name

    if update.message.contact:
        phone_number = validate_phone_number(update.message.contact.phone_number)
    elif update.message.text == "Ввести номер вручную":
        update.message.reply_text(
            "Пожалуйста, введите ваш номер телефона в формате +7XXX...",
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
        )
        return PHONE
    elif update.message.text != "Отмена":
        phone_number = validate_phone_number(update.message.text)

    if not phone_number:
        update.message.reply_text("Неверный формат номера. Пожалуйста, введите номер в формате +7XXX...")
        return PHONE

    # Показываем что идет отправка
    update.message.reply_text("⌛ Отправляем ваши данные в CRM...")

    # Отправляем в CRM (имя и телефон)
    success = send_to_crm(phone_number, user_name)

    if success:
        update.message.reply_text(
            "✅ Спасибо! Ваши данные приняты и отправлены менеджеру. Мы свяжемся с вами в ближайшее время!\n\n"
            "Для нового подбора нажмите /start",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )
    else:
        update.message.reply_text(
            "❌ Произошла ошибка при отправке данных. Пожалуйста, попробуйте позже или свяжитесь с нами по телефону.\n\n"
            "Для повторной попытки нажмите /start",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )

    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    """Отменяет опрос."""
    update.message.reply_text(
        'Диалог прерван. Если нужна помощь, начните заново с /start.',
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )
    return ConversationHandler.END


def error_handler(update: Update, context: CallbackContext):
    """Обрабатывает ошибки."""
    logger.error("Ошибка:", exc_info=context.error)


def main():
    """Запускает бота в polling режиме"""
    logger.info("🚀 Запуск бота в polling режиме...")

    # Создаем Updater (старая версия PTB)
    updater = Updater(BOT_TOKEN, use_context=True)

    # Получаем dispatcher для регистрации обработчиков
    dp = updater.dispatcher
    dp.add_error_handler(error_handler)

    # Обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AUTOSTART: [MessageHandler(Filters.regex('^(С автозапуском|БЕЗ автозапуска)$'), autostart_choice)],
            CONTROL: [MessageHandler(Filters.regex('^(😎 Приложение в телефоне|📺 Брелок)$'), control_choice)],
            GPS: [MessageHandler(Filters.regex('^(Да, нужен GPS|Нет, не нужен)$'), gps_choice)],
            PHONE: [
                MessageHandler(Filters.contact, get_phone),
                MessageHandler(Filters.text & ~Filters.command, get_phone)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(conv_handler)

    # Запускаем polling
    logger.info("✅ Бот запущен и ожидает сообщений...")
    updater.start_polling()

    # Запускаем бота до принудительной остановки
    updater.idle()


if __name__ == '__main__':
    main()