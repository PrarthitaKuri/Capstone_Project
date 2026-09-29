from __future__ import annotations

import logging
import threading
from typing import Any, Callable, List, Sequence, Tuple

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import EXPLICIT_WAIT, POLL_FREQUENCY, AD_WATCHDOG_INTERVAL

logger = logging.getLogger(__name__)

Locator = Tuple[str, str]
CSS = By.CSS_SELECTOR
XPATH = By.XPATH
ID = By.ID
CLASS = By.CLASS_NAME


class SmartWait:
    def __init__(self, driver: WebDriver, timeout: int | None = None, poll: float | None = None):
        self.driver = driver
        self.timeout = timeout or EXPLICIT_WAIT
        self.poll = poll or POLL_FREQUENCY

    def _wait(self, condition, timeout: int | None = None):
        t = timeout if timeout is not None else self.timeout
        return WebDriverWait(self.driver, t, poll_frequency=self.poll, ignored_exceptions=[
            NoSuchElementException,
            StaleElementReferenceException,
        ]).until(condition)

    def visible(self, locator: Locator, timeout: int | None = None) -> WebElement:
        return self._wait(EC.visibility_of_element_located(locator), timeout)

    def present(self, locator: Locator, timeout: int | None = None) -> WebElement:
        return self._wait(EC.presence_of_element_located(locator), timeout)

    def clickable(self, locator: Locator, timeout: int | None = None) -> WebElement:
        return self._wait(EC.element_to_be_clickable(locator), timeout)

    def click(self, locator: Locator, timeout: int | None = None) -> None:
        el = self.clickable(locator, timeout)
        self._safe_click(el)

    def text_contains(self, locator: Locator, text: str, timeout: int | None = None) -> WebElement:
        return self._wait(EC.text_to_be_present_in_element(locator, text), timeout)

    def title_contains(self, text: str, timeout: int | None = None) -> bool:
        return self._wait(EC.title_contains(text), timeout)

    def url_contains(self, fragment: str, timeout: int | None = None) -> bool:
        return self._wait(EC.url_contains(fragment), timeout)

    def url_matches(self, pattern: str, timeout: int | None = None) -> bool:
        return self._wait(EC.url_matches(pattern), timeout)

    def absence(self, locator: Locator, timeout: int | None = None) -> bool:
        return self._wait(EC.invisibility_of_element_located(locator), timeout)

    def any_visible(self, locators: Sequence[Locator], timeout: int | None = None) -> Tuple[WebElement, Locator]:
        def _check(drv):
            for loc in locators:
                try:
                    el = drv.find_element(*loc)
                    if el.is_displayed():
                        return (el, loc)
                except (NoSuchElementException, StaleElementReferenceException):
                    continue
            return False
        return self._wait(_check, timeout)

    def until(self, condition: Callable[[WebDriver], Any], timeout: int | None = None, message: str = ""):
        return self._wait(condition, timeout)

    def _safe_click(self, element: WebElement) -> None:
        try:
            element.click()
        except ElementClickInterceptedException:
            AdDismissalEngine.dismiss_all(self.driver)
            element.click()


class AdDismissalEngine:
    AD_IFRAME_SELECTORS = [
        'iframe[id*="google_ads"]',
        'iframe[name*="google_ads"]',
        'iframe[id*="aswift"]',
        'iframe[id*="ad_iframe"]',
        'iframe[name*="ad"]',
        'iframe[src*="googleads"]',
        'iframe[src*="doubleclick"]',
        'iframe[src*="googlesyndication"]',
        'iframe[src*="pagead"]',
        'iframe[id*="adContainer"]',
    ]

    AD_DIV_SELECTORS = [
        'ins.adsbygoogle',
        'div[id*="google_ads"]',
        'div[class*="google-auto-placed"]',
        'div[class*="adsbygoogle"]',
        'div[id*="ad_container"]',
        'div[id*="ad-container"]',
        'div[class*="ad-overlay"]',
        'div[id*="overlay-ad"]',
        'div[class*="interstitial"]',
        'div[class*="promo-modal"]',
    ]

    def __init__(self, driver: WebDriver):
        self.driver = driver

    @classmethod
    def dismiss_all(cls, driver: WebDriver, quiet: bool = True) -> None:
        engine = cls(driver)
        engine._remove_ad_iframes(quiet)
        engine._remove_ad_divs(quiet)
        engine._dismiss_overlay_modals(quiet)
        engine._press_escape(quiet)

    @classmethod
    def sweep_ads(cls, driver: WebDriver, quiet: bool = True) -> None:
        engine = cls(driver)
        engine._remove_ad_iframes(quiet)
        engine._remove_ad_divs(quiet)

    def _remove_ad_iframes(self, quiet: bool = True) -> None:
        for sel in self.AD_IFRAME_SELECTORS:
            self._execute_js_removal(
                f"""
                document.querySelectorAll('{sel}').forEach(function(el) {{
                    if (el.parentElement) el.parentElement.removeChild(el);
                }});
                """,
                quiet,
            )

    def _remove_ad_divs(self, quiet: bool = True) -> None:
        for sel in self.AD_DIV_SELECTORS:
            self._execute_js_removal(
                f"""
                document.querySelectorAll('{sel}').forEach(function(el) {{
                    var style = window.getComputedStyle(el);
                    if (style.position === 'fixed' || style.position === 'absolute') {{
                        if (el.parentElement) el.parentElement.removeChild(el);
                    }}
                }});
                """,
                quiet,
            )

    def _dismiss_overlay_modals(self, quiet: bool = True) -> None:
        self._execute_js_removal(
            """
            document.querySelectorAll('div[class*="modal"]').forEach(function(el) {
                if (el.id === 'cartModal' || el.id === 'checkoutModal') return;
                var style = window.getComputedStyle(el);
                if (style.position === 'fixed' && style.zIndex > 1000 &&
                    !el.querySelector('[data-qa="login-email"]')) {
                    var close = el.querySelector('button[data-dismiss], .close, [aria-label="Close"]');
                    if (close) { close.click(); }
                    else if (el.parentElement) { el.parentElement.removeChild(el); }
                }
            });
            """,
            quiet,
        )

    def _press_escape(self, quiet: bool = True) -> None:
        try:
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.common.action_chains import ActionChains
            ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        except WebDriverException:
            if not quiet:
                logger.debug("Failed to press Escape key")

    def _execute_js_removal(self, script: str, quiet: bool = True) -> None:
        try:
            self.driver.execute_script(script)
        except Exception:
            if not quiet:
                logger.debug("JS removal script failed")


class AdWatchdog(threading.Thread):
    def __init__(self, driver: WebDriver, interval: int | None = None, enabled: bool = True):
        super().__init__(daemon=True, name="AdWatchdog")
        self._driver = driver
        self._interval = interval or AD_WATCHDOG_INTERVAL
        self._stop_event = threading.Event()
        self._enabled = enabled

    def run(self) -> None:
        while not self._stop_event.is_set():
            if self._enabled:
                try:
                    AdDismissalEngine.sweep_ads(self._driver, quiet=True)
                except Exception:
                    pass
            self._stop_event.wait(self._interval)

    def stop(self) -> None:
        self._stop_event.set()
