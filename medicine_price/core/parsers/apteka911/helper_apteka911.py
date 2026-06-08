""" методи парсингу """
import re
import time
import json
import requests
import random

from django.utils import timezone
from datetime import timedelta

from bs4 import BeautifulSoup
from django.db.models.functions import Lower
from fake_useragent import UserAgent
from urllib.parse import urljoin, quote

from core.parsers.helper_parser import LIST_PREPARATY
from home.models import SearchResult
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
                session.close()
                return categories


    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        session.close()
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
    with requests.Session() as session:
        print('Start session')
        # session = requests.Session()

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
    print('End session')


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

# не використовується
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


def create_obj_model_drug_apteka911(product, category_url=None):
    included_fields = [f.name for f in DrugApteka911._meta.fields if
                       f.name != 'productAvail' and
                       f.name != 'productNameNormalized' and
                       f.name != 'id' and f.name != 'img' and f.name != 'category'
                       and f.name != 'time_created' and f.name != 'time_updated']

    drug_data = {}
    for field in included_fields:
        drug_data[field] = product.get(field, None)

    if category_url:
        drug_data['category'] = category_url
    drug_data['productNameNormalized'] = drug_data['productName'].casefold()
    drug_data['productAvail'] = True if product.get('productAvail') == 'yes' else False
    # отримання даних картинки
    drug_data['img'] = drug_data['image']

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
    if BATCH_TO_UPDATE:
        try:
            DrugApteka911.objects.bulk_update(BATCH_TO_UPDATE,
                                              ['category',
                                               'img',
                                               'productName',
                                               'productNameNormalized',
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
    if BATCH_TO_CREATE:
        try:
            DrugApteka911.objects.bulk_create(BATCH_TO_CREATE, batch_size=100)
            print(f'create {len(BATCH_TO_CREATE)} products')

        except Exception as e:
            print(f"[DB ERROR] (insert): {e}")


def update_all_drugs_apteka911(categories):
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

    session.close()
    save_to_db()


""" Search: методи пошуку препаратів """

# не використовується
def update_drugs_apteka911(producty):
    drugs = DrugApteka911.objects.filter(productNameNormalized__icontains=product_name)
    for drug in drugs:
        print(f'{drug.productName}({drug.category}): {drug.productPrice}')

    global EXISTING_PRODUCTS
    EXISTING_PRODUCTS = {
        drug.productID: drug.id
        for drug in drugs
    }

    existing_url_categories = set(drug.category for drug in drugs)

    session = create_session()

    for url_category in existing_url_categories:

        parse_category(session, url_category)

        if len(BATCH_TO_UPDATE) >= 500 or len(BATCH_TO_CREATE) >= 500:
            save_to_db()
            BATCH_TO_UPDATE.clear()
            BATCH_TO_CREATE.clear()

    session.close()
    save_to_db()


# не використовується
def get_list_dict(list_search_preparaty):
    return [
        {
            'productID': int(drug['productID']),
            'productName': drug['productName'],
            'productAvail': drug['productAvail'],
            'productPrice': drug['productPrice'],
            'alias': drug["alias"],
            'pharmacy': 'Аптека 911',
        }
        for drug in list_search_preparaty
    ]


def search_preparaty(query, session_key):
    """ пошук за назвою препарата """



    session = create_session()

    list_search_preparaty = []

    page = 1

    url = f"https://apteka911.ua/ua/shop/search?query={quote(query)}"

    try:
        response = session.get(url, headers=session.headers, timeout=5)
        response.raise_for_status()
        html = response.text
        # отримаємо кількість сторінок
        total_pages = get_count_pages(html)

        data = get_data_html_page(html)
        if not data:
            return None

        list_search_preparaty.extend(drug for drug in data)

        while page < total_pages:
            page += 1
            print(f'page: {page}')
            url = f"https://apteka911.ua/ua/shop/search/page={page}?query={quote(query)}"

            response = session.get(url, headers=session.headers, timeout=10)
            response.raise_for_status()
            html = response.text

            data = get_data_html_page(html)
            list_search_preparaty.extend(drug for drug in data)

        session.close()
        print('Fall session')

        # for drug in list_search_preparaty:
        #     list_preparaty.append(create_obj_model_drug_apteka911(drug))

        # save_drugs_to_db(list_preparaty, query)

        # res = get_list_dict(list_search_preparaty)
        #
        # return res if res else None

        # зберегти в таблицю пошуку БД
        is_save = save_search_results(query, list_search_preparaty, session_key)

        return len(is_save)

    except Exception as e:
        print(f"Помилка apteka911: {e}")
        time.sleep(10)  # Довша пауза при помилці
    return None


def save_search_results(query, results, session_key):
    """
    Зберігає результати пошуку в БД
    """

    SearchResult.objects.filter(
        created_at__lt=timezone.now() - timedelta(hours=2)
    ).delete()

    objects = []

    for drug in results:
        objects.append(
            SearchResult(
                query=query,
                name=drug['productName'],
                nameNormalized=drug['productName'].casefold(),
                session_key=session_key,
                product_id=int(drug['productID']),
                pharmacy='Аптека 911',
                price=drug['productPrice'],
                alias=drug["alias"],
                brand=drug['tmName'],
                image_url=drug['image'],
                stock_status=(
                    SearchResult.StockStatus.IN_STOCK if drug['productAvail'] == 'yes' else SearchResult.StockStatus.OUT_OF_STOCK
                ),
            )
        )

    return SearchResult.objects.bulk_create(objects)


def get_count_pages(html):
    soup = BeautifulSoup(html, "html.parser")

    pages = soup.select(".pagination a")
    if not pages:
        # якщо кількість сторінок не знайдено, то сторінка одна
        return 1
    page_numbers = []

    for page in pages:

        text = page.get_text(strip=True)

        if text.isdigit():
            page_numbers.append(int(text))

    max_page = max(page_numbers)

    return max_page


def get_data_html_page(html):
    try:

        if '"products"' in html:
            match = re.search(
                r'"products":(\[\{.*?\}\])',
                html,
                re.DOTALL
            )

            if not match:
                print("PRODUCTS NOT FOUND")
                return None
            products_json = match.group(1)

            products = json.loads(products_json)

            images_by_alias = get_product_images_by_alias(html)

            prefix_alias = 'https://apteka911.ua/ua/shop'
            for product in products:
                # print(f'product name: {product["productName"]}')
                product['alias'] = f'{prefix_alias}/{product['alias'].lstrip('/')}'
                product_alias = str(product.get('alias', '')).strip()
                product['image'] = images_by_alias.get(product_alias)

            return products

    except Exception as e:
        print(f"Помилка get_data_html_page apteka911: {e}")
        time.sleep(10)  # Довша пауза при помилці

    return None


def get_product_alias(card):
    pass


def get_product_images_by_alias(html):
    soup = BeautifulSoup(html, "html.parser")
    images_by_alias = {}

    for card in soup.select('.b-prod__tile'):
        # alias із посилання
        link = card.select_one('a[href]')
        if not link:
            continue

        alias = link.get('href')
        image = card.select_one('picture > img')

        images_by_alias[alias] = image.get('src') if image else ""

    return images_by_alias




# не використовується
def is_valid_product(product, query):
    if product['productAvail'] != 'yes':
        return False

    if product['productID'] in SEEN_PRODUCT_ID:
        return False

    if query.casefold() not in product['productName'].casefold():
        return False

    SEEN_PRODUCT_ID.add(product['productID'])

    return True


# не використовується
def save_drugs_to_db(products, query):
    list_update = []
    list_create = []

    existing_products = {
        drug.productID: drug.id
        for drug in
        DrugApteka911.objects.only('id', 'productID')
    }

    if existing_products:

        for product in products:
            product_id = product.productID

            if product_id in existing_products:
                product.id = existing_products[product_id]
                list_update.append(product)
            else:
                list_create.append(product)

    else:
        list_create.extend(products)

    if list_update:
        try:
            DrugApteka911.objects.bulk_update(list_update,
                                              [
                                                  'productName',
                                                  'productNameNormalized',
                                                  'alias',
                                                  'productAvail',
                                                  'productMname',
                                                  'productPrice',
                                              ], batch_size=100)
            print(f'update {len(list_update)} products')
        except Exception as e:
            print(f"[DB ERROR] (update): {e}")
    if list_create:
        try:
            DrugApteka911.objects.bulk_create(list_create, batch_size=100)
            print(f'create {len(list_create)} products')

        except Exception as e:
            print(f"[DB ERROR] (insert): {e}")
