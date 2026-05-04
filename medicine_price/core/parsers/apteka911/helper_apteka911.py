""" методи парсингу """
import time
import json
import requests
import random

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urljoin

from pharmacies.models import CategoryApteka911, DrugApteka911

SEEN_URLS = set()
LIST_PREPARATY = []

""" парсер html-сторінки Головного меню (Категорії) """


def get_categories_apteka911():
    ua = UserAgent()
    session = requests.Session()
    url = 'https://apteka911.ua/ua'

    response = session.get(url, headers={"User-Agent": ua.random})

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "x-requested-with": "XMLHttpRequest",  # КРИТИЧНО: саме це каже серверу віддати JSON
        # Referer має бути ПОВНИМ URL сторінки препарату
        "referer": f"https://apteka911.ua/ua",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    session.cookies.update({
        'site_version': 'desktop',
        'wucmf_region': '89',
        # 'PHPSESSID': '601c139cc7ac20fdcbecfdfd55095eb8'
    })

    try:
        response = session.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text
        soup = BeautifulSoup(html, 'html.parser')

        templates = soup.find_all('script', {'type': 'text/x-template'})

        for tpl in templates:
            if 'menu-catalog__list' in tpl.text:
                inner_soup = BeautifulSoup(tpl.text, 'html.parser')
                main_menu = inner_soup.find_all('ul', class_='menu-catalog__list')

                categories = []

                for a in main_menu[0].select('a[data-link-self-path]'):
                    name = a.get_text(strip=True)
                    path = a.get('data-link-self-path')

                    if not path:
                        continue

                    url = urljoin('https://apteka911.ua', path)

                    if path and path in SEEN_URLS:
                        continue
                    else:
                        SEEN_URLS.add(url)

                        categories.append({
                            "name": name,
                            "url": url
                        })

                return categories


    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        return None


def save_to_file(data, file_name):
    with open(file_name, 'w') as f:
        json.dump(data, f, indent=4)


def update_categories_db(categories):
    """ оновлення категорій в БД """
    for cat in categories:
        obj_category, _ = CategoryApteka911.objects.update_or_create(
            url=cat['url'],
            defaults={"name": cat['name']},
        )
        print(obj_category)


""" парсер json (препарати Аптека911) по категоріям """


def update_drugs_apteka911(categories):
    session = create_session()

    for cat in categories:
        url, name = cat

        parse_category(session, url)


def create_session():
    ua = UserAgent()
    session = requests.Session()

    session.headers.update({
        "User-Agent": ua.random,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
    })

    # ініціалізація cookies
    session.get("https://apteka911.ua/ua")

    session.cookies.update({
        "site_version": "desktop",
        "wucmf_region": "89",
    })

    return session


def fetch_page(session, url):
    headers = {
        "Referer": url
    }

    response = session.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    if "application/json" in response.headers.get("Content-Type", ""):
        return response.json()

    return None


def add_list(products):
    included_fields = [f.name for f in DrugApteka911._meta.fields if
                       f.name != 'id' and f.name != 'img' and f.name != 'category'
                       and f.name != 'time_created' and f.name != 'time_updated']

    for product in products:
        drug = {}
        for field in included_fields:
            drug = {
                field: product[field]
            }
        LIST_PREPARATY.append(drug)





def parse_category(session, url):
    page = 1

    while True:
        paged_url = f"{url}?PAGEN_1={page}"

        data = fetch_page(session, paged_url)

        if not data:
            break

        products = data.get("data", {}).get("ajax_products", [])
        add_list(products)

        if not products:
            break

        print(f"Page {page}: {len(products)} products")

        page += 1

        # anti-rate limit
        time.sleep(random.uniform(1, 3))
