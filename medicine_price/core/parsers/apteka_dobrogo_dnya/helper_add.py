import time
import re
import json

from django.utils import timezone
from datetime import timedelta

from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from home.models import SearchResult


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


def search_preparaty(query, session_key):
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
        list_preparaty.extend(drug for drug in data if query.casefold() in drug['name'].casefold())
        while page < total_pages:
            page += 1
            url = f"https://www.add.ua/ua/catalogsearch/result/index/?p={page}&q={quote(query)}"

            response = session.get(url, headers=session.headers, timeout=10)
            response.raise_for_status()
            html = response.text

            data = get_data_html_page(html)
            list_preparaty.extend(drug for drug in data if query.casefold() in drug['name'].casefold())
        session.close()
        print('Fall session')

        # res = get_list_dict(list_preparaty)
        # return res if res else None

        # зберегти в БД
        is_save = save_search_results(query,list_preparaty, session_key)

        return len(is_save)


    except Exception as e:
        print(f"Помилка Аптека доброго дня: {e}")
        time.sleep(10)  # Довша пауза при помилці
    return None


# не використовується
def search_drugs_autocomplete(query, session_key):
    """ autocomplete API, тобто дає швидкі результати
    пошуку, але не обов’язково весь каталог"""

    url = f"https://add-api.evinent.site/api/search/autocomplete/1/1/{query}/true/"

    r = requests.get(url, headers={
        "Origin": "https://www.add.ua",
        "Referer": "https://www.add.ua/ua/borispil/",
        "User-Agent": "Mozilla/5.0",
    }, timeout=10)
    data = r.json()

    for p in data["products"]:
        print(p["code"], p["title"], p["price"], p["isAvailable"])



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
                pharmacy='Аптека доброго дня',
                price=drug['price'],
                alias= drug['alias'],# f'https://www.add.ua/ua/catalogsearch/result/?q={drug["name"]}',
                brand=drug.get('brand', ''),
                image_url=drug.get('image', ''),
                stock_status=(
                    SearchResult.StockStatus.UNKNOWN
                ),
            )
        )

    return SearchResult.objects.bulk_create(objects)


# не використовується
def get_list_dict(list_search_preparaty):
    """ створює словник зі списку знайдених препаратів """
    return [
        {
            'productID': int(drug['id']),
            'productName': drug['name'],
            'productAvail': True,
            'productPrice': drug['price'],
            'image': drug.get('image'),
            'alias': drug.get('alias'), # f'https://www.add.ua/ua/catalogsearch/result/?q={drug["name"]}',
            'pharmacy': 'Аптека доброго дня',
        }
        for drug in list_search_preparaty
    ]


def get_url_from_srcset(srcset):
    if not srcset:
        return None

    candidates = [
        part.strip().split()[0]
        for part in srcset.split(',')
        if part.strip()
    ]

    return candidates[-1] if candidates else None


def get_product_url(card):
    """ отримати посилання на сторінку препарату """

    link = card.select_one('a.product-item-photo')

    if link:
        return link.get('href')
    else: return '#'


def get_product_image_url(card):
    """ отримати url картинки """
    image = card.select_one('img.product-image-photo')

    if image:
        for attr in ('src', 'data-src', 'data-original'):
            value = image.get(attr)
            if value:
                return urljoin('https://www.add.ua', value)

        image_url = get_url_from_srcset(
            image.get('srcset') or image.get('data-srcset')
        )
        if image_url:
            return urljoin('https://www.add.ua', image_url)

    source = card.select_one('picture source[srcset]')
    if source:
        image_url = get_url_from_srcset(source.get('srcset'))
        if image_url:
            return urljoin('https://www.add.ua', image_url)

    return None


def get_product_code(card):
    """ отримання коду препарату зі сторінки """

    form = card.select_one('form[data-product-sku]')
    if form and form.get('data-product-sku'):
        return form.get('data-product-sku').strip()

    sku = card.select_one('.product-item-sku')
    if sku:
        match = re.search(r'\d+', sku.get_text(strip=True))
        if match:
            return match.group(0)

    return None


def get_alias_and_images_by_code(html):
    """ отримання картинки зі сторінки html"""
    soup = BeautifulSoup(html, 'html.parser')
    images_by_code = {}

    for card in soup.select('li.product-item'):
        code = get_product_code(card)
        alias = get_product_url(card)
        image_url = get_product_image_url(card)

        if code:
            images_by_code[code] = {
                'alias': alias if alias else '#',
                'image': image_url if image_url else "",
            }

    return images_by_code


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
            alias_and_images_by_code = get_alias_and_images_by_code(html)

            for product in products:
                product_code = str(product.get('id', '')).strip()
                product['image'] = alias_and_images_by_code.get(product_code, '').get('image', '')
                product['alias'] = alias_and_images_by_code.get(product_code, '').get('alias', '')

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
