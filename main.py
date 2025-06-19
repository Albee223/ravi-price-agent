import os, datetime, asyncio
from playwright.async_api import async_playwright
import requests
import re

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

async def fetch_price_etmall(page):
    price_el = await page.query_selector('.item-sale-price span')
    if price_el:
        price_text = await price_el.inner_text()
        return price_text.strip()
    return None

async def fetch_price_shopee(page):
    price_el = await page.query_selector('._3e_UQT')
    if not price_el:
        price_el = await page.query_selector('._3n5NQx')  # 嘗試另一種樣式
    if price_el:
        price_text = await price_el.inner_text()
        return price_text.strip()
    return None

async def fetch_price_yahoo(page):
    price_el = await page.query_selector('.HeroPrimaryInfo__price_HeroPrimaryInfo__price_3l0mj')
    if price_el:
        price_text = await price_el.inner_text()
        return price_text.strip()
    return None

async def fetch_price(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        if not url:
            return None
        await page.goto(url, timeout=15000)
        await page.wait_for_timeout(3000)

        if "etmall.com.tw" in url:
            price = await fetch_price_etmall(page)
        elif "shopee.tw" in url:
            price = await fetch_price_shopee(page)
        elif "tw.buy.yahoo.com" in url:
            price = await fetch_price_yahoo(page)
        else:
            content = await page.content()
            prices = re.findall(r"\$?\d{1,3}(,\d{3})*(\.\d+)?", content)
            price = prices[0] if prices else None

        await browser.close()
        return price

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
    parsed_price = float(price.replace(",", "").replace("$", "").replace("NT$", "").replace("元", "").strip())
    url = f"https://api.notion.com/v1/pages/{page_id}"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    data = {
        "properties": {
            "價格（TWD）": {
                "number": parsed_price
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
        if price:
            update_page_price(row["id"], price)

if __name__ == "__main__":
    asyncio.run(main())
