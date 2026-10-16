import asyncio
import sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.stdout.reconfigure(encoding="utf-8")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="ru-RU",
            viewport={"width": 1400, "height": 1000}
        )
        page = await context.new_page()
        await page.goto("https://lens.google.com", wait_until="networkidle", timeout=30000)
        
        inputs = await page.query_selector_all("input[type='file']")
        print(f"Found {len(inputs)} file inputs.")
        target_img = r"C:\Users\user\Downloads\photo_2026-10-09_12-38-42.jpg"
        for inp in inputs:
            await inp.set_input_files(target_img)
            
        print("Waiting 7 seconds...")
        await page.wait_for_timeout(7000)
        print("Final URL:", page.url)
        text = await page.evaluate("document.body ? document.body.innerText : ''")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        print(f"Total lines: {len(lines)}")
        for l in lines[:40]:
            print(" *", l)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
