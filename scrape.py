import requests
from bs4 import BeautifulSoup
import json
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ScraperBot/1.0; +http://example.com/bot)"
}
DELAY = 1


def scrape_tunday_kababi():
    data = {
        "name": "Tunday Kababi (Lucknow)",
        "locations": [],
        "menu": [],
        "hours": None,
        "contact": {},
        "special": [],
    }
    try:
        time.sleep(DELAY)
        res = requests.get(
            "https://www.tundaykababi.com/contact-us", headers=HEADERS, timeout=10
        )
        soup = BeautifulSoup(res.text, "html.parser")
        contact_info = soup.find("h2", string=re.compile(r"Tunday Kababi"))
        if contact_info:
            addr = contact_info.find_next("p").get_text(separator=" ").strip()
            phones = contact_info.find_next("p").find_next("p").get_text().strip()
            data["locations"].append(addr)
            data["contact"]["phone"] = phones.split("|")[0].strip()
        menu_url = "https://www.tundaykababi.com/shop/kebabs"
        time.sleep(DELAY)
        res2 = requests.get(menu_url, headers=HEADERS, timeout=10)
        soup2 = BeautifulSoup(res2.text, "html.parser")
        items = soup2.select("h3")
        for item in items:
            name = item.get_text(strip=True)
            if name and name not in data["menu"]:
                data["menu"].append({"name": name, "description": None, "price": None})
    except Exception as e:
        print(f"Tunday Kababi scrape error: {e}")
    return data


def scrape_kfc():
    data = {
        "name": "KFC (Shahjahan Road, Lucknow)",
        "locations": [],
        "menu": [],
        "hours": None,
        "contact": {},
        "special": [],
    }
    try:
        time.sleep(DELAY)
        res = requests.get(
            "https://restaurants.kfc.co.in/kfc-shahjanaf-road-restaurants-shahjanaf-road-lucknow-34993/Home",
            headers=HEADERS,
            timeout=10,
        )
        soup = BeautifulSoup(res.text, "html.parser")

        loc = soup.find("h1")
        if loc:
            addr = loc.find_next("ul").get_text(" ", strip=True)
            data["locations"].append(addr)

        phone = soup.find(string=re.compile(r"\+91"))
        if phone:
            data["contact"]["phone"] = phone.strip()

        hours = soup.find(string=re.compile(r"Open until"))
        if hours:
            data["hours"] = hours.strip()
        card_bodies = soup.find_all("div", class_="card-body")
        if not card_bodies:
            card_bodies = soup.find_all("div", id="card-body")

        if card_bodies:
            for card in card_bodies:
                item_name_elem = card.find(
                    ["h5", "h4", "h3", "div", "span"],
                    class_=re.compile(r"item-name|title|menu-item-name"),
                )
                item_price_elem = card.find(
                    ["span", "div", "p"], class_=re.compile(r"price|amount|cost")
                )
                if not item_name_elem or not item_price_elem:
                    card_text = card.get_text()
                    name_price_match = re.search(r"(.*?)(?:[\s-]+)(₹\s*\d+)", card_text)

                    if name_price_match:
                        name = name_price_match.group(1).strip()
                        price = name_price_match.group(2).strip()
                        if name and len(name) > 1:
                            data["menu"].append(
                                {"name": name, "description": None, "price": price}
                            )
                else:
                    name = item_name_elem.get_text(strip=True)
                    price = item_price_elem.get_text(strip=True)

                    # Add to menu if name is not empty
                    if name and len(name) > 1:
                        data["menu"].append(
                            {"name": name, "description": None, "price": price}
                        )
        if not data["menu"]:
            menu_section = soup.find(
                "div", string=re.compile(r"KFC Menu in Shahjanaf Road")
            )
            if menu_section:
                items = soup.find_all("li", text=re.compile(r"₹"))
                for li in items:
                    text = li.get_text(separator="|").split("|")
                    if len(text) >= 2:
                        name = text[0].strip()
                        price = text[-1].strip()
                        data["menu"].append(
                            {"name": name, "description": None, "price": price}
                        )
        if not data["menu"]:
            price_elements = soup.find_all(string=re.compile(r"₹\s*\d+"))
            for price_elem in price_elements:
                parent = price_elem.find_parent()
                if parent:
                    parent_text = parent.get_text()
                    name_price_match = re.search(
                        r"(.*?)(?:[\s-]+)(₹\s*\d+)", parent_text
                    )

                    if name_price_match:
                        name = name_price_match.group(1).strip()
                        price = name_price_match.group(2).strip()

                        if (
                            name
                            and len(name) > 1
                            and not any(item["name"] == name for item in data["menu"])
                        ):
                            data["menu"].append(
                                {"name": name, "description": None, "price": price}
                            )
    except Exception as e:
        print(f"KFC scrape error: {e}")
    # print(data)
    return data


