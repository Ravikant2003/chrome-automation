# app/browser/launcher.py

from pydoll.browser.options import ChromiumOptions

def get_browser_options(profile_path: str, binary_path: str = None):
    options = ChromiumOptions()

    # ----- BROWSER PATH GOES HERE -----
    if binary_path:
        options.binary_location = binary_path
    else:
        # Default (Docker path)
        options.binary_location = "/usr/bin/chromium"
    # ----------------------------------

    options.user_data_dir = profile_path

    #options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")


    return options
