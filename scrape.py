import requests
from bs4 import BeautifulSoup
import time
import json

# List of restaurants with name and URLs to scrape
restaurants_info = [
    {
        "name": "Haji's",
        "site": "https://www.hajislucknow.com",  # base URL for reference
        "pages": {
            "contact": "https://www.hajislucknow.com/contact",
            "menu": "https://www.hajislucknow.com/menus",
        },
    },
    {
        "name": "Punjab Grill",
        "site": "https://www.punjabgrill.in",
        "pages": {"menu": "https://www.punjabgrill.in/punjab-grill-menu/"},
    },
    {
        "name": "Flavours (Hometel Alambagh)",
        "site": "https://www.sarovarhotels.com",
        "pages": {
            "dining": "https://www.sarovarhotels.com/hometel-alambagh-lucknow/dining.html"
        },
    },
    {
        "name": "Pizza Hut (Hazratganj)",
        "site": "https://restaurants.pizzahut.co.in",
        "pages": {
            "branch": "https://restaurants.pizzahut.co.in/pizza-hut-hazratganj-pizza-restaurant-hazratganj-lucknow-1258/Menu"
        },
    },
    {
        "name": "Biryani Blues (Phoenix Mall)",
        "site": "https://restaurants.biryaniblues.com",
        "pages": {
            "outlet": "https://restaurants.biryaniblues.com/biryani-blues-restaurants-lucknow-tehsil-lucknow-368922/Home"
        },
    },
    {
        "name": "Kitchen: The Food Stop",
        "site": "https://kitchentfs.com",
        "pages": {"home": "https://kitchentfs.com/"},
    },
]

headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
scraped_data = []

