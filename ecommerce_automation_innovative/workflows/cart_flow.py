from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import BASE_URL
from core.smart_wait import SmartWait, AdDismissalEngine

logger = logging.getLogger(__name__)

LOC_CART_TABLE = (By.CSS_SELECTOR, "#cart_info_table")
LOC_CART_ROWS = (By.CSS_SELECTOR, "#cart_info_table tbody tr[id*='product-']")
LOC_EMPTY_CART = (By.CSS_SELECTOR, "#empty_cart")
LOC_QTY_BUTTON = (By.CSS_SELECTOR, "td.cart_quantity button, .cart_quantity button")
LOC_QTY_INPUT = (By.CSS_SELECTOR, "input.cart_quantity_input")
LOC_PRICE = (By.CSS_SELECTOR, ".cart_price p")
LOC_TOTAL = (By.CSS_SELECTOR, ".cart_total .cart_total_price")
LOC_PRODUCT_NAME = (By.CSS_SELECTOR, ".cart_description h4 a")
LOC_DELETE_ITEM = (By.CSS_SELECTOR, "a.cart_quantity_delete")
LOC_QTY_UP = (By.CSS_SELECTOR, "a.cart_quantity_up")
LOC_QTY_DOWN = (By.CSS_SELECTOR, "a.cart_quantity_down")

LOC_DETAIL_QUANTITY = (By.CSS_SELECTOR, "#quantity")
LOC_DETAIL_ADD_BUTTON = (By.CSS_SELECTOR, "button.cart, a.cart, .btn.cart")
LOC_CART_MODAL_SHOW = (By.CSS_SELECTOR, "#cartModal.show")
LOC_VIEW_CART_LINK = (By.CSS_SELECTOR, '#cartModal a[href="/view_cart"]')

_PRICE_RE = re.compile(r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)")


def _parse_price(text: str) -> float:
    match = _PRICE_RE.search(text)
    if not match:
        clean = re.sub(r"[^\d.]", "", text)
        return float(clean) if clean else 0.0
    return float(match.group(1).replace(",", ""))


