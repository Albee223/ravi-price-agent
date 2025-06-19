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
        await page.goto(url)
        await page.wait_for_timeout(3000)

        if "etmall.com.tw" in url:
            element = await page.query_selector(".area_price .txt_red")
        elif "pchome.com.tw" in url:
            element = await page.query_selector("span.Price")
        elif "shopee.tw" in url:
            element = await page.query_selector("._3e_UQT") or await page.query_selector("._2Shl1j")  # 不同樣式備援
        elif "buy.yahoo.com" in url:
            element = await page.query_selector("span[class*='Price']")  # 類似 .Price或價格樣式
        else:
            element = None

        if element:
            text = await element.inner_text()
            return re.sub(r"[^\d]", "", text)  # 保留純數字
        else:
            html = await page.content()
            prices = re.findall(r"\$[\d,]+", html)
            if prices:
                return prices[0].replace(",", "").replace("$", "")
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
    try:
        price_number = int(float(price))
    except:
        return
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "properties": {
            "價格（TWD）": {
                "number": price_number
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
        product_url = props["商品連結"].get("url", "")
        print(f"🔍 查詢商品：{product_name}")
        price = await fetch_price(product_url)
        print(f"➡️ 擷取價格：{price}")
        if price:
            update_page_price(row["id"], price)

if __name__ == "__main__":
    asyncio.run(main())
