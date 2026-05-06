import os
import time
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

OLX_URL = "https://www.olx.pl/praca/finanse-ksiegowosc/warszawa/?search%5Bdist%5D=30"
CHECK_EVERY_SECONDS = 60

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def notify(text):
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": False,
        },
        timeout=20,
    )
    response.raise_for_status()

def normalize_link(href):
    absolute = urljoin("https://www.olx.pl", href)
    parsed = urlsplit(absolute)
    path = parsed.path.rstrip("/")
    return urlunsplit((parsed.scheme, parsed.netloc, path, "", ""))

def clean_text(text):
    return " ".join(text.split())

def extract_title(anchor):
    title_el = anchor.select_one(
        "[data-testid='ad-title'], [data-cy='ad-card-title'], h4, h5, h6"
    )

    if title_el:
        return clean_text(title_el.get_text(" ", strip=True))

    return clean_text(anchor.get_text(" ", strip=True))

def get_offers():
    response = requests.get(
        OLX_URL,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
        },
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    offers = []
    seen_links = set()

    for anchor in soup.select("a[href*='/oferta/']"):
        link = normalize_link(anchor["href"])
        title = extract_title(anchor)

        if not title or link in seen_links:
            continue

        seen_links.add(link)
        offers.append({
            "title": title,
            "link": link,
        })

    return offers[:30]

def main():
    known_links = {offer["link"] for offer in get_offers()}

    notify(
        "Monitor OLX uruchomiony\n"
        f"Obserwuje oferty: {OLX_URL}\n"
        f"Aktualnie widze {len(known_links)} ofert."
    )

    while True:
        try:
            offers = get_offers()

            for offer in reversed(offers):
                if offer["link"] in known_links:
                    continue

                known_links.add(offer["link"])

                notify(
                    "Nowa oferta pracy OLX\n\n"
                    f"{offer['title']}\n"
                    f"{offer['link']}"
                )

            print(f"Sprawdzono OLX. Ofert na stronie: {len(offers)}.", flush=True)

        except Exception as e:
            print(f"Blad OLX: {e}", flush=True)

        time.sleep(CHECK_EVERY_SECONDS)

if __name__ == "__main__":
    main()
