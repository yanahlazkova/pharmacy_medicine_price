import json
import re
import time

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from urllib.parse import quote, urljoin


def create_session():
    ua = UserAgent()
    session = requests.Session()
    print('Start session 1sa')

    session.headers.update({
        'User-Agent': ua.random,
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


def search_preparaty(query, session_key):
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

        soup = BeautifulSoup(html, "html.parser")

        # отримаємо кількість сторінок
        total_pages = get_count_pages(soup)

        data = get_data_html_page(soup)

        if not data:
            return None, None

        list_preparaty.extend(drug for drug in data if query.casefold() in drug['name'].casefold())

        while page < total_pages:
            page += 1
            url = f'https://1sa.com.ua/catalogsearch/result/index/?p={page}&q={quote(query)}'
            # url = f"https://1sa.com.ua/ua/catalogsearch/result/index/?p={page}&q={quote(query)}"

            response = session.get(url, timeout=30)
            response.raise_for_status()
            html = response.text

            soup = BeautifulSoup(html, "html.parser")

            data = get_data_html_page(soup)
            list_preparaty.extend(drug for drug in data if query.casefold() in drug['name'].casefold())

        session.close()
        print('Fall session')

        return list_preparaty

    except Exception as e:
        print(f"Помилка Перша соціальна аптека: {e}")
        time.sleep(10)  # Довша пауза при помилці
        return None


def get_count_pages(soup):
    # отримати кількість сторінок
    pages_count = soup.select_one("li.items-count strong.page")

    if not pages_count:
        return 1
    try:
        return int(pages_count.text.strip())
    except ValueError:
        return 1


def get_data_html_page(soup):
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

            # match = re.search(r'\[.*\]', text, re.DOTALL)
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
