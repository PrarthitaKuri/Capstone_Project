from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASE_URL = "https://automationexercise.com"
LOGIN_URL = f"{BASE_URL}/login"
PRODUCTS_URL = f"{BASE_URL}/products"
CART_URL = f"{BASE_URL}/view_cart"
SIGNUP_URL = f"{BASE_URL}/signup"

EXPLICIT_WAIT = 20
POLL_FREQUENCY = 0.5

SCREENSHOTS_DIR = PROJECT_ROOT / "reports" / "screenshots"
REPORTS_DIR = PROJECT_ROOT / "reports"
EXCEL_PATH = PROJECT_ROOT / "data" / "test_data.xlsx"

BROWSER = "chrome"
HEADLESS = False
AD_WATCHDOG_ENABLED = True
AD_WATCHDOG_INTERVAL = 3

GREEN = "#00C853"
RED = "#FF1744"
HIGHLIGHT_JS_TIMEOUT_MS = 3000
