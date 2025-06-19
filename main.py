import os, datetime, asyncio
from playwright.async_api import async_playwright
import requests
import re

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

async def fetch_price(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        if not url:
            return None
        try:
            await page.goto(url, timeout=15000)
            await page.wait_for_timeout(3000)
            content = await page.content()
        except Exception as e:
            return None
        finally:
            await browser.close()

        numbers = re.findall(r"[\$NT]*\s*[\d,]+", content)
        cleaned = []
        for n in numbers:
            n = n.replace(",", "").replace("$", "").replace("NT", "").replace("元", "").strip()
            if n.isdigit():
                cleaned.append(int(n))
        if cleaned:
            return min(cleaned)
        return None

def query_notion_database():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers)
    return response.json()

def update_page_price(page_id, price):
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "properties": {
            "價格（TWD）": {"number": price},
            "查詢時間": {
                "date": {"start": datetime.datetime.now().isoformat()}
            }
        }
    }
    requests.patch(url, headers=headers, json=data)

async def main():
    data = query_notion_database()
    for row in data.get("results", []):
        props = row["properties"]
        name = props["商品名稱"]["title"][0]["text"]["content"]
        url = props["商品連結"]["url"]
        print(f"🔍 {name} | {url}")
        price = await fetch_price(url)
        print(f"➡️ 價格: {price}")
        if price:
            update_page_price(row["id"], price)

if __name__ == "__main__":
    asyncio.run(main())
