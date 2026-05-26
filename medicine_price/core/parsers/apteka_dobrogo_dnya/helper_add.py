import time
import re
import json

from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


def create_session():
    ua = UserAgent()
    session = requests.Session()
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
        total_pages = get_count_pages(html)

        data = get_data_html_page(html)
        if not data:
            return None
        list_preparaty.extend(drug for drug in data)
        while page < total_pages:
            page += 1
            url = f"https://www.add.ua/ua/catalogsearch/result/index/?p={page}&q={quote(query)}"

            response = session.get(url, headers=session.headers, timeout=10)
            response.raise_for_status()
            html = response.text

            data = get_data_html_page(html)
            list_preparaty.extend(drug for drug in data)
        session.close()
        print('Fall session')

        res = get_list_dict(list_preparaty)

        return res if res else None

    except Exception as e:
        print(f"Помилка Аптека доброго дня: {e}")
        time.sleep(10)  # Довша пауза при помилці
    return None


def get_list_dict(list_search_preparaty):
    return [
        {
            'productID': int(drug['id']),
            'productName': drug['name'],
            'productAvail': True,
            'productPrice': drug['price'],
            'alias': f'https://www.add.ua/ua/catalogsearch/result/?q={drug["name"]}',
            'pharmacy': 'Аптека доброго дня',
        }
        for drug in list_search_preparaty
    ]


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
        print(f"Помилка get_data_html_page Аптека доброго дня: {e}")
        time.sleep(10)  # Довша пауза при помилці

    return None


def get_count_pages(html):
    soup = BeautifulSoup(html, "html.parser")

    pages_element = soup.select_one(".items-count .page")

    if not pages_element:
        return 1

    try:
        return int(pages_element.text.strip())
    except ValueError:
        return 1