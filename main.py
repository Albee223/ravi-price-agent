
import os, datetime, asyncio
from playwright.async_api import async_playwright
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

async def fetch_price(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        if not url:
            return None
        await page.goto(url)
        await page.wait_for_timeout(4000)
        content = await page.content()
        await browser.close()

        # 簡化處理：抓取頁面中第一個出現的價格（可依實際平台調整）
        import re
        prices = re.findall(r"\$?\d+[,.]?\d*", content)
        return prices[0] if prices else "無法取得"

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
            "價格（TWD）": {
                "number": float(price.replace(",", "").replace("$", ""))
            },
            "查詢時間": {
                "date": {
                    "start": datetime.datetime.now().isoformat()
                }
            }
        }
    }
    requests.patch(url, headers=headers, json=data)

async def main():
    data = query_notion_database()
    for row in data.get("results", []):
        props = row["properties"]
        product_name = props["商品名稱"]["title"][0]["text"]["content"]
        product_url = props["商品連結"]["url"]
        print(f"🔍 查詢商品：{product_name}")
        price = await fetch_price(product_url)
        print(f"➡️ 取得價格：{price}")
        if price and price != "無法取得":
            update_page_price(row["id"], price)

if __name__ == "__main__":
    asyncio.run(main())
