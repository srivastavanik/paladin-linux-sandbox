# playwright_scenarios/xss.py
import argparse, asyncio, sys, json
from playwright.async_api import async_playwright

XSS_EVENTS_JS = """
window.__xssFired = false;
['alert','confirm','prompt'].forEach(f => {
  const orig = window[f];
  window[f] = function(msg){ window.__xssFired = true; return orig.call(window, msg); };
});
"""

async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--url", required=True)
    p.add_argument("--payload", default="<script>alert('xss')</script>")
    args = p.parse_args()

    print(f"[xss] url={args.url} payload={args.payload}")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.add_init_script(XSS_EVENTS_JS)
        await page.goto(args.url, wait_until="domcontentloaded")

        inputs = page.locator("input, textarea, [contenteditable=true]")
        count = await inputs.count()
        print(f"[xss] inputs_found={count}")

        fired = False
        for i in range(count):
            el = inputs.nth(i)
            try:
                await el.fill(args.payload)
            except Exception:
                continue
        # try submitting any form on the page
        forms = page.locator("form")
        if await forms.count() > 0:
            await forms.nth(0).evaluate("(f)=>f.submit()")
            await page.wait_for_timeout(1000)

        fired = await page.evaluate("window.__xssFired")
        await page.screenshot(path="/tmp/xss.png")
        print(f"[xss] xss_alert={fired} screenshot=/tmp/xss.png")
        await browser.close()

        if fired:
            sys.exit(42)   # signal detection

if __name__ == "__main__":
    asyncio.run(main())
