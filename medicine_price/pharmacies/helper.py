""" методи парсингу """
import time
import json
import requests

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from urllib.parse import urljoin

from pharmacies.models import CategoryApteka911

SEEN_URLS = set()


def get_categories_whith_page_cite_apteka911():
    driver = webdriver.Chrome()
    driver.get("https://apteka911.ua/ua/")

    time.sleep(3)

    # знайти кнопку меню
    # menu_btn = driver.find_element(By.XPATH, "//div[contains(., 'Каталог')]")
    # menu_btn = driver.find_element(By.CSS_SELECTOR, "div.menu-catalog__button")
    menu_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".menu-nav span"))
    )

    menu_btn.click()

    html = driver.page_source

    soup = BeautifulSoup(html, "html.parser")
    categories = []

    items = driver.find_elements(By.CSS_SELECTOR, "ul.menu-catalog__list > li")

    for item in items:
        try:
            name = item.find_element(By.CSS_SELECTOR, "meta[itemprop='name']").get_attribute("content")
            url = item.find_element(By.CSS_SELECTOR, "a[itemprop='url']").get_attribute("href")

            if url and url in SEEN_URLS:
                continue
            else:
                SEEN_URLS.add(url)

                categories.append({
                    "name": name,
                    "url": url
                })
                categories += check_category_tree_html(url)
        except:
            continue

    # записати у файл json
    with open('categories.json', 'w') as f:
        json.dump(categories, f, indent=4)

    return categories


def check_category_tree_html(url: str):
    ua = UserAgent()
    session = requests.Session()

    response = session.get('https://apteka911.ua/ua', headers={"User-Agent": ua.random})

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
        content_type = response.headers.get('Content-Type', '').lower()

        if 'application/json' in content_type:
            # data = response.json()
            print("Це JSON")
            return None

        elif 'text/html' in content_type:
            html = response.text
            categories_tree = get_categories_tree_with_html(html)
            print("Це HTML")
            return categories_tree

        else:
            print(f"Невідомий тип: {content_type}")
            return None
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error: {e}")
        return None


def get_categories_tree_with_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    script = soup.find('script', {'type': 'text/x-template'})
    if not script:
        print("❌ script не знайдено")

    template_html = script.string

    soup2 = BeautifulSoup(template_html, 'html.parser')

    categories = []

    for a in soup2.select('a[data-link-self-path]'):
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


def update_categories_db(categories):
    """ оновлення категорій в БД """
    for cat in categories:
        obj_category, _ = CategoryApteka911.objects.update_or_create(
            url=cat['url'],
            defaults={"name": cat['name']},
        )
        print(obj_category)


