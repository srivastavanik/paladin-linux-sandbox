# playwright_scenarios/goto.py
import argparse, sys, asyncio
from playwright.async_api import async_playwright

async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    args = p.parse_args()

    print(f"[goto] navigating to {args.url}")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        resp = await page.goto(args.url, wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        print(f"[goto] status={resp.status if resp else 'n/a'} title={title}")
        await page.screenshot(path="/tmp/goto.png")
        print("[goto] screenshot=/tmp/goto.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
