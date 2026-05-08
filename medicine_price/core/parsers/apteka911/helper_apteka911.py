""" методи парсингу """
import time
import json
import requests
import random

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urljoin

from pharmacies.models import CategoryApteka911, DrugApteka911

SEEN_URLS = set()  # для збору url категорій

SEEN_PRODUCT_ID = set()  # для збору id препаратів
EXISTING_PRODUCTS: list[dict] = []  # існучі в БД
BATCH_TO_CREATE: list[dict] = []  # партія/пакет для створення
BATCH_TO_UPDATE: list[dict] = []  # партія/пакет для оновлення

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
    print('save to file')
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
    """ отримання json-даних сторінки """
    headers = {
        "Referer": url
    }

    response = session.get(url, headers=headers, timeout=10)
    response.raise_for_status()

    if "application/json" in response.headers.get("Content-Type", ""):
        return response.json()

    return None


def build_image_url(drug):
    try:
        return (
                "https://apteka911.ua"
                + drug.get('dataUrl', '')
                + drug.get('productThumbs', {}).get('webpmid', {}).get('file', '')
        )
    except:
        try:
            return (
                    "https://apteka911.ua"
                    + drug.get('dataUrl', '')
                    + drug.get('productThumbs', {}).get('mid', {}).get('file', '')
            )
        except:
            return None


def create_obj_model_drug_apteka911(product, category_url):
    included_fields = [f.name for f in DrugApteka911._meta.fields if
                       f.name != 'productAvail' and
                       f.name != 'id' and f.name != 'img' and f.name != 'category'
                       and f.name != 'time_created' and f.name != 'time_updated']

    drug_data = {}
    for field in included_fields:
        drug_data[field] = product.get(field, None)

    drug_data['category'] = category_url
    drug_data['productAvail'] = True if product.get('productAvail') == 'yes' else False
    # отримання даних картинки
    drug_data['img'] = build_image_url(product)

    obj = DrugApteka911(**drug_data)
    return obj


def prepare_drug_for_sync(products, category_url):
    """ перевіряє дублікати
        визначає create/update
        готує об’єкт"""

    for product in products:

        product_id = product.get('productID')

        if product_id in SEEN_PRODUCT_ID:
            continue
        else:
            SEEN_PRODUCT_ID.add(product_id)

        # створити об'єкт-модель
        drug_obj = create_obj_model_drug_apteka911(product, category_url)

        # є в БД → update
        if product_id not in EXISTING_PRODUCTS:
            BATCH_TO_CREATE.append(drug_obj)
        # нема → create
        else:
            drug_obj.id = EXISTING_PRODUCTS[product_id]  # .get(product_id)
            BATCH_TO_UPDATE.append(drug_obj)


def parse_category(session, category_url):
    requests_count = 0  # для перерви/відпочинку
    page = 1
    while True:
        paged_url = f"{category_url}/page={page}"

        data = fetch_page(session, paged_url)

        if not data:
            break

        products = data.get("data", {}).get("ajax_products", [])

        prepare_drug_for_sync(products, category_url)

        last_page = data.get('data', {}).get('pages', {}).get('npages', 1)

        print(f"Page {page}: {len(products)} products: {category_url}")

        if page >= last_page:
            break

        requests_count += 1
        page += 1

        # anti-rate limit
        time.sleep(random.uniform(1, 3))

        if requests_count % 50 == 0:
            # save_to_file(LIST_PREPARATY, 'apteka911.json')

            time.sleep(random.uniform(20, 40))


def save_to_db():
    try:
        DrugApteka911.objects.bulk_update(BATCH_TO_UPDATE,
                                          ['category',
                                           'img',
                                           'productName',
                                           'alias',
                                           'brandName',
                                           'formName',
                                           'productAvail',
                                           'productCountry',
                                           'productForm',
                                           'productMeasure',
                                           'productMname',
                                           'productPrice',
                                           ], batch_size=100)
        print(f'update {len(BATCH_TO_UPDATE)} products')
    except Exception as e:
        print(f"[DB ERROR] (update): {e}")

    try:
        DrugApteka911.objects.bulk_create(BATCH_TO_CREATE, batch_size=100)
        print(f'create {len(BATCH_TO_CREATE)} products')

    except Exception as e:
        print(f"[DB ERROR] (insert): {e}")


def update_drugs_apteka911(categories):
    global EXISTING_PRODUCTS
    EXISTING_PRODUCTS = {
        drug.productID: drug.id
        for drug in DrugApteka911.objects.only('id', 'productID')
    }

    session = create_session()
    count = 0
    for cat in categories:
        id, url = cat
        count += 1
        print(f'category {count}: {url}')

        parse_category(session, url)

        if len(BATCH_TO_UPDATE) >= 500 or len(BATCH_TO_CREATE) >= 500:
            save_to_db()
            BATCH_TO_UPDATE.clear()
            BATCH_TO_CREATE.clear()

    save_to_db()


""" Search """





def search_preparaty(query):
    session = create_session()

    api_url = "https://apteka911.ua/ua/shop/search"

    payload = {
        'q': query,
    }

    try:
        # ЗАПИТ ДО API ЗА КИРИЛИЧНОЮ НАЗВОЮ
        response = session.post(api_url, headers=session.headers, data=payload, timeout=10)
        response.raise_for_status()
        json_data = response.json()
        alias_category = json_data.get("data", {}).get("results", [])[0]['alias']
        url_category = f'https://apteka911.ua/ua{alias_category}'
        res = session.post(url_category, headers=session.headers, timeout=10)
        res.raise_for_status()
        json_data = res.json()
        return json_data

    except Exception as e:
        print(f"Помилка: {e}")
        time.sleep(10)  # Довша пауза при помилці