class CartFlow:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.sw = SmartWait(driver)

    def open_cart(self) -> None:
        current = self.driver.current_url
        if "view_cart" not in current:
            self.driver.get(f"{BASE_URL}/view_cart")
        AdDismissalEngine.dismiss_all(self.driver)
        self.sw.present(LOC_CART_TABLE, timeout=15)

    def reset_cart(self) -> None:
        self.driver.get(f"{BASE_URL}/view_cart")
        AdDismissalEngine.dismiss_all(self.driver)
        try:
            empty = self.driver.find_element(*LOC_EMPTY_CART)
            if empty.is_displayed():
                logger.info("Cart already empty; no reset needed")
                return
        except NoSuchElementException:
            pass
        self.sw.present(LOC_CART_TABLE, timeout=15)
        self.clear_cart()
        logger.info("Cart reset to empty (deterministic starting state)")

    def get_all_rows(self) -> List[WebElement]:
        return self.driver.find_elements(*LOC_CART_ROWS)

    def get_first_row(self) -> WebElement:
        return self.sw.present(LOC_CART_ROWS)

    def get_product_id(self, row: Optional[WebElement] = None) -> str:
        row = row or self.get_first_row()
        row_id = row.get_attribute("id") or ""
        return row_id.replace("product-", "").strip()

    def get_product_name(self, row: Optional[WebElement] = None) -> str:
        row = row or self.get_first_row()
        try:
            return row.find_element(*LOC_PRODUCT_NAME).text.strip()
        except NoSuchElementException:
            return "Unknown"

    def current_qty(self, row: Optional[WebElement] = None) -> int:
        row = row or self.get_first_row()
        try:
            qty_btn = row.find_element(*LOC_QTY_BUTTON)
            return int(qty_btn.text.strip() or "1")
        except (NoSuchElementException, ValueError):
            try:
                qty_inp = row.find_element(*LOC_QTY_INPUT)
                return int(qty_inp.get_attribute("value") or "1")
            except (NoSuchElementException, ValueError):
                return 1

    def get_quantity_element(self, row: Optional[WebElement] = None) -> WebElement:
        row = row or self.get_first_row()
        try:
            return row.find_element(*LOC_QTY_BUTTON)
        except NoSuchElementException:
            return row.find_element(*LOC_QTY_INPUT)

    def get_unit_price(self, row: Optional[WebElement] = None) -> float:
        row = row or self.get_first_row()
        return _parse_price(row.find_element(*LOC_PRICE).text)

    def get_row_total(self, row: Optional[WebElement] = None) -> float:
        row = row or self.get_first_row()
        return _parse_price(row.find_element(*LOC_TOTAL).text)

    def get_total_element(self, row: Optional[WebElement] = None) -> WebElement:
        row = row or self.get_first_row()
        return row.find_element(*LOC_TOTAL)

    def wait_for_qty(self, target: int, row: Optional[WebElement] = None, timeout: int = 15):
        row = row or self.get_first_row()
        qty_el = row.find_element(*LOC_QTY_BUTTON)

        def _check(drv):
            try:
                return int(qty_el.text.strip()) == target
            except ValueError:
                return False

        WebDriverWait(self.driver, timeout, poll_frequency=0.4).until(_check)

    def clear_cart(self) -> None:
        delete_links = self.driver.find_elements(*LOC_DELETE_ITEM)
        for link in delete_links:
            try:
                self._safe_click(link)
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", link)
                except Exception:
                    continue
        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(LOC_EMPTY_CART)
            )
            logger.info("Cart cleared (%d item(s) removed)", len(delete_links))
        except TimeoutException:
            remaining = len(self.driver.find_elements(*LOC_DELETE_ITEM))
            logger.warning("Cart clear incomplete; %d item(s) remain", remaining)

    def add_with_quantity(self, product_id: str, quantity: int) -> Dict:
        detail_url = f"{BASE_URL}/product_details/{product_id}"
        self.driver.get(detail_url)
        AdDismissalEngine.dismiss_all(self.driver)

        qty_input = self.sw.present(LOC_DETAIL_QUANTITY, timeout=15)
        qty_input.clear()
        qty_input.send_keys(str(quantity))

        add_btn = self.sw.clickable(LOC_DETAIL_ADD_BUTTON, timeout=10)
        self._safe_click(add_btn)

        self.sw.present(LOC_CART_MODAL_SHOW, timeout=10)
        AdDismissalEngine.dismiss_all(self.driver)

        self.sw.click(LOC_VIEW_CART_LINK, timeout=10)
        self.sw.url_contains("view_cart", timeout=15)
        self.sw.present(LOC_CART_ROWS, timeout=15)

        row = self.get_first_row()
        info = {
            "product_id": self.get_product_id(row),
            "product": self.get_product_name(row),
            "unit_price": self.get_unit_price(row),
            "quantity": self.current_qty(row),
            "total": self.get_row_total(row),
        }
        logger.info("Added %d x %s to cart -> %s", quantity, info["product"], info)
        return info

    def update_quantity(self, target: int, product_id: Optional[str] = None) -> None:
        row = self.get_first_row()
        pid = product_id or self.get_product_id(row)
        current = self.current_qty(row)

        if current == target:
            logger.info("Cart quantity already %d; no update required", target)
            return

        self.clear_cart()
        info = self.add_with_quantity(pid, target)

        if info["quantity"] != target:
            raise AssertionError(
                f"Quantity update failed: expected {target}, cart shows {info['quantity']}"
            )
        logger.info(
            "Quantity updated in cart: %d -> %d for product %s",
            current, target, pid,
        )

    def verify_totals(self, expected_qty: Optional[int] = None) -> Dict:
        row = self.get_first_row()
        product_name = self.get_product_name(row)
        unit_price = self.get_unit_price(row)
        actual_qty = self.current_qty(row)
        actual_total = self.get_row_total(row)
        expected_total = round(unit_price * actual_qty, 2)

        qty_ok = (expected_qty is None) or (actual_qty == expected_qty)
        price_ok = abs(actual_total - expected_total) < 0.01

        result = {
            "product": product_name,
            "unit_price": unit_price,
            "expected_qty": expected_qty,
            "actual_qty": actual_qty,
            "qty_ok": qty_ok,
            "expected_total": expected_total,
            "actual_total": actual_total,
            "price_ok": price_ok,
            "all_ok": qty_ok and price_ok,
        }

        logger.info(
            "Cart verification: %s | qty=%d (expected=%s) | "
            "total=Rs.%.2f (expected=Rs.%.2f) | ok=%s",
            product_name, actual_qty, expected_qty,
            actual_total, expected_total, result["all_ok"],
        )
        return result

    def get_cart_summary(self) -> Dict:
        rows = self.get_all_rows()
        items = []
        grand_total = 0.0
        for row in rows:
            info = {
                "name": self.get_product_name(row),
                "price": self.get_unit_price(row),
                "quantity": self.current_qty(row),
                "total": self.get_row_total(row),
            }
            items.append(info)
            grand_total += info["total"]

        summary = {
            "items": items,
            "item_count": len(items),
            "grand_total": grand_total,
        }
        logger.info(
            "Cart summary: item_count=%d grand_total=Rs.%.2f -> %s",
            summary["item_count"], summary["grand_total"], items,
        )
        return summary

    def _safe_click(self, element: WebElement) -> None:
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)