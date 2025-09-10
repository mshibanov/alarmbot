import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re


class SimpleFormHandler:
    def __init__(self, form_url):
        self.form_url = form_url
        self.base_url = self.get_base_url(form_url)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        })

    def get_base_url(self, url):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def analyze_form(self):
        """Анализирует форму и возвращает необходимые поля"""
        try:
            response = self.session.get(self.form_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            form = soup.find('form')
            if not form:
                return None

            # Получаем action формы
            form_action = form.get('action', '')
            if form_action.startswith('/'):
                form_action = urljoin(self.base_url, form_action)
            elif not form_action.startswith(('http://', 'https://')):
                form_action = self.form_url

            # Находим обязательные поля
            required_fields = []
            for input_tag in form.find_all(['input', 'textarea', 'select']):
                if input_tag.get('required') and input_tag.get('name'):
                    field_name = input_tag.get('name')
                    field_type = input_tag.get('type', 'text')
                    required_fields.append({
                        'name': field_name,
                        'type': field_type,
                        'label': self.get_field_label(input_tag)
                    })

            return {
                'action': form_action,
                'method': form.get('method', 'post').lower(),
                'required_fields': required_fields,
                'all_fields': [tag.get('name') for tag in form.find_all(['input', 'textarea', 'select']) if
                               tag.get('name')]
            }

        except Exception as e:
            print(f"Error analyzing form: {e}")
            return None

    def get_field_label(self, input_tag):
        """Пытается найти label для поля"""
        # Ищем по id
        field_id = input_tag.get('id')
        if field_id:
            label = input_tag.find_previous('label', {'for': field_id})
            if label:
                return label.get_text(strip=True)

        # Ищем ближайший текст
        parent = input_tag.parent
        if parent:
            label = parent.find('label')
            if label:
                return label.get_text(strip=True)

        return "Неизвестное поле"

    def submit_phone_only(self, phone_number):
        """Отправляет форму только с телефоном"""
        try:
            response = self.session.get(self.form_url)
            soup = BeautifulSoup(response.text, 'html.parser')

            form = soup.find('form')
            if not form:
                return False, "Form not found"

            # Получаем action
            form_action = form.get('action', '')
            if form_action.startswith('/'):
                form_action = urljoin(self.base_url, form_action)
            elif not form_action.startswith(('http://', 'https://')):
                form_action = self.form_url

            # Собираем все скрытые поля
            form_data = {}
            for input_tag in form.find_all('input', type='hidden'):
                name = input_tag.get('name')
                value = input_tag.get('value', '')
                if name:
                    form_data[name] = value

            # Находим поле для телефона
            phone_field = None
            for input_tag in form.find_all(['input', 'textarea']):
                name = input_tag.get('name')
                if name and any(phone_word in name.lower() for phone_word in ['phone', 'tel', 'telephone', 'mobile']):
                    phone_field = name
                    break

            # Если не нашли по имени, ищем по типу
            if not phone_field:
                for input_tag in form.find_all('input', type='tel'):
                    name = input_tag.get('name')
                    if name:
                        phone_field = name
                        break

            # Если все еще не нашли, используем первое текстовое поле
            if not phone_field:
                for input_tag in form.find_all(['input', 'textarea']):
                    if input_tag.get('type') in ['text', None] and input_tag.get('name'):
                        phone_field = input_tag.get('name')
                        break

            if phone_field:
                form_data[phone_field] = phone_number

            # Отправляем форму
            method = form.get('method', 'post').lower()
            if method == 'post':
                response = self.session.post(form_action, data=form_data, headers={
                    'Referer': self.form_url,
                    'Origin': self.base_url
                })
            else:
                response = self.session.get(form_action, params=form_data, headers={
                    'Referer': self.form_url
                })

            # Проверяем успешность
            if response.status_code == 200:
                # Дополнительная проверка по содержимому
                if any(word in response.text.lower() for word in ['success', 'спасибо', 'thank']):
                    return True, "Form submitted successfully"
                return True, "Form submitted (status 200)"
            else:
                return False, f"Server returned status: {response.status_code}"

        except Exception as e:
            return False, f"Error: {str(e)}"