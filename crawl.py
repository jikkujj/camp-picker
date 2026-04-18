import asyncio
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

BASE_URL = "https://friscoisd.hometownticketing.com"
LIST_HTML_FILE = "summer_list.html"
OUTPUT_FILE = "frisco_camps_combined.json"
CONCURRENCY = 8


def clean(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def parse_list_file():
    with open(LIST_HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    items = []

    for block in soup.select(".public-event .assoc-out"):
        title_el = block.select_one(".public-showtime-name")
        link_el = block.select_one(".assoc-status a[href]")

        title = clean(title_el.get_text()) if title_el else ""
        href = link_el["href"] if link_el else ""

        if href:
            items.append({
                "title": title,
                "location": "",
                "event_url": urljoin(BASE_URL, href),
            })

    for box in soup.select(".showtime-box"):
        title_el = box.select_one(".public-event-title")
        link_el = box.select_one('a[href*="/embed/event/"]')

        if not title_el or not link_el:
            continue

        title = clean(title_el.get_text())

        location = ""
        desc = box.select_one(".showtime-description")
        if desc:
            direct_divs = desc.find_all("div", recursive=False)
            if direct_divs:
                location = clean(direct_divs[0].get_text())

        items.append({
            "title": title,
            "location": location,
            "event_url": urljoin(BASE_URL, link_el["href"]),
        })

    deduped = []
    seen = set()
    for item in items:
        if item["event_url"] not in seen:
            seen.add(item["event_url"])
            deduped.append(item)

    return deduped


def extract_structured_fields(text: str, url: str):
    event_id = ""
    m = re.search(r"/embed/event/(\d+)", url)
    if m:
        event_id = m.group(1)

    lines = [clean(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    detail_title = ""
    venue = ""
    address = ""
    event_policy = ""
    description = ""
    sessions = []

    # Title: usually after "SUMMER CAMPS"
    for i, line in enumerate(lines):
        if line.upper() == "SUMMER CAMPS" and i + 1 < len(lines):
            detail_title = lines[i + 1]
            break

    # Description between "Camp Information:" and "Camp dates and times..."
    try:
        start = lines.index("Camp Information:") + 1
        end = lines.index("Camp dates and times are available as follows:")
        description = clean(" ".join(lines[start:end]))
    except ValueError:
        pass

    # Venue/address/policy
    for i, line in enumerate(lines):
        if "Event Policy:" in line:
            event_policy = line
            # venue/address are usually 2 lines above
            if i >= 2:
                address = lines[i - 1]
                venue = lines[i - 2]
            break

    # Sessions section
    # Collect blocks like:
    # June 1-5
    # 9:00 AM - 12:00 PM
    # Grade level: 4th-5th grade
    try:
        start = lines.index("Camp dates and times are available as follows:") + 1
        end = lines.index("Cancellations/Refunds:")
        session_lines = lines[start:end]

        i = 0
        while i < len(session_lines):
            if re.search(r"(June|July|August|May|April|March|February|January|September|October|November|December)", session_lines[i], re.I):
                session = {"dates": session_lines[i], "time": "", "grade_level": ""}
                if i + 1 < len(session_lines):
                    session["time"] = session_lines[i + 1]
                if i + 2 < len(session_lines) and "Grade level:" in session_lines[i + 2]:
                    session["grade_level"] = session_lines[i + 2].replace("Grade level:", "").strip()
                sessions.append(session)
                i += 3
            else:
                i += 1
    except ValueError:
        pass

    return {
        "event_id": event_id,
        "detail_url": url,
        "detail_title": detail_title,
        "venue": venue,
        "address": address,
        "description": description,
        "sessions": sessions,
        "event_policy": event_policy,
        "detail_text": clean(text),
    }


async def get_real_event_frame_text(page):
    target_frame = None

    for frame in page.frames:
        if "friscoisd.hometownticketing.com/embed/event/" in (frame.url or ""):
            target_frame = frame
            break

    if target_frame is None:
        return "", ""

    text = await target_frame.locator("body").inner_text()
    return text, target_frame.url


async def fetch_one(context, item, index, total):
    page = await context.new_page()
    url = item["event_url"]

    try:
        print(f"[{index}/{total}] {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        text, frame_url = await get_real_event_frame_text(page)

        if not text:
            return {**item, "error": "Could not find real event iframe"}

        detail = extract_structured_fields(text, frame_url)

        return {
            **item,
            "frame_url_used": frame_url,
            **detail,
        }

    except Exception as e:
        return {**item, "error": str(e)}

    finally:
        await page.close()


async def worker(context, queue, results, total):
    while True:
        job = await queue.get()
        if job is None:
            queue.task_done()
            break

        index, item = job
        result = await fetch_one(context, item, index, total)
        results.append(result)
        queue.task_done()


async def main():
    items = parse_list_file()
    total = len(items)
    print(f"Found {total} event URLs from saved list HTML")

    if total == 0:
        print("No items found. Check summer_list.html")
        return

    queue = asyncio.Queue()
    results = []

    for idx, item in enumerate(items, start=1):
        await queue.put((idx, item))

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
        )

        workers = [asyncio.create_task(worker(context, queue, results, total)) for _ in range(CONCURRENCY)]

        await queue.join()

        for _ in workers:
            await queue.put(None)

        await asyncio.gather(*workers)
        await context.close()
        await browser.close()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"Done. Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())