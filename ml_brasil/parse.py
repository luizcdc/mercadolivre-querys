import importlib.resources as resources
import bs4
from bs4 import BeautifulSoup
from requests import get
from time import sleep
from pickle import load
from urllib.parse import quote
from re import compile, search
from . import categories

SKIP_PAGES = 0  # 0 unless debugging
INT32_MAX = 2 ** 31 - 1

try:
    with resources.open_binary(categories, "categories.pickle") as cat:
        CATS = load(cat)
except FileNotFoundError:
    raise FileNotFoundError("The categories.pickle database could not be "
                            "loaded. Try to generate a new updated data"
                            "base with the extract_categories script, or "
                            "to reinstall the module.")


def get_link(product):
    LINK_CATCHER = compile(r"(https?://.+(?:MLB\d+|-_JM))")
    link = product.find(class_="item__info-title")
    if link:
        link = link.get("href").strip()
        link = search(LINK_CATCHER, link)
        return link[0]
    return ""


def get_title(product):
    title_tag = product.find(class_="main-title")
    if not title_tag:
        title_tag = ""
    else:
        title_tag = title_tag.contents[0].strip()
    return title_tag


def get_price(product):
    price_container = product.find(class_="price__container")
    if price_container:
        price_int = price_container.find(
            class_="price__fraction").contents[0].strip()
        price_int = int(float(price_int) * (1 if len(price_int) < 4 else 1000))
        price_cents = price_container.find(class_="price__decimals")
        price_cents = 0 if not price_cents else int(price_cents.contents[0].strip())
    else:
        price_int, price_cents = float('nan'), float('nan')
    return (price_int, price_cents)


def get_picture(product):
    picture = ""
    image_tag = product.find(class_="item__image item__image--stack")
    if image_tag:
        picture = image_tag.find("img").get("src")
        if not picture:
            picture = image_tag.find("img").get("data-src")
        if not picture:
            picture = ""

    return picture


def is_no_interest(product):
    return "item-installments free-interest" in str(product)


def has_free_shipping(product):
    return "stack_column_item shipping highlighted" in str(product)


def is_in_sale(product):
    return "item__discount" in str(product)


def get_all_products(pages, min_rep):
    products = [
        BeautifulSoup(page, "html.parser")
        .find_all(class_="results-item highlighted article stack product")
        for page in pages]

    return [{
            "link": get_link(product),
            "title": get_title(product),
            "price": get_price(product),
            "no-interest": is_no_interest(product),
            "free-shipping": has_free_shipping(product),
            "in-sale": is_in_sale(product),
            "reputable": is_reputable(
                get_link(product), min_rep),
            "picture": get_picture(product)}
            for page in products for product in page]


def is_reputable(link, min_rep=3, aggressiveness=2):
    if min_rep > 0:
        if not link:
            return False

        sleep(0.5**aggressiveness)
        product = BeautifulSoup(get(link).text, "html.parser")

        if "ui-pdp-other-sellers__title" not in str(product):
            thermometer = product.find(class_="card-section seller-thermometer")
            THERM_LEVELS = ("newbie", "red", "orange",
                            "yellow", "light_green", "green")[0:min_rep]
            if any(badrep in str(thermometer)
                   for badrep in THERM_LEVELS) or thermometer == None:
                return False

    return True


def get_cat(catid):
    father_num, child_num = map(int, catid.split('.'))
    subdomain = False
    for father_cat in CATS:
        if father_cat[0][0] == father_num:
            for child in father_cat[1]:
                if child['number'] == child_num:
                    subdomain = child['subdomain']
                    suffix = child['suffix']
                    break
    if not subdomain:
        raise ValueError(f"Categoria informada \"{catid}\" não existe.")

    return subdomain, suffix


def get_all_products(pages, min_rep):
    products = [
        BeautifulSoup(page, "html.parser")
        .find_all(class_="results-item highlighted article stack product")
        for page in pages]

    return [{
            "link": get_link(product),
            "title": get_title(product),
            "price": get_price(product),
            "no-interest": is_no_interest(product),
            "free-shipping": has_free_shipping(product),
            "in-sale": is_in_sale(product),
            "reputable": is_reputable(
                get_link(product), min_rep),
            "picture": get_picture(product)}
            for page in products for product in page]


def get_search_pages(term, cat='0.0',
                     price_min=0, price_max=INT32_MAX,
                     condition=0, aggressiveness=2):
    CONDITIONS = ["", "_ITEM*CONDITION_2230284", "_ITEM*CONDITION_2230581"]
    subdomain, suffix = get_cat(cat)
    index = 1
    pages = []
    while True:
        sleep(0.5**aggressiveness)
        page = get(
            f"https://{subdomain}.mercadolivre.com.br/{suffix}"
            f"{quote(term, safe='')}_Desde_{index}"
            f"_PriceRange_{price_min}-{price_max}{CONDITIONS[condition]}")
        index += 50 * (SKIP_PAGES + 1)  # DEBUG
        if page.status_code == 404:
            break
        else:
            pages.append(page.text)
    return pages