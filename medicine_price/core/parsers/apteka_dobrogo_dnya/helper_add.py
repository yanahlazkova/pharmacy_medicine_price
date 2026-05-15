import time
import re
import json

from urllib.parse import quote

import requests
from fake_useragent import UserAgent


def create_session():
    ua = UserAgent()
    with requests.Session() as session:
        print('Start session')

    # session = requests.Session()

        session.headers.update({
            "User-Agent": ua.random,
            # "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept": "text/html,application/xhtml+xml",
        })

        session.get("https://www.add.ua")

        session.cookies.update({
            'region': 'borispil'
        })

        return session

    print('End session')



def search_preparaty(query):
    """ пошук за назвою препарата """
    session = create_session()

    list_preparaty = []

    page = 1

    url = f"https://www.add.ua/ua/catalogsearch/result/?q={quote(query)}"

    try:
        response = session.get(url, headers=session.headers, timeout=10)
        response.raise_for_status()
        html = response.text
        # отримаємо кількість сторінок
        # total_pages = get_count_pages(html)

        data = get_data_html_page(html)
        if not data:
            return None
        list_preparaty.extend(drug for drug in data)
        # while page < total_pages:
        #     page += 1
        #     url = f"https://apteka911.ua/ua/shop/search/page={page}?query={quote(query)}"
        #
        #     response = session.get(url, headers=session.headers, timeout=10)
        #     response.raise_for_status()
        #     html = response.text
        #
        #     data = get_data_html_page(html)
        #     list_preparaty.extend(drug for drug in data)
        session.close()
        print('Fall session')

        return  list_preparaty if list_preparaty else None

    except Exception as e:
        print(f"Помилка: {e}")
        time.sleep(10)  # Довша пауза при помилці
    return None


def get_data_html_page(html):
    try:

        if 'products' in html:
            # match = re.search(r'products:(\[\{.*?\})', html, re.DOTALL)
            start = html.find('products:[{')
            end = html.find('},]};')
            text = html[start:end]

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
        print(f"Помилка: {e}")
        time.sleep(10)  # Довша пауза при помилці

    return None