# WIPRO Capstone Assignment 1 — E-Commerce Automation Framework

Automated the full purchase journey on **https://automationexercise.com/** using
**Selenium WebDriver (Python)** — a clean, modular, data-driven framework with
two-way Excel automation, JS-based visual highlighting, an ad/overlay dismissal
engine, and interactive HTML reporting.

---

## 1. Architecture

```
ecommerce_automation_innovative/
├── config/
│   ├── settings.py                  # URLs, wait timeouts, screenshot dirs, brand colors
│   └── __init__.py
├── data/
│   ├── test_data.xlsx               # Input data + write-back of execution results
│   ├── create_test_data.py          # Bootstraps the sample workbook
│   ├── update_credentials.py        # Stamps one registered account into all rows
│   └── excel_manager.py             # Two-way Excel read/write utility
├── core/
│   ├── driver_factory.py            # Chrome / Edge init (headless + anti-popup flags)
│   ├── smart_wait.py                # Smart explicit waits + AdDismissalEngine + AdWatchdog
│   └── visual_highlighter.py        # JS 3px border highlight + PIL-stamped screenshots
├── workflows/
│   ├── auth_flow.py                 # Login / session validation / logout
│   ├── search_flow.py               # Resilient search + product selection + add-to-cart
│   └── cart_flow.py                 # Quantity update + price/math reconciliation
├── tests/
│   ├── conftest.py                  # Fixtures, result tracker, Excel write-back hook
│   └── test_ecommerce_flow.py       # Data-driven end-to-end test (4 scenarios)
├── reports/
│   ├── screenshots/                 # Timestamped, highlighted audit screenshots
│   └── report.html                  # Interactive pytest-html summary (screenshots embedded)
├── pytest.ini                       # Markers + default HTML report generation
├── requirements.txt
└── README.md
```

### Execution flow

```
tests/test_ecommerce_flow.py  (parametrised by test_data.xlsx)
        │
        ├─► DriverFactory ───────────── Chrome/Edge + headless/anti-popup options
        ├─► AuthFlow    ───────────── Login ▶ validate "Logged in as ..."
        ├─► CartFlow    ───────────── reset_cart() ▶ deterministic start (server-side cart cleared)
        ├─► SearchFlow  ───────────── Search ▶ select ▶ add to cart ▶ View Cart
        ├─► CartFlow    ───────────── Update quantity ▶ verify unit × qty = total
        ├─► VisualHighlighter ─────── 3px green/red border ▶ PIL-stamped screenshot
        └─► conftest hooks ────────── PASS/FAIL + time + screenshot ▶ written back to Excel
```

---

## 2. Innovative implementations

1. **Two-way Excel automation** (`data/excel_manager.py`)
   - Reads **Scenario_ID, Email, Password, Search_Term, Quantity** at collection time.
   - Writes back **Status, Execution_Time, Screenshot_Path, Remarks** into the same
     workbook at session end — with green/red row colour-coding. Survives a locked
     workbook by redirecting to a `_results.xlsx` backup.

2. **Smart element highlighter** (`core/visual_highlighter.py`)
   - Applies a temporary **3px border** via `driver.execute_script` — **green = PASS,
     red = FAIL** — around the verified cart-total element (and the quantity control),
     scrolls it into view, captures the audit screenshot, then stamps the verdict and
     timestamp onto the image with **Pillow**, and finally clears the highlight.

3. **Ad / overlay dismissal engine** (`core/smart_wait.py`)
   - `AdDismissalEngine` removes Google Ads iframes/divs and dismisses high-z-index
     overlays via JS DOM surgery + Escape, called at every risky navigation point.
   - `AdWatchdog` runs a **background daemon thread** that silently sweeps the page
     every 3 seconds so late-appearing popups never flake the test.

4. **Zero `time.sleep()`** — every pause is an explicit `WebDriverWait` on a real
   condition (URL, element, text, quantity change).

> **Note on quantity updates:** the live automationexercise cart renders quantity as a
> read-only control, so the framework "updates quantity in cart" the way the site
> intends — it clears the line item, then re-adds the same product with the target
> quantity from the product-detail page (`#quantity` + `.cart`), then re-reads the
> cart and reconciles `unit_price × qty === cart_total_price`.
>
> **State reset:** automationexercise persists the logged-in account's cart server-side,
> so `CartFlow.reset_cart()` empties the cart after login — every scenario starts from a
> clean, deterministic state regardless of what earlier runs left behind.

---

## 3. Setup & run

```powershell
cd ecommerce_automation_innovative
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# 1) Bootstrap the sample workbook
python data\create_test_data.py

# 2) Register ONE free account on https://automationexercise.com/
#    then stamp it into all 4 data rows:
python data\update_credentials.py you@example.com  YourPassword

# 3) Run the suite (headless is quieter/faster)
python -m pytest --headless

# Or headed + a specific browser:
python -m pytest --browser chrome            # or --browser edge
python -m pytest --disable-watchdog          # optional: stop background ad sweeper
```

Artifacts after a run:

- `data/test_data.xlsx` — Status / Execution_Time / Screenshot_Path written back
- `reports/screenshots/*.png` — highlighted, PASS/FAIL-stamped audit captures
- `reports/report.html` — interactive report with embedded screenshots

---

## 4. Sample data

Auto-generated by `data/create_test_data.py` (search terms verified against the site):

| Scenario | Search | Qty | Validated result (sample run) |
|----------|--------|-----|-------------------------------|
| TC_001   | Top    | 3   | product 1 · "Blue Top" · Rs.500 × 3 = Rs.1500 |
| TC_002   | Jeans  | 2   | product 33 · "Soft Stretch Jeans" · Rs.799 × 2 = Rs.1598 |
| TC_003   | Polo   | 4   | product 30 · "Premium Polo T-Shirts" · Rs.1500 × 4 = Rs.6000 |
| TC_004   | Sleeve | 5   | product 3 · "Sleeves Printed Top - White" · Rs.1000 × 5 = Rs.5000 |

> Product list order on automationexercise can vary, so the framework picks the
> **first matching product** for each search term; recorded `grand_total` values above
> were taken from the framework's live cart reconciliation (see `Remarks` column).

The shipped workbook already contains a **real passing run** (Status=PASS, timings,
screenshot links) as proof the framework executes end-to-end green.

---

## 5. Tech stack

Python 3.10+ · Selenium WebDriver 4.x (webdriver-manager) · pytest · pytest-html ·
openpyxl · Pillow

## 6. Hooks & plugins used

- `pytest_runtest_makereport` — captures PASS/FAIL/duration per scenario
- `pytest_sessionfinish` — bulk two-way Excel write-back
- `pytest_html_environment_setup` / `pytest_html_report_title` — branded report