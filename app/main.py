# app/main.py  (OPTION B — Real Chrome + CDP + AUTO-LAUNCH + PATH-SAFE)

import asyncio
import os
import random
import logging
import aiohttp
import subprocess
import sys

from pydoll.browser import Chrome
from browser.cdp_utils import cdp
from utils.artifacts import save_artifacts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("Phase1_OptionB")

TARGET_URL = "https://www.scrapingcourse.com/antibot-challenge"

# -------- PATH HANDLING (LOCAL + DOCKER SAFE) --------
if os.path.exists("/.dockerenv"):   # Running inside Docker
    OUTPUT_DIR = "/app/output"
else:                               # Running locally on your Mac
    OUTPUT_DIR = os.path.expanduser("~/pydoll_output")

logger.info(f"Using OUTPUT_DIR = {OUTPUT_DIR}")

# =====================================================
# 1) PUBLIC IP UTILITY
# =====================================================

async def get_public_ip():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org?format=json", timeout=10) as resp:
                data = await resp.json()
                return data.get("ip", "unknown")
    except Exception as e:
        logger.error(f"Failed to get public IP: {e}")
        return "unknown"

# =====================================================
# 2) AUTO-LAUNCH CHROME (IF NOT RUNNING)
# =====================================================

async def ensure_chrome_running():
    """
    Ensure Chrome is running with remote debugging enabled.
    If not, launch it automatically.
    """

    debug_url = "http://docker.for.mac.localhost:9222/json"

    # Check if Chrome is already running with debugging
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(debug_url, timeout=3) as resp:
                if resp.status == 200:
                    logger.info("✅ Chrome already running with remote debugging.")
                    return
    except:
        logger.info("Chrome not detected on 9222 — launching automatically...")

    # Launch Chrome on Mac
    chrome_cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--remote-debugging-port=9222",
        "--remote-debugging-address=0.0.0.0",
        "--user-data-dir=" + os.path.expanduser("~/chrome_debug_profile"),
    ]

    try:
        subprocess.Popen(chrome_cmd)
        logger.info("🚀 Launched Chrome with remote debugging enabled.")
    except Exception as e:
        logger.error(f"Failed to launch Chrome: {e}")
        sys.exit(1)

    # Wait for Chrome to be ready
    for i in range(15):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(debug_url, timeout=3) as resp:
                    if resp.status == 200:
                        logger.info("✅ Chrome is now ready for CDP.")
                        return
        except:
            await asyncio.sleep(1)

    raise RuntimeError("Chrome did not start on port 9222 in time.")

# =====================================================
# 3) DISCOVER REAL CHROME WS URL
# =====================================================

async def get_chrome_ws_url():
    debug_url = "http://docker.for.mac.localhost:9222/json"
    logger.info(f"Querying Chrome debugger at: {debug_url}")

    async with aiohttp.ClientSession() as session:
        async with session.get(debug_url, timeout=10) as resp:
            data = await resp.json()

    # Prefer a clean "New tab"
    for entry in data:
        if entry.get("type") == "page" and entry.get("title") == "New tab":
            ws_url = entry.get("webSocketDebuggerUrl")
            logger.info(f"Selected NEW TAB WS URL: {ws_url}")
            return ws_url

    # Fallback: first available page
    for entry in data:
        if entry.get("type") == "page":
            ws_url = entry.get("webSocketDebuggerUrl")
            logger.info(f"Using fallback PAGE WS URL: {ws_url}")
            return ws_url

    raise RuntimeError("No usable Chrome page WebSocket found!")

# =====================================================
# 4) HUMAN BEHAVIOR HELPERS
# =====================================================

async def human_mouse_move(page, steps=15):
    logger.info("Simulating human-like mouse movement...")
    for _ in range(steps):
        x = random.randint(100, 1200)
        y = random.randint(100, 700)
        await cdp(
            page,
            "Runtime.evaluate",
            {
                "expression": f"""
                window.dispatchEvent(new MouseEvent('mousemove', {{
                    clientX: {x}, clientY: {y}, bubbles: true
                }}));
                """
            },
        )
        await asyncio.sleep(random.uniform(0.02, 0.12))


async def wait_for_cloudflare(page, timeout=40):
    logger.info("Waiting for Cloudflare challenge...")

    for second in range(timeout):
        res = await cdp(
            page,
            "Runtime.evaluate",
            {"expression": "document.title"},
        )

        title = (res.get("result", {}).get("value") or "").lower()
        logger.info(f"[{second}s] Page title: {title}")

        if "just a moment" not in title:
            logger.info("Cloudflare passed.")
            return True

        await asyncio.sleep(1)

    logger.warning("Cloudflare timeout.")
    return False

# =====================================================
# 5) MAIN PIPELINE
# =====================================================

async def main():
    logger.info("🚀 Starting Phase 1 — OPTION B (Real Chrome + CDP)")

    public_ip = await get_public_ip()
    logger.info(f"🌍 Current Public IP: {public_ip}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ✅ AUTO-LAUNCH CHROME IF NEEDED
    await ensure_chrome_running()

    ws_url = await get_chrome_ws_url()

    async with Chrome() as browser:
        logger.info(f"Connecting to Chrome via {ws_url}")
        await browser.connect(ws_url)

        # Use low-level handler as our "page"
        handler = browser._connection_handler

        class PageProxy:
            def __init__(self, handler):
                self._connection_handler = handler

            async def go_to(self, url):
                await handler.execute_command({
                    "method": "Page.navigate",
                    "params": {"url": url}
                })

            @property
            async def page_source(self):
                res = await handler.execute_command({
                    "method": "Page.getFrameTree"
                })
                return str(res)

        page = PageProxy(handler)

        # Enable CDP domains
        await cdp(page, "Page.enable")
        await cdp(page, "Runtime.enable")
        await cdp(page, "Network.enable")

        logger.info(f"📡 Navigating to {TARGET_URL}")
        await page.go_to(TARGET_URL)

        passed = await wait_for_cloudflare(page)
        if not passed:
            logger.error("Cloudflare likely blocked the session.")
            return

        await human_mouse_move(page)

        # Save artifacts (robust, retry-based)
        await save_artifacts(page, OUTPUT_DIR, logger, public_ip)

        logger.info("🏁 Option B session complete.")

if __name__ == "__main__":
    asyncio.run(main())
