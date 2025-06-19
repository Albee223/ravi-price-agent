import os, datetime, asyncio
from playwright.async_api import async_playwright
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

async def fetch_price(keyword, platform):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = {
            "Shopee": f"https://shopee.tw/search?keyword={keyword}",
            "MOMO": f"https://www.momoshop.com.tw/mosearch/{keyword}.html",
            "ETmall": f"https://www.etmall.com.tw/Search?q={keyword}"
        }.get(platform, "")
        if url == "":
            return
        await page.goto(url)
        await page.wait_for_timeout(4000)
        await browser.close()

        print(f"商品名稱: {keyword}（{platform}）")
        print(f"搜尋連結: {url}")
        # 寫入 Notion 略過

async def main():
    await fetch_price("娜美妍智慧筋膜槍", "Shopee")

if __name__ == "__main__":
    asyncio.run(main())