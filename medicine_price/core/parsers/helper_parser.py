""" загальні методи парсингу """
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from fake_useragent import UserAgent

from home.models import Filters


def get_user_agent():

    ua = UserAgent()

    while True:
        user_agent = ua.random
        print(user_agent)

        if not any(x in user_agent for x in ("Android", "iPhone", "iPad", "Mobile")):
            return user_agent




def save_filters_to_db(query, filters, session_key, pharmacy_name):
    """
        Зберігає фільтри в БД
    """
    # очистити таблицю перед новим пошуком
    with transaction.atomic():
        Filters.objects.filter(
            query=query,
            session_key=session_key
        ).delete()

        Filters.objects.filter(
            created_at__lt=timezone.now() - timedelta(hours=2)
        ).delete()

    objects = []

    for filter_name in filters:
        for value in filters[filter_name]:
            objects.append(
                Filters(
                    query=query,
                    session_key=session_key,
                    pharmacy=pharmacy_name,
                    filter_name=filter_name,
                    filter_value=str(value),
                    nameNormalized=str(value).casefold(),
                )
            )

    res = Filters.objects.bulk_create(objects)
    print(f'{len(res)} filters created')

    return


# import time
# import json
# import requests
#
# from selenium import webdriver
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.by import By
# from bs4 import BeautifulSoup
# from fake_useragent import UserAgent
# from urllib.parse import urljoin
#
# from pharmacies.models import CategoryApteka911
#
#
#
# SEEN_URLS = set()
# LIST_PREPARATY = []
#
#
# def get_categories_apteka911():
#     ua = UserAgent()
#     session = requests.Session()
#     url = 'https://apteka911.ua/ua'
#
#     response = session.get(url, headers={"User-Agent": ua.random})
#
#     headers = {
#         "accept": "application/json, text/javascript, */*; q=0.01",
#         "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
#         "x-requested-with": "XMLHttpRequest",  # КРИТИЧНО: саме це каже серверу віддати JSON
#         # Referer має бути ПОВНИМ URL сторінки препарату
#         "referer": f"https://apteka911.ua/ua",
#         "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
#     }
#     session.cookies.update({
#         'site_version': 'desktop',
#         'wucmf_region': '89',
#         # 'PHPSESSID': '601c139cc7ac20fdcbecfdfd55095eb8'
#     })
#
#     try:
#         response = session.get(url, headers=headers, timeout=10)
#         response.raise_for_status()
#         html = response.text
#         soup = BeautifulSoup(html, 'html.parser')
#
#         templates = soup.find_all('script', {'type': 'text/x-template'})
#
#         for tpl in templates:
#             if 'menu-catalog__list' in tpl.text:
#                 inner_soup = BeautifulSoup(tpl.text, 'html.parser')
#                 main_menu = inner_soup.find_all('ul', class_='menu-catalog__list')
#
#                 categories = []
#
#                 for a in main_menu[0].select('a[data-link-self-path]'):
#                     name = a.get_text(strip=True)
#                     path = a.get('data-link-self-path')
#
#                     if not path:
#                         continue
#
#                     url = urljoin('https://apteka911.ua', path)
#
#                     if path and path in SEEN_URLS:
#                         continue
#                     else:
#                         SEEN_URLS.add(url)
#
#                         categories.append({
#                             "name": name,
#                             "url": url
#                         })
#
#                 return categories
#
#
#     except requests.exceptions.HTTPError as e:
#         print(f"HTTP error: {e}")
#         return None
#
#
# def save_to_file_categories(categories):
#     with open('categories.json', 'w') as f:
#         json.dump(categories, f, indent=4)
#
#
# def update_categories_db(categories):
#     """ оновлення категорій в БД """
#     for cat in categories:
#         obj_category, _ = CategoryApteka911.objects.update_or_create(
#             url=cat['url'],
#             defaults={"name": cat['name']},
#         )
#         print(obj_category)
#
#
# """ парсер препаратів Аптека911 """
#
# def update_drugs_apteka911(categories):
#     ua = UserAgent()
#     base_url = 'https://apteka911.ua/ua'
#     session = requests.Session()
#
#     response = session.get(base_url, headers={'User-Agent': ua.random})
#
#     headers_base = {
#         "accept": "application/json, text/javascript, */*; q=0.01",
#         "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
#         "x-requested-with": "XMLHttpRequest",  # КРИТИЧНО: саме це каже серверу віддати JSON
#         # Referer має бути ПОВНИМ URL сторінки препарату
#         "referer": base_url,
#         "user-agent": ua.random,
#     }
#
#     session.cookies.update({
#         'site_version': 'desktop',
#         'wucmf_region': '89',
#         # 'PHPSESSID': '601c139cc7ac20fdcbecfdfd55095eb8'
#     })
#
#     for category in categories:
#         url, name = category
#         # Змінюємо User-Agent для кожного запиту
#         headers = headers_base.copy()
#         headers['User-Agent'] = ua.random
#
#         try:
#             response = session.get(url, headers=headers, timeout=10)
#             response.raise_for_status()
#             content_type = response.headers.get('Content-Type', '').lower()
#
#             # перевірка сторінки за url, це JSON чи HTML-сторінка
#             if 'application/json' in content_type:
#                 data = response.json()
#                 get_data_with_json(url, data['data'], session)
#                 print("Це JSON")
#                 return None
#
#             elif 'text/html' in content_type:
#                 html = response.text
#                 # categories_tree = get_categories_tree_with_html(html)
#                 print("Це HTML")
#                 # return categories_tree
#
#             else:
#                 print(f"Невідомий тип: {content_type}")
#                 return None
#         except requests.exceptions.HTTPError as e:
#             print(f"HTTP error: {e}")
#             return None
#
#
# def get_data_with_json(url, data: dict, session):
#     count_pages = data['pages']['npages']
#     if count_pages > 1:
#         ua = UserAgent()
#         session = requests.Session()
#         base_url = 'https://apteka911.ua/ua'
#
#         response = session.get(base_url, headers={'User-Agent': ua.random})
#
#         headers_base = {
#             "accept": "application/json, text/javascript, */*; q=0.01",
#             "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
#             "x-requested-with": "XMLHttpRequest",  # КРИТИЧНО: саме це каже серверу віддати JSON
#             # Referer має бути ПОВНИМ URL сторінки препарату
#             "referer": base_url,
#             "user-agent": ua.random,
#         }
#
#         session.cookies.update({
#             'site_version': 'desktop',
#             'wucmf_region': '89',
#             # 'PHPSESSID': '601c139cc7ac20fdcbecfdfd55095eb8'
#         })
#
#         # робимо сесію для кожної сторінки з інтервалом 5 сек.
#         for page in range(2, count_pages + 1):
#
#
#             url_page = f'{url}/page={page}'
#             drugs = get_ajax_products(url_page, headers_base, session)
#
#     else:
#         LIST_PREPARATY.append({
#             url: data['ajax_products']
#         })
#
#
# def get_ajax_products(url: str, headers_base, session):
#     # Змінюємо User-Agent для кожного запиту
#     ua = UserAgent()
#     headers = headers_base.copy()
#     headers['User-Agent'] = ua.random
#     response = session.get(url, headers=headers, timeout=10)
#     response.raise_for_status()
#     data = response.json()
#
#
#
# # def get_categories_whith_page_cite_apteka911():
# #     """ отримуємо категорії зі сторінки сайту """
# #     driver = webdriver.Chrome()
# #     driver.get("https://apteka911.ua/ua/")
# #
# #     time.sleep(3)
# #
# #     # знайти кнопку меню
# #     # menu_btn = driver.find_element(By.XPATH, "//div[contains(., 'Каталог')]")
# #     # menu_btn = driver.find_element(By.CSS_SELECTOR, "div.menu-catalog__button")
# #     menu_btn = WebDriverWait(driver, 10).until(
# #         EC.element_to_be_clickable((By.CSS_SELECTOR, ".menu-nav span"))
# #     )
# #
# #     menu_btn.click()
# #
# #     html = driver.page_source
# #
# #     soup = BeautifulSoup(html, "html.parser")
# #     categories = []
# #
# #     items = driver.find_elements(By.CSS_SELECTOR, "ul.menu-catalog__list > li")
# #
# #     for item in items:
# #         try:
# #             name = item.find_element(By.CSS_SELECTOR, "meta[itemprop='name']").get_attribute("content")
# #             url = item.find_element(By.CSS_SELECTOR, "a[itemprop='url']").get_attribute("href")
# #
# #             if url and url in SEEN_URLS:
# #                 # деякі url повторюються, пропустимо їх
# #                 continue
# #             else:
# #                 # якщо url ще не зустрічався, додамо у SEEN_URLS
# #                 SEEN_URLS.add(url)
# #
# #                 categories.append({
# #                     "name": name,
# #                     "url": url
# #                 })
# #                 # перевірка чи існують підкатегорії
# #                 categories += check_category_tree_html(url)
# #         except:
# #             continue
# #
# #     # записати у файл json для подальшого завантаження у БД
# #     with open('categories.json', 'w') as f:
# #         json.dump(categories, f, indent=4)
# #
# #     return categories
# #
# #
# # def check_category_tree_html(url: str):
# #     """ перевірка сторінки за знайденим url, це JSON чи HTML-сторінка.
# #     Якщо HTML-сторінка - робимо парсинг сторінки і знаходимо нові url """
# #
# #     ua = UserAgent()
# #     session = requests.Session()
# #
# #     response = session.get('https://apteka911.ua/ua', headers={"User-Agent": ua.random})
# #
# #     headers = {
# #         "accept": "application/json, text/javascript, */*; q=0.01",
# #         "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
# #         "x-requested-with": "XMLHttpRequest",  # КРИТИЧНО: саме це каже серверу віддати JSON
# #         # Referer має бути ПОВНИМ URL сторінки препарату
# #         "referer": f"https://apteka911.ua/ua",
# #         "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
# #     }
# #     session.cookies.update({
# #         'site_version': 'desktop',
# #         'wucmf_region': '89',
# #         # 'PHPSESSID': '601c139cc7ac20fdcbecfdfd55095eb8'
# #     })
# #     try:
# #         response = session.get(url, headers=headers, timeout=10)
# #         response.raise_for_status()
# #         content_type = response.headers.get('Content-Type', '').lower()
# #
# #         if 'application/json' in content_type:
# #             # data = response.json()
# #             print("Це JSON")
# #             return None
# #
# #         elif 'text/html' in content_type:
# #             html = response.text
# #             categories_tree = get_categories_tree_with_html(html)
# #             print("Це HTML")
# #             return categories_tree
# #
# #         else:
# #             print(f"Невідомий тип: {content_type}")
# #             return None
# #     except requests.exceptions.HTTPError as e:
# #         print(f"HTTP error: {e}")
# #         return None
# #
# #
# # def get_categories_tree_with_html(html):
# #     soup = BeautifulSoup(html, 'html.parser')
# #     script = soup.find('script', {'type': 'text/x-template'})
# #     if not script:
# #         print("❌ script не знайдено")
# #         return None
# #
# #     template_html = script.string
# #
# #     soup2 = BeautifulSoup(template_html, 'html.parser')
# #
# #     categories = []
# #
# #     for a in soup2.select('a[data-link-self-path]'):
# #         name = a.get_text(strip=True)
# #         path = a.get('data-link-self-path')
# #
# #         if not path:
# #             continue
# #
# #         url = urljoin('https://apteka911.ua', path)
# #
# #         if path and path in SEEN_URLS:
# #             continue
# #         else:
# #             SEEN_URLS.add(url)
# #
# #             categories.append({
# #                 "name": name,
# #                 "url": url
# #             })
# #
# #     return categories