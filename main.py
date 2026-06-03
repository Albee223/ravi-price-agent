import asyncio
import datetime
import os
import re
from typing import Any

import requests
from playwright.async_api import async_playwright

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
REQUEST_TIMEOUT = 15
MIN_PRICE = 10


def _validate_notion_config() -> None:
    missing = []
    if not NOTION_TOKEN:
        missing.append("NOTION_TOKEN")
    if not DATABASE_ID:
        missing.append("NOTION_DATABASE_ID")
    if missing:
        raise ValueError(f"Missing required environment variable(s): {', '.join(missing)}")


def _notion_headers() -> dict[str, str]:
    _validate_notion_config()
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _extract_price(content: str) -> int | None:
    currency_patterns = [
        r"(?:NT\$?|NTD|\$)\s*([\d,]+)",
        r"([\d,]+)\s*元",
    ]
    cleaned: list[int] = []

    for pattern in currency_patterns:
        for match in re.findall(pattern, content, flags=re.IGNORECASE):
            value = match.replace(",", "").strip()
            if value.isdigit():
                price = int(value)
                if price >= MIN_PRICE:
                    cleaned.append(price)

    if cleaned:
        return min(cleaned)
    return None


async def fetch_price(url: str | None) -> int | None:
    if not url:
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, timeout=15000)
                await page.wait_for_timeout(3000)
                content = await page.content()
            finally:
                await browser.close()
    except Exception as e:
        print(f"fetch_price failed for {url}: {e}")
        return None

    return _extract_price(content)


def query_notion_database() -> dict[str, Any]:
    _validate_notion_config()
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=_notion_headers(), timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def update_page_price(page_id: str, price: int) -> None:
    url = f"https://api.notion.com/v1/pages/{page_id}"
    data = {
        "properties": {
            "價格（TWD）": {"number": price},
            "查詢時間": {
                "date": {"start": datetime.datetime.now().isoformat()}
            },
        }
    }
    response = requests.patch(
        url,
        headers=_notion_headers(),
        json=data,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()


def _get_product_name(props: dict[str, Any]) -> str | None:
    title = props.get("商品名稱", {}).get("title", [])
    if not title:
        return None
    return title[0].get("text", {}).get("content")


def _get_product_url(props: dict[str, Any]) -> str | None:
    return props.get("商品連結", {}).get("url")


async def main() -> None:
    data = query_notion_database()
    for row in data.get("results", []):
        props = row.get("properties", {})
        name = _get_product_name(props)
        url = _get_product_url(props)
        page_id = row.get("id")

        if not page_id:
            print("⚠️ 跳過缺少 page id 的資料列")
            continue
        if not name:
            print(f"⚠️ 跳過缺少商品名稱的資料列: {page_id}")
            continue
        if not url:
            print(f"⚠️ 跳過缺少商品連結的資料列: {name}")
            continue

        print(f"🔍 {name} | {url}")
        price = await fetch_price(url)
        print(f"➡️ 價格: {price}")
        if price is not None:
            update_page_price(page_id, price)


if __name__ == "__main__":
    asyncio.run(main())
