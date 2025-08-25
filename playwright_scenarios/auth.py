# playwright_scenarios/auth.py
import argparse, asyncio, sys
from playwright.async_api import async_playwright

async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)       # base URL
    p.add_argument("--login-path", default="/login")
    p.add_argument("--user", default="admin")
    p.add_argument("--password", default="admin")
    args = p.parse_args()

    login_url = args.url.rstrip("/") + args.login_path
    print(f"[auth] login_url={login_url} user={args.user}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(login_url, wait_until="domcontentloaded")

        # naive field detection; improve for your app
        await page.fill('input[name="username"], input[name="user"], input[type="text"]', args.user)
        await page.fill('input[name="password"], input[type="password"]', args.password)
        await page.click('button[type="submit"], input[type="submit"]')

        await page.wait_for_timeout(1500)
        title = await page.title()
        url   = page.url
        print(f"[auth] after_login url={url} title={title}")
        await page.screenshot(path="/tmp/auth.png")
        print("[auth] screenshot=/tmp/auth.png")

        # naive success heuristic: redirected away from /login
        if "/login" not in url:
            print("[auth] default credentials accepted")
            await browser.close()
            sys.exit(43)  # signal auth bypass

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