for rest in restaurants_info:
    data = {
        "name": rest["name"],
        "address": None,
        "hours": None,
        "phone": None,
        "email": None,
        "menu": [],
        "notes": None,
    }
    pages = rest.get("pages", {})

    # Scrape Haji's contact page for address, hours, contact
    if rest["name"] == "Haji's":
        try:
            res = requests.get(pages["contact"], headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            # Extract address text
            addr = soup.find(text="Haider Market,")
            if addr:
                data["address"] = addr.strip()
            # Opening hours are in a table, get all days
            hours_tags = soup.select("div:contains('-')")  # simplistic selector
            hours_list = [
                tag.get_text(separator=" ").strip()
                for tag in hours_tags
                if "12:00" in tag.text
            ]
            if hours_list:
                data["hours"] = "; ".join(hours_list)
            # Phone and email
            phone = soup.find(string=lambda t: t and t.strip().startswith("(+91"))
            email = soup.find(string=lambda t: t and "@" in t)
            if phone:
                data["phone"] = phone.strip()
            if email:
                data["email"] = email.strip()
        except Exception as e:
            print(f"Failed to scrape Haji's contact page: {e}")
        time.sleep(1)
        # Scrape Haji's menu page
        try:
            res = requests.get(pages["menu"], headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            # Find categories and items
            categories = soup.find_all(["h2", "h3"])
            current_section = None
            for tag in categories:
                if tag.name == "h2":  # category
                    current_section = tag.get_text().strip()
                elif tag.name == "h3":  # item
                    item_name = tag.get_text().strip()
                    # find next sibling text for price
                    price_tag = tag.find_next(
                        string=lambda t: t and t.strip().startswith("₹")
                    )
                    price = price_tag.strip() if price_tag else None
                    # Add item to menu list
                    data["menu"].append(
                        {
                            "section": current_section,
                            "item": item_name,
                            "description": None,
                            "price": price,
                        }
                    )
        except Exception as e:
            print(f"Failed to scrape Haji's menu: {e}")
        time.sleep(1)

    # Scrape Punjab Grill menu page
    elif rest["name"].startswith("Punjab Grill"):
        try:
            res = requests.get(pages["menu"], headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            # Items are listed under headings; find all menu items
            # Each item appears as a list bullet or similar
            ul = soup.find_all("li")
            for li in ul:
                text = li.get_text(separator=" ").strip()
                if text:
                    parts = text.split("₹")
                    if len(parts) >= 2:
                        item_desc = parts[0].strip()
                        price = "₹" + parts[1].strip()
                        # In Punjab Grill menu, each item includes name and description
                        name_desc = item_desc.split(None, 1)
                        item_name = name_desc[0].strip()
                        desc = name_desc[1].strip() if len(name_desc) > 1 else ""
                        data["menu"].append(
                            {
                                "section": "Main Menu",
                                "item": item_name,
                                "description": desc,
                                "price": price,
                            }
                        )
        except Exception as e:
            print(f"Failed to scrape Punjab Grill: {e}")
        time.sleep(1)

    # Scrape Flavours restaurant page for address/hours
    elif rest["name"].startswith("Flavours"):
        try:
            res = requests.get(pages["dining"], headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            # Address and hours are clearly labeled on this page
            address_tag = soup.find(string=lambda t: t and "Alambagh, Lucknow" in t)
            hours_tag = soup.find(string=lambda t: t and t.strip().endswith("Hours"))
            if address_tag:
                data["address"] = address_tag.strip()
            # The line with "24 Hours"
            hours_val = soup.find(string=lambda t: t and "24 Hours" in t)
            if hours_val:
                data["hours"] = "24 Hours"
            # Contact email/phone might be in same page
            phone = soup.find(string=lambda t: t and "+91" in t)
            email = soup.find(string=lambda t: t and "@sarovarhotels" in t)
            if phone:
                data["phone"] = phone.strip()
            if email:
                data["email"] = email.strip()
        except Exception as e:
            print(f"Failed to scrape Flavours page: {e}")
        time.sleep(1)

    # Scrape Pizza Hut branch page for address/contact
    elif rest["name"].startswith("Pizza Hut"):
        try:
            res = requests.get(pages["branch"], headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            # Find address by keyword "MG Marg"
            addr_tag = soup.find(string=lambda t: t and "MG Marg" in t)
            if addr_tag:
                data["address"] = addr_tag.strip()
            # Find phone number line
            phone_tag = soup.find(
                string=lambda t: t and t.strip().isdigit() and len(t.strip()) > 5
            )
            if phone_tag:
                data["phone"] = phone_tag.strip()
            # Hours may be under a tag
            status_tag = soup.find(
                string=lambda t: t and ("Open" in t or "Closed" in t)
            )
            if status_tag:
                data["hours"] = status_tag.strip()
        except Exception as e:
            print(f"Failed to scrape Pizza Hut branch page: {e}")
        time.sleep(1)

    # Scrape Biryani Blues outlet page for address/hours
    elif rest["name"].startswith("Biryani Blues"):
        try:
            res = requests.get(pages["outlet"], headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            # Address line contains "Phoenix United Mall"
            addr = soup.find(string=lambda t: t and "Phoenix United Mall" in t)
            if addr:
                data["address"] = addr.strip()
            # Business hours listed under Business Hours section
            bh = soup.find_all(
                string=lambda t: t and "-" in t and t.strip().endswith("PM")
            )
            hours_list = [t.strip() for t in bh if t.strip()]
            if hours_list:
                data["hours"] = "; ".join(hours_list)
        except Exception as e:
            print(f"Failed to scrape Biryani Blues outlet page: {e}")
        time.sleep(1)

    # Scrape Kitchen site footer for address/contact
    elif rest["name"].startswith("Kitchen"):
        try:
            res = requests.get(pages["home"], headers=headers, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.text, "html.parser")
            addr = soup.find(string=lambda t: t and "Aravali Marg" in t)
            phone = soup.find(string=lambda t: t and t.strip().startswith("0522"))
            email = soup.find(string=lambda t: t and "@kitchentfs" in t)
            if addr:
                data["address"] = addr.strip()
            if phone:
                data["phone"] = phone.strip()
            if email:
                data["email"] = email.strip()
        except Exception as e:
            print(f"Failed to scrape Kitchen site: {e}")
        time.sleep(1)

    # Save the data for this restaurant (omit None fields)
    # Remove empty fields
    data = {k: v for k, v in data.items() if v}
    scraped_data.append(data)

# Write results to JSON file
with open("restaurants_lucknow.json", "w", encoding="utf-8") as f:
    json.dump(scraped_data, f, indent=2, ensure_ascii=False)

print("Scraping complete. Data saved to restaurants_lucknow.json.")


