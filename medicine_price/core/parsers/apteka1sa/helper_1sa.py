import json
import re
import time
from datetime import timedelta

import requests
from bs4 import BeautifulSoup
from django.utils import timezone
from fake_useragent import UserAgent

from urllib.parse import quote, urljoin

from core.parsers.apteka_dobrogo_dnya.helper_add import get_product_code, get_product_url, get_alias_and_images_by_code
from core.parsers.helper_parser import get_user_agent
from home.models import SearchResult


def create_session():
    ua = get_user_agent()
    session = requests.Session()
    print('Start session 1sa')

    session.headers.update({
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
        'accept-language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
        # Це заголовок каже: Я AJAX-запит, дай мені JSON”.
        # "X-Requested-With": "XMLHttpRequest",
    })
    try:
        session.get('https://1sa.com.ua/', timeout=10)

        session.cookies.update({
            "site_version": "desktop",
            'region': 'borispil',
        })

        return session

    except requests.exceptions.RequestException as e:
        print(f'Сайт Першої соціальної аптеки недоступний {e}')
        return None


def search_preparaty(request, query, session_key):
    """ пошук за назвою препарата """
    session = create_session()

    if not session:
        return None, f"\"Перша соціальна аптека\" зараз недоступна. Спробуйте пізніше."

    list_preparaty = []

    page = 1

    url = f'https://1sa.com.ua/catalogsearch/result/?q={quote(query)}'

    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        print(content_type)

        html = response.text

        # отримаємо кількість сторінок
        total_pages = get_count_pages(html)

        data = get_data_html_page(html)

        if not data:
            return None, None

        list_preparaty.extend(drug for drug in data if query.casefold() in drug['name'].casefold())

        # пошук даних з інших сторінок
        # while page < total_pages:
        #     page += 1
        #     url = f'https://1sa.com.ua/catalogsearch/result/index/?p={page}&q={quote(query)}'
        #
        #     response = session.get(url, timeout=15)
        #     response.raise_for_status()
        #     html = response.text
        #
        #     # soup = BeautifulSoup(html, "html.parser")
        #
        #     data = get_data_html_page(html)
        #     list_preparaty.extend(drug for drug in data if query.casefold() in drug['name'].casefold())

        session.close()
        print('Fall session')

        is_save = save_search_results(query,list_preparaty, session_key)

        return len(is_save), None

    except Exception as e:
        print(f"Помилка Перша соціальна аптека: {e}")
        time.sleep(10)  # Довша пауза при помилці
        return None, None


def get_count_pages(html):
    soup = BeautifulSoup(html, "html.parser")

    # отримати кількість сторінок
    pages_count = soup.select_one("li.items-count strong.page")

    if not pages_count:
        return 1
    try:
        return int(pages_count.text.strip())
    except ValueError:
        return 1


def get_data_html_page(html):
    soup = BeautifulSoup(html, "html.parser")
    products = get_data_with_script(soup)

    if not products:
        return None

    alias_and_images_by_code = get_alias_and_images_by_code(html)

    for product in products:
        product_code = str(product.get('id', '')).strip()
        product['image'] = alias_and_images_by_code.get(product_code, '').get('image', '')
        product['alias'] = alias_and_images_by_code.get(product_code, '').get('alias', '')

    return products


def get_data_with_script(soup):
    """ отримання json-даних зі скрипта на html-сторнці"""

    target_script = None

    for script in soup.find_all("script"):
        text = script.string or script.get_text()

        if "staticImpressions['search_result_list']" in text:
            target_script = text
            break

    if not target_script:
        raise ValueError("Скрипт з препаратами не знайдено")

    try:

        if 'products' in target_script:
            # match = re.search(r'products:(\[\{.*?\})', html, re.DOTALL)
            start = target_script.find('products:[{')
            end = target_script.find('},]};')
            text = target_script[start:end]

            if not text.endswith(']'):
                text += '}]'

            match = re.search(r'\[.*\]', text, re.DOTALL)

            if not match:
                print("PRODUCTS NOT FOUND")
                return None

            products_json = match.group(0)

            products = json.loads(products_json)

            return products
    except Exception as e:
        print(f"Помилка get_data_html_page 1sa: {e}")
        time.sleep(10)  # Довша пауза при помилці
        return None


def save_search_results(query, results, session_key):
    """
    Зберігає результати пошуку в БД
    """
    # Видалити дані, що існують більше 2 годин
    SearchResult.objects.filter(
        created_at__lt=timezone.now() - timedelta(hours=2)
    ).delete()

    objects = []

    for drug in results:
        objects.append(
            SearchResult(
                query=query,
                name=drug['name'],
                nameNormalized=drug['name'].casefold(),
                session_key=session_key,
                product_id=drug['id'],
                pharmacy='1 соціальна аптека',
                price=drug['price'],
                alias= drug['alias'],# f'https://www.add.ua/ua/catalogsearch/result/?q={drug["name"]}',
                brand=drug.get('brand', '') if drug.get('brand') else '',
                image_url=drug.get('image', ''),
                stock_status=(
                    SearchResult.StockStatus.UNKNOWN
                ),
            )
        )

    return SearchResult.objects.bulk_create(objects)
