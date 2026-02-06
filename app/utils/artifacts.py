# app/utils/artifacts.py

import base64
from pathlib import Path
from browser.cdp_utils import cdp

async def save_artifacts(page, output_dir, logger, public_ip="unknown"):
    """
    Robust artifact saver for Option B (Real Chrome + Docker).
    Best-effort, with retries + fallback.
    """

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # ---- 1) TRY SCREENSHOT (with retry) ----
    screenshot_path = Path(output_dir) / "phase1_result.png"

    success = False
    for attempt in range(3):
        try:
            logger.info(f"📸 Attempting screenshot (try {attempt+1}/3)...")

            shot = await cdp(
                page,
                "Page.captureScreenshot",
                {"format": "png"},
                timeout=20,   # shorter timeout per attempt
            )

            data = shot.get("result", {}).get("data")
            if data:
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(data))
                logger.info(f"Screenshot saved: {screenshot_path}")
                success = True
                break

        except Exception as e:
            logger.warning(f"Screenshot attempt {attempt+1} failed: {e}")

    if not success:
        logger.error("⚠️ Screenshot failed after 3 retries — continuing anyway.")

    # ---- 2) SAVE PAGE HTML (safer) ----
    try:
        html = await page.page_source
        html_path = Path(output_dir) / "page.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        logger.info(f"HTML saved: {html_path}")
    except Exception as e:
        logger.error(f"Failed to save HTML: {e}")

    # ---- 3) SAVE METADATA (useful for your report) ----
    meta_path = Path(output_dir) / "session_meta.txt"
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"public_ip={public_ip}\n")
    logger.info(f"Session metadata saved: {meta_path}")
