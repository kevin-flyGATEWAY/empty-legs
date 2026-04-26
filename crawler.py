import json
import re
from playwright.sync_api import sync_playwright

BASE_URL = "https://client.jetinsight.com/embed/a371a901-ab80-42a4-a429-b10468ba9b1f/empty"
OUTPUT_FILE = "empty_legs.json"
PER_PAGE = 10


def get_total_pages(html):
    pages = set()
    for m in re.finditer(r"page=(\d+)", html):
        pages.add(int(m.group(1)))
    return max(pages) if pages else 1


def parse_location(text):
    m = re.match(r"^(.+?)\s*\(([A-Z]{3})\),\s*(.+)$", text.strip())
    if m:
        return m.group(1).strip(), m.group(2), m.group(3).strip()
    return text.strip(), None, None


def parse_listings(page):
    flights = []
    cards = page.query_selector_all(".empty-leg-block")
    for card in cards:
        flight = {}

        img = card.query_selector(".img-wrapper img")
        if img:
            flight["image_url"] = img.get_attribute("src") or ""

        locations = card.query_selector_all(".location-header")
        if len(locations) >= 1:
            airport, code, state = parse_location(locations[0].inner_text().strip())
            flight["origin_airport"] = airport
            flight["origin_code"] = code
            flight["origin_state"] = state
        if len(locations) >= 2:
            airport, code, state = parse_location(locations[1].inner_text().strip())
            flight["destination_airport"] = airport
            flight["destination_code"] = code
            flight["destination_state"] = state

        h3 = card.query_selector("h3")
        if h3:
            flight["aircraft"] = h3.inner_text().strip()

        for detail in card.query_selector_all(".detail"):
            text = detail.inner_text().strip()
            icon = detail.query_selector("i")
            icon_class = icon.get_attribute("class") or "" if icon else ""

            if "calendar" in icon_class:
                m = re.search(r"Available\s+(.+)", text)
                if m:
                    dates = m.group(1).strip()
                    parts = [p.strip() for p in dates.split("-")]
                    flight["date_from"] = parts[0] if parts else dates
                    flight["date_to"] = parts[1] if len(parts) > 1 else parts[0]
            elif "clock" in icon_class:
                m = re.search(r"Travel time\s+(.+)", text)
                if m:
                    flight["duration"] = m.group(1).strip()
            elif "users" in icon_class:
                m = re.search(r"Seats\s+(\d+)", text)
                if m:
                    flight["seats"] = int(m.group(1))

        h2 = card.query_selector("h2")
        if h2:
            flight["price"] = h2.inner_text().strip()

        form = card.query_selector("form")
        if form:
            for name, key in [
                ("embedded_leg_request[aircraft_uuid]", "aircraft_uuid"),
                ("embedded_leg_request[origin]", "origin_icao"),
                ("embedded_leg_request[destination]", "destination_icao"),
            ]:
                inp = form.query_selector(f"input[name='{name}']")
                if inp:
                    flight[key] = inp.get_attribute("value") or ""

        if flight.get("aircraft"):
            flights.append(flight)

    return flights


def crawl():
    all_flights = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            executable_path="/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
            args=[
                "--disable-features=EncryptedClientHello",
                "--ignore-certificate-errors",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            extra_http_headers={"Referer": "https://www.flyadvanced.com/"},
        )
        pg = context.new_page()

        print("Fetching page 1...")
        pg.goto(f"{BASE_URL}?page=1&per_page={PER_PAGE}", wait_until="networkidle", timeout=30000)
        pg.wait_for_selector(".empty-leg-block", timeout=15000)

        total_pages = get_total_pages(pg.content())
        print(f"Total pages: {total_pages}")

        flights = parse_listings(pg)
        print(f"  Page 1: {len(flights)} listings")
        all_flights.extend(flights)

        for page_num in range(2, total_pages + 1):
            print(f"Fetching page {page_num}...")
            pg.goto(
                f"{BASE_URL}?page={page_num}&per_page={PER_PAGE}",
                wait_until="networkidle",
                timeout=30000,
            )
            pg.wait_for_selector(".empty-leg-block", timeout=15000)
            flights = parse_listings(pg)
            print(f"  Page {page_num}: {len(flights)} listings")
            all_flights.extend(flights)

        browser.close()

    output = {
        "source_url": BASE_URL,
        "total_listings": len(all_flights),
        "pages_crawled": total_pages,
        "flights": all_flights,
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nDone. {len(all_flights)} total listings saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    crawl()
