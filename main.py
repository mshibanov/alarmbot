import os
import logging
import re
import asyncio
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.error import Conflict, RetryAfter
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
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://ya7auto.ru',
        'Referer': 'https://ya7auto.ru/',
        'Connection': 'keep-alive',
    }

    try:
        logger.info(f"Отправка данных в CRM: {form_data}")

        # Создаем сессию для сохранения куки
        session = requests.Session()

        # Сначала получаем главную страницу для установки куки
        session.get('https://ya7auto.ru/', headers=headers, timeout=10)

        # Получаем саму форму iframe для получения CSRF токена и других скрытых полей
        form_response = session.get(url, headers=headers, timeout=10)

        # Парсим HTML формы чтобы найти скрытые поля
        soup = BeautifulSoup(form_response.text, 'html.parser')
        hidden_fields = {}

        # Ищем все скрытые поля формы
        for input_tag in soup.find_all('input', type='hidden'):
            if input_tag.get('name') and input_tag.get('value'):
                hidden_fields[input_tag['name']] = input_tag['value']

        # Добавляем скрытые поля к данным формы
        form_data.update(hidden_fields)

        logger.info(f"Полные данные для отправки: {form_data}")

        # Отправляем POST запрос с данными формы
        response = session.post(url, data=form_data, headers=headers, timeout=15)

        logger.info(f"Ответ CRM: {response.status_code}")

        # Проверяем успешность по статусу коду
        if response.status_code == 200:
            # Дополнительная проверка по содержанию ответа
            response_text = response.text.lower()
            success_indicators = ['успех', 'success', 'спасибо', 'thank', 'принято', 'отправлено']

            if any(indicator in response_text for indicator in success_indicators):
                logger.info(f"✅ Данные успешно отправлены в CRM")
                return True
            else:
                logger.warning(f"⚠️ Форма вернула 200, но без явных признаков успеха. Ответ: {response.text[:200]}...")
                # Все равно считаем успехом, так как сервер принял запрос
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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает опрос, задает первый вопрос."""
    user = update.message.from_user
    await update.message.reply_text(
        f"👋🏻 Приветствуем, {user.first_name}!\n\n"
        "Готов помочь подобрать идеальную систему для твоего автомобиля!\n\n"
        "🦾 Давай определимся с ключевыми функции...",
        reply_markup=ReplyKeyboardMarkup(
            [["С автозапуском", "БЕЗ автозапуска"]],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return AUTOSTART


async def autostart_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор автозапуска и задает второй вопрос."""
    choice = update.message.text
    user_id = update.message.from_user.id
    user_data[user_id] = {'autostart': 1 if choice == 'С автозапуском' else 0}

    await update.message.reply_text(
        "📡 Теперь давай выберем способ управления...",
        reply_markup=ReplyKeyboardMarkup(
            [["😎 Приложение в телефоне", "📺 Брелок"]],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return CONTROL


async def control_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор управления и задает третий вопрос."""
    choice = update.message.text
    user_id = update.message.from_user.id
    user_data[user_id]['control'] = 'app' if 'Приложение' in choice else 'remote'

    await update.message.reply_text(
        "🔥 Отлично! Мы почти подобрали твою идеальную систему...",
        reply_markup=ReplyKeyboardMarkup(
            [["Да, нужен GPS", "Нет, не нужен"]],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return GPS


async def gps_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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

    await update.message.reply_text(message_text, parse_mode='HTML', disable_web_page_preview=True)

    await update.message.reply_text(
        "Пожалуйста, отправьте ваш номер телефона. Используйте кнопку ниже для удобства.",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📞 Отправить мой номер", request_contact=True)], ["Ввести номер вручную"]],
            one_time_keyboard=True,
            resize_keyboard=True
        ),
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает полученный контакт и отправляет его в CRM."""
    phone_number = None
    user = update.message.from_user
    user_name = f"{user.first_name} {user.last_name}" if user.last_name else user.first_name

    if update.message.contact:
        phone_number = validate_phone_number(update.message.contact.phone_number)
    elif update.message.text == "Ввести номер вручную":
        await update.message.reply_text(
            "Пожалуйста, введите ваш номер телефона в формате +7XXX...",
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
        )
        return PHONE
    elif update.message.text != "Отмена":
        phone_number = validate_phone_number(update.message.text)

    if not phone_number:
        await update.message.reply_text("Неверный формат номера. Пожалуйста, введите номер в формате +7XXX...")
        return PHONE

    # Показываем что идет отправка
    await update.message.reply_text("⌛ Отправляем ваши данные в CRM...")

    # Отправляем в CRM (имя и телефон)
    success = send_to_crm(phone_number, user_name)

    if success:
        await update.message.reply_text(
            "✅ Спасибо! Ваши данные приняты и отправлены менеджеру. Мы свяжемся с вами в ближайшее время!\n\n"
            "Для нового подбора нажмите /start",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "❌ Произошла ошибка при отправке данных. Пожалуйста, попробуйте позже или свяжитесь с нами по телефону.\n\n"
            "Для повторной попытки нажмите /start",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет опрос."""
    await update.message.reply_text(
        'Диалог прерван. Если нужна помощь, начните заново с /start.',
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )
    return ConversationHandler.END


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает ошибки."""
    logger.error("Ошибка:", exc_info=context.error)


def main() -> None:
    """Запускает бота в polling режиме"""
    logger.info("🚀 Запуск бота в polling режиме...")

    # Создаем Application с обработкой конфликтов
    application = Application.builder() \
        .token(BOT_TOKEN) \
        .read_timeout(30) \
        .write_timeout(30) \
        .connect_timeout(30) \
        .pool_timeout(30) \
        .build()

    application.add_error_handler(error_handler)

    # Обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            AUTOSTART: [MessageHandler(filters.Regex("^(С автозапуском|БЕЗ автозапуска)$"), autostart_choice)],
            CONTROL: [MessageHandler(filters.Regex("^(😎 Приложение в телефоне|📺 Брелок)$"), control_choice)],
            GPS: [MessageHandler(filters.Regex("^(Да, нужен GPS|Нет, не нужен)$"), gps_choice)],
            PHONE: [
                MessageHandler(filters.CONTACT, get_phone),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Запускаем polling с обработкой ошибок
    logger.info("✅ Бот запущен и ожидает сообщений...")

    try:
        application.run_polling(
            drop_pending_updates=True,  # Игнорирует старые сообщения при запуске
            allowed_updates=Update.ALL_TYPES,
            close_loop=False
        )
    except Conflict as e:
        logger.error(f"⚠️ Конфликт: другой экземпляр бота уже запущен. {e}")
        logger.info("🔄 Перезапуск через 10 секунд...")
        asyncio.run(asyncio.sleep(10))
        main()  # Рекурсивный перезапуск
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        raise


if __name__ == '__main__':
    main()