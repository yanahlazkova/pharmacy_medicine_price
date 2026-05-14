""" методи парсингу """
import re
import time
import json
import requests
import random

from bs4 import BeautifulSoup
from django.db.models.functions import Lower
from fake_useragent import UserAgent
from urllib.parse import urljoin, quote

from core.parsers.helper_parser import LIST_PREPARATY
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
                       f.name != 'productNameNormalized' and
                       f.name != 'id' and f.name != 'img' and f.name != 'category'
                       and f.name != 'time_created' and f.name != 'time_updated']

    drug_data = {}
    for field in included_fields:
        drug_data[field] = product.get(field, None)

    drug_data['category'] = category_url
    drug_data['productNameNormalized'] = drug_data['productName'].casefold()
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


""" Search """

"""
{result: "success", data: {query: "парацетамол",…}}
data: {query: "парацетамол",…}
qnt_fuzzy
: false
qnt_hints: 1
qnt_indexes: 13
qnt_products: false
query: "парацетамол"
results: [{hint: 1, logID: 7396249, type: 1, alias: "/drugs/paratsetamol-d2238", indexID: "220225",…}, {,…},…]
0: {hint: 1, logID: 7396249, type: 1, alias: "/drugs/paratsetamol-d2238", indexID: "220225",…}
1: {,…}
2: {analizeStr: "Парацетамол Беби", analizeStr2: "Парацетамол Бебі", indexID: 364612,…}

"""


def update_drugs_apteka911(product_name):
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


def search_preparaty(query):
    """ пошук за назвою препарата """
    session = create_session()

    api_url = "https://apteka911.ua/ua/shop/search"

    payload = {
        'q': query,
        'checkUrl': True,
    }

    try:
        # ЗАПИТ ДО API ЗА КИРИЛИЧНОЮ НАЗВОЮ
        response = session.post(api_url, headers=session.headers, data=payload, timeout=10)
        response.raise_for_status()
        json_data = response.json()
        json_url = json_data['data']['url']
        if json_url:
            url = f'https://apteka911.ua/ua{json_url}'
        else:
            url = f"https://apteka911.ua/ua/shop/search?query={quote(query)}"
            response = session.get(url, headers=session.headers, timeout=10)
            response.raise_for_status()
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')



        products = get_data_html_page(session, url)
        LIST_PREPARATY.extend(
            product for product in products
            if is_valid_product(product, query)
        )
        print(f'{len(LIST_PREPARATY)} PRODUCTS FOUND')

        return LIST_PREPARATY

        # is_products = json_data.get("data", {}).get("qnt_products", False)
        #
        # results = json_data.get("data", {}).get("results", [])
        #
        # if not is_products:
        #     # перебрати категорії
        #     for item in results:
        #         alias = item.get("alias")
        #
        #         if alias:
        #             print(alias)
        #
        #             # 2. отримання товарів по alias
        #             # payload_alias = {
        #             #     "pushHistory": "true",
        #             #     "alias": alias,
        #             # }
        #             #
        #             # response2 = session.post(
        #             #     "https://apteka911.ua/ua/shop/search",
        #             #     headers=session.headers,
        #             #     data=payload_alias,
        #             # )
        #             url = "https://apteka911.ua" + alias
        #             response2 = session.get(url, headers=session.headers)
        #             response2.raise_for_status()
        #             response_html = response2.text
        #             get_data_html_page(response_html, response2)

            # for item in results:
            #     parse_category_for_search(session, item['alias'], query)
        # else:
        #     # повернути знайдені препарати
        #     return LIST_PREPARATY
    #
    except Exception as e:
        print(f"Помилка: {e}")
        time.sleep(10)  # Довша пауза при помилці


def get_data_html_page(session, url):
    response = session.get(url)
    html = response.text
    print('"products":' in html)
    match = re.search(
        r'"products":(\[\{.*?\}\])',
        html,
        re.DOTALL
    )

    if not match:
        print("PRODUCTS NOT FOUND")
        return

    products_json = match.group(1)
    products = json.loads(products_json)

    return products



# def parse_category_for_search(session, category_url, query):
#     requests_count = 0  # для перерви/відпочинку
#     page = 1
#     while True:
#         url = f"https://apteka911.ua/ua{category_url}/page={page}"
#         headers = {
#             "Referer": url
#         }
#
#         # data_json = fetch_page(session, paged_url)
#         # response = session.post(paged_url, headers=session.headers, data=payload, timeout=10)
#         response = session.post(url, headers=session.headers, timeout=10)
#         response.raise_for_status()
#         data_json = response.json()
#
#         if not data_json:
#             break
#
#         ajax_products = data_json.get("data", {}).get("ajax_products", [])
#
#         # перевірка за дублікатами, пошуковим словом, наявністю
#         LIST_PREPARATY.extend(
#             product for product in ajax_products
#             if is_valid_product(product, query)
#         )
#
#         last_page = data_json.get('data', {}).get('pages', {}).get('npages', 1)
#
#         print(f"Page {page}: {len(ajax_products)} products: {category_url}")
#
#         if page >= last_page:
#             break
#
#         requests_count += 1
#         page += 1
#
#         # anti-rate limit
#         time.sleep(random.uniform(1, 3))
#
#         if requests_count % 50 == 0:
#             # save_to_file(LIST_PREPARATY, 'apteka911.json')
#
#             time.sleep(random.uniform(20, 40))


def is_valid_product(product, query):
    if product['productAvail'] != 'yes':
        return False

    if product['productID'] in SEEN_PRODUCT_ID:
        return False

    if query.casefold() not in product['productName'].casefold():
        return False

    SEEN_PRODUCT_ID.add(product['productID'])

    return True
