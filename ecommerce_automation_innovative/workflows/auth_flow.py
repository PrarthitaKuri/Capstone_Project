from __future__ import annotations

import logging

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from config.settings import BASE_URL, LOGIN_URL
from core.smart_wait import SmartWait, AdDismissalEngine

logger = logging.getLogger(__name__)

LOC_LOGIN_EMAIL = (By.CSS_SELECTOR, '[data-qa="login-email"]')
LOC_LOGIN_PASSWORD = (By.CSS_SELECTOR, '[data-qa="login-password"]')
LOC_LOGIN_BUTTON = (By.CSS_SELECTOR, '[data-qa="login-button"]')
LOC_LOGGED_IN_TEXT = (By.XPATH, '//a[contains(text(), "Logged in as")]')
LOC_USER_ICON = (By.CSS_SELECTOR, '.fa-user')
LOC_LOGIN_LINK = (By.CSS_SELECTOR, 'a[href="/login"]')
LOC_LOGOUT_LINK = (By.CSS_SELECTOR, 'a[href="/logout"]')
LOC_ALERT_LOGIN = (By.CSS_SELECTOR, '.login-form p')
LOC_ALERT_SIGNUP = (By.CSS_SELECTOR, '.signup-form p')


class AuthFlow:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.sw = SmartWait(driver)

    def navigate_to_login(self) -> None:
        self.driver.get(LOGIN_URL)
        AdDismissalEngine.dismiss_all(self.driver)
        self.sw.present(LOC_LOGIN_EMAIL)

    def login(self, email: str, password: str) -> bool:
        if self.is_logged_in():
            logger.info("Already logged in; skipping login")
            return True

        self.navigate_to_login()
        self.sw.present(LOC_LOGIN_EMAIL).send_keys(email)
        self.sw.present(LOC_LOGIN_PASSWORD).send_keys(password)
        self.sw.click(LOC_LOGIN_BUTTON)

        try:
            self.sw.url_contains("/", timeout=15)
        except TimeoutException:
            pass

        AdDismissalEngine.dismiss_all(self.driver)

        if self.is_logged_in():
            logger.info("Login successful for %s", email)
            return True

        error = self._get_login_error()
        raise AssertionError(f"Login failed for {email}: {error}")

    def is_logged_in(self) -> bool:
        try:
            el = self.driver.find_element(*LOC_LOGGED_IN_TEXT)
            return bool(el.text.strip())
        except NoSuchElementException:
            pass

        try:
            user_icon = self.driver.find_element(*LOC_USER_ICON)
            nav = self.driver.find_element(By.CSS_SELECTOR, ".shop-menu")
            if "Logged in as" in nav.text:
                return True
        except NoSuchElementException:
            pass

        try:
            self.driver.find_element(By.CSS_SELECTOR, 'a[href="/logout"]')
            return True
        except NoSuchElementException:
            pass

        return False

    def get_logged_in_username(self) -> str:
        try:
            el = self.driver.find_element(*LOC_LOGGED_IN_TEXT)
            text = el.text.strip()
            marker = "Logged in as"
            if marker in text:
                return text.split(marker, 1)[1].strip()
        except NoSuchElementException:
            pass
        return ""

    def logout(self) -> None:
        self.driver.get(f"{BASE_URL}/logout")
        self.sw.present(LOC_LOGIN_EMAIL)

    def _get_login_error(self) -> str:
        for selector in [LOC_ALERT_LOGIN, LOC_ALERT_SIGNUP]:
            try:
                el = self.driver.find_element(*selector)
                if el.text.strip():
                    return el.text.strip()
            except NoSuchElementException:
                continue
        return "Unknown error - check credentials"
