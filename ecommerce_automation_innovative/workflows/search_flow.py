from __future__ import annotations

import logging
from typing import Optional, Tuple

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from config.settings import PRODUCTS_URL
from core.smart_wait import SmartWait, AdDismissalEngine

logger = logging.getLogger(__name__)

LOC_SEARCH_INPUT = (By.CSS_SELECTOR, "#search_product")
LOC_SEARCH_BUTTON = (By.CSS_SELECTOR, "#submit_search")
LOC_PRODUCT_WRAPPERS = (By.CSS_SELECTOR, ".features_items .product-image-wrapper")
LOC_CART_MODAL = (By.CSS_SELECTOR, "#cartModal")
LOC_CART_MODAL_SHOW = (By.CSS_SELECTOR, "#cartModal.show")
LOC_VIEW_CART_LINK = (By.CSS_SELECTOR, '#cartModal a[href="/view_cart"]')
LOC_CONTINUE_SHOPPING = (By.CSS_SELECTOR, "#cartModal .close-modal")


class SearchFlow:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.sw = SmartWait(driver)
        self._last_product_id: Optional[str] = None

    def navigate_to_products(self) -> None:
        self.driver.get(PRODUCTS_URL)
        AdDismissalEngine.dismiss_all(self.driver)
        self.sw.present(LOC_SEARCH_INPUT)

    def search(self, term: str) -> list[WebElement]:
        self.navigate_to_products()
        search_box = self.sw.present(LOC_SEARCH_INPUT)
        search_box.clear()
        search_box.send_keys(term)
        self.sw.click(LOC_SEARCH_BUTTON)
        self.sw.url_contains("search=", timeout=15)
        AdDismissalEngine.dismiss_all(self.driver)

        try:
            self.sw.present(LOC_PRODUCT_WRAPPERS, timeout=15)
        except TimeoutException:
            logger.warning("No products found for search term: %s", term)
            return []

        wrappers = self.driver.find_elements(*LOC_PRODUCT_WRAPPERS)
        logger.info("Found %d product(s) for term '%s'", len(wrappers), term)
        return wrappers

    def select_product_by_term(self, term: str) -> Optional[WebElement]:
        wrappers = self.driver.find_elements(*LOC_PRODUCT_WRAPPERS)
        term_lower = term.lower()
        for wrapper in wrappers:
            try:
                name_el = wrapper.find_element(By.CSS_SELECTOR, ".productinfo p")
                if term_lower in name_el.text.lower():
                    return wrapper
            except NoSuchElementException:
                continue
        if wrappers:
            return wrappers[0]
        return None

    def add_to_cart_from_products(self, wrapper: WebElement) -> str:
        product_id = wrapper.get_attribute("data-product-id") or ""
        if not product_id:
            pid_el = wrapper.find_element(By.CSS_SELECTOR, "a.add-to-cart")
            product_id = pid_el.get_attribute("data-product-id") or "unknown"

        add_btn = wrapper.find_element(By.CSS_SELECTOR, ".productinfo .add-to-cart")
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", add_btn)
        AdDismissalEngine.dismiss_all(self.driver)
        self._force_click(add_btn)

        try:
            self.sw.present(LOC_CART_MODAL_SHOW, timeout=10)
        except TimeoutException:
            self.sw.present(LOC_CART_MODAL)
            self.driver.execute_script(
                "document.querySelector('#cartModal').classList.add('show');"
            )

        AdDismissalEngine.dismiss_all(self.driver)
        self._last_product_id = product_id
        logger.info("Added product %s to cart", product_id)
        return product_id

    def click_view_cart(self) -> None:
        self.sw.click(LOC_VIEW_CART_LINK, timeout=10)
        self.sw.url_contains("view_cart", timeout=15)
        AdDismissalEngine.dismiss_all(self.driver)

    def click_continue_shopping(self) -> None:
        self.sw.click(LOC_CONTINUE_SHOPPING, timeout=5)

    def search_and_add_to_cart(self, term: str) -> Tuple[str, str]:
        self.search(term)
        wrapper = self.select_product_by_term(term)
        if not wrapper:
            raise AssertionError(f"No product found matching term: {term}")
        pid = self.add_to_cart_from_products(wrapper)
        self.click_view_cart()
        return pid, term

    def _force_click(self, element: WebElement) -> None:
        try:
            element.click()
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