def scrape_dominos():
    """Scrape Domino's Pizza (Chowk, Lucknow) menu."""
    data = {
        "name": "Domino's Pizza (Chowk, Lucknow)",
        "locations": [],
        "menu": [],
        "hours": None,
        "contact": {},
        "special": [],
    }
    try:
        time.sleep(DELAY)
        res = requests.get(
            "https://www.dominos.co.in/store-location/lucknow/chowk-lucknow-uttar-pradesh",
            headers=HEADERS,
            timeout=10,
        )
        soup = BeautifulSoup(res.text, "html.parser")
        # Location and contact
        heading = soup.find("h3")
        if heading:
            address = heading.find_next("address")
            phone = heading.find_next(string=re.compile(r"\d{10,}"))
            if address:
                data["locations"].append(address.get_text(" ", strip=True))
            if phone:
                data["contact"]["phone"] = phone.strip()
        hours = soup.find("div", string=re.compile(r"Opening hours"))
        if hours:
            data["hours"] = hours.find_next("p").get_text(strip=True)
        # Switch to menu tab
        time.sleep(DELAY)
        res2 = requests.get(
            "https://www.dominos.co.in/store-location/lucknow/chowk-lucknow-uttar-pradesh/menu",
            headers=HEADERS,
            timeout=10,
        )
        soup2 = BeautifulSoup(res2.text, "html.parser")
        sections = soup2.select("h3")
        for h3 in sections:
            name = h3.get_text(strip=True)
            desc = h3.find_next("p")
            desc_text = desc.get_text(strip=True) if desc else None
            if name:
                data["menu"].append(
                    {"name": name, "description": desc_text, "price": None}
                )
    except Exception as e:
        print(f"Domino's scrape error: {e}")
    # print(data)
    return data


def scrape_motimahal_delux():
    data = {
        "name": "Moti Mahal Delux (Lucknow)",
        "locations": [],
        "menu": [],
        "hours": None,
        "contact": {},
        "special": [],
    }
    try:
        time.sleep(DELAY)
        res = requests.get(
            "https://www.motimahaldelux.com/post/moti-mahal-lucknow",
            headers=HEADERS,
            timeout=10,
        )
        soup = BeautifulSoup(res.text, "html.parser")
        addr_content = soup.find(string=re.compile(r"Address:"))
        if addr_content:
            parent = addr_content.find_parent()
            address_text = parent.get_text()
            address_match = re.search(
                r"Address:(.*?)(?:Operating Hours|$)", address_text, re.DOTALL
            )
            if address_match:
                address = address_match.group(1).strip()
                data["locations"].append(address)
        full_text = soup.get_text()
        hours_match = re.search(
            r"Operating Hours.*?Monday to Sunday:\s*(.*?PM)", full_text, re.DOTALL
        )
        if hours_match:
            hours_time = hours_match.group(1).strip()
            data["hours"] = "Monday to Sunday: " + hours_time
        else:
            hours_section = soup.find(
                string=lambda text: text and "Operating Hours" in text
            )
            if hours_section:
                parent_elem = hours_section.find_parent()
                next_ul = parent_elem.find_next("ul")
                if next_ul:
                    hour_item = next_ul.find(string=re.compile(r"Monday to Sunday"))
                    if hour_item:
                        hours_text = hour_item.strip()
                        data["hours"] = hours_text
        menu_section = soup.find(string=re.compile(r"Menu Highlights"))
        if menu_section:
            menu_parent = menu_section.find_parent()
            menu_list = menu_parent.find_next("ul")
            if menu_list:
                menu_items = menu_list.find_all("li")
                for item in menu_items:
                    item_text = item.get_text().strip()
                    dish_match = re.search(r"(.*?):(.*)", item_text)
                    if dish_match:
                        dish_name = dish_match.group(1).strip()
                        dish_desc = dish_match.group(2).strip()
                        data["menu"].append(
                            {"name": dish_name, "description": dish_desc, "price": None}
                        )
        special_section = soup.find(string=re.compile(r"Why Choose"))
        if special_section:
            special_parent = special_section.find_parent()
            special_list = special_parent.find_next("ul")
            if special_list:
                special_items = special_list.find_all("li")
                for item in special_items:
                    special_text = item.get_text().strip()
                    special_match = re.search(r"(.*?):(.*)", special_text)
                    if special_match:
                        special_feature = (
                            special_match.group(1).strip()
                            + ": "
                            + special_match.group(2).strip()
                        )
                    else:
                        special_feature = special_text
                    data["special"].append(special_feature)
        faq_section = soup.find(string=re.compile(r"Frequently Asked Questions"))
        if faq_section:
            private_events = soup.find(
                string=re.compile(r"Can I book the restaurant for private events")
            )
            if private_events:
                parent = private_events.find_parent()
                answer = parent.find_next(string=re.compile(r"A:"))
                if answer:
                    events_text = answer.find_parent().get_text()
                    events_match = re.search(r"A:(.*)", events_text)
                    if events_match:
                        data["special"].append(
                            "Private Events: " + events_match.group(1).strip()
                        )
                    else:
                        events_info = re.search(
                            r"Can I book.*?\n*.*?(Yes, we accept.*?)(?:\n|$)",
                            full_text,
                            re.DOTALL,
                        )
                        if events_info:
                            data["special"].append(
                                "Private Events: " + events_info.group(1).strip()
                            )
        if data["locations"]:
            location_match = re.search(r"(Hazratganj, Lucknow)", data["locations"][0])
            if location_match:
                data["contact"]["location"] = location_match.group(1)
            address_match = re.search(
                r"(Moti Mahal Delux,.*?)(?:Operating Hours|$)",
                " ".join(data["locations"]),
                re.DOTALL,
            )
            if address_match:
                data["contact"]["address"] = address_match.group(1).strip()
    except Exception as e:
        print(f"Moti Mahal Delux scrape error: {e}")
    return data


restaurants = []
for fn in (
    scrape_kfc,
    scrape_dominos,
    scrape_tunday_kababi,
    scrape_motimahal_delux,
):
    try:
        info = fn()
        restaurants.append(info)
    except Exception as ex:
        print(f"Error scraping {fn.__name__}: {ex}")

with open("lucknow_restaurants.json", "w", encoding="utf-8") as f:
    json.dump(restaurants, f, indent=2, ensure_ascii=False)

print("Scraping complete. Data saved to lucknow_restaurants.json.")
