from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
from selenium.common.exceptions import JavascriptException, WebDriverException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

from config.settings import GREEN, RED, SCREENSHOTS_DIR, HIGHLIGHT_JS_TIMEOUT_MS

logger = logging.getLogger(__name__)

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class VisualHighlighter:
    def __init__(self, driver: WebDriver, screenshot_dir: Path | str | None = None):
        self.driver = driver
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir else SCREENSHOTS_DIR
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

    def highlight(
        self,
        element: WebElement,
        color: str = GREEN,
        border_px: int = 3,
        duration_ms: int = HIGHLIGHT_JS_TIMEOUT_MS,
    ) -> None:
        js = """
        var el = arguments[0];
        var color = arguments[1];
        var border = arguments[2];
        var duration = arguments[3];

        el.setAttribute('data-orig-style', el.getAttribute('style') || '');
        el.style.border = border + 'px solid ' + color;
        el.style.boxShadow = '0 0 ' + (border * 2) + 'px ' + color + '80';
        el.scrollIntoView({block: 'center', behavior: 'smooth'});

        if (duration > 0) {
            setTimeout(function() {
                el.style.border = '';
                el.style.boxShadow = '';
                el.removeAttribute('data-orig-style');
            }, duration);
        }
        """
        try:
            self.driver.execute_script(js, element, color, border_px, duration_ms)
        except (JavascriptException, WebDriverException):
            logger.debug("Highlight script failed for element")

    def highlight_and_capture(
        self,
        element: Optional[WebElement],
        status: bool = True,
        tag: str = "audit",
        extra_elements: Optional[list[WebElement]] = None,
    ) -> str:
        color = GREEN if status else RED
        status_label = "PASS" if status else "FAIL"

        if element:
            self.highlight(element, color=color, border_px=3, duration_ms=0)

        if extra_elements:
            for el in extra_elements:
                self.highlight(el, color=color, border_px=2, duration_ms=0)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{tag}_{status_label}.png"
        filepath = self.screenshot_dir / filename

        try:
            self.driver.save_screenshot(str(filepath))
            self._stamp_image(filepath, status_label, color)
        except WebDriverException:
            logger.warning("Screenshot capture failed; generating fallback")
            filepath = self._fallback_screenshot(filepath, status_label, color)

        if element:
            self._clear_highlight(element)

        logger.info("Audit screenshot: %s", filepath)
        return str(filepath)

    def capture(self, tag: str = "failure", status: bool = False) -> str:
        color = RED if not status else GREEN
        label = "FAIL" if not status else "PASS"
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{tag}_{label}.png"
        filepath = self.screenshot_dir / filename
        try:
            self.driver.save_screenshot(str(filepath))
            self._stamp_image(filepath, label, color)
        except WebDriverException:
            filepath = self._fallback_screenshot(filepath, label, color)
        return str(filepath)

    def _clear_highlight(self, element: WebElement) -> None:
        js = """
        var el = arguments[0];
        el.style.border = '';
        el.style.boxShadow = '';
        el.removeAttribute('data-orig-style');
        """
        try:
            self.driver.execute_script(js, element)
        except (JavascriptException, WebDriverException):
            pass

    @staticmethod
    def _stamp_image(filepath: Path, label: str, color_hex: str) -> None:
        try:
            img = Image.open(filepath)
            draw = ImageDraw.Draw(img, "RGBA")

            font_size = 28
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except OSError:
                try:
                    font = ImageFont.load_default(size=font_size)
                except TypeError:
                    font = ImageFont.load_default()

            text_bbox = draw.textbbox((0, 0), label, font=font)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]

            padding = 10
            x, y = 10, 10
            bg_color = (
                int(color_hex[1:3], 16),
                int(color_hex[3:5], 16),
                int(color_hex[5:7], 16),
                200,
            )
            draw.rectangle(
                [x - padding, y - padding, x + text_w + padding, y + text_h + padding],
                fill=bg_color,
            )
            draw.text((x, y), label, fill="white", font=font)

            timestamp_text = time.strftime("%Y-%m-%d %H:%M:%S")
            small_font_size = 14
            try:
                small_font = ImageFont.truetype("arial.ttf", small_font_size)
            except OSError:
                try:
                    small_font = ImageFont.load_default(size=small_font_size)
                except TypeError:
                    small_font = ImageFont.load_default()

            ts_bbox = draw.textbbox((0, 0), timestamp_text, font=small_font)
            ts_w = ts_bbox[2] - ts_bbox[0]
            ts_x = img.width - ts_w - 15
            ts_y = 15
            draw.rectangle(
                [ts_x - 5, ts_y - 5, ts_x + ts_w + 5, ts_y + 18],
                fill=(0, 0, 0, 160),
            )
            draw.text((ts_x, ts_y), timestamp_text, fill="white", font=small_font)

            img.save(filepath)
        except Exception as exc:
            logger.debug("PIL stamp failed (%s); screenshot saved unstamped", exc)

    @staticmethod
    def _fallback_screenshot(filepath: Path, label: str, color_hex: str) -> Path:
        try:
            img = Image.new("RGB", (800, 600), color=(30, 30, 30))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("arial.ttf", 32)
            except OSError:
                try:
                    font = ImageFont.load_default(size=32)
                except TypeError:
                    font = ImageFont.load_default()
            draw.text(
                (50, 250),
                f"Screenshot unavailable - {label}",
                fill="white",
                font=font,
            )
            img.save(filepath)
        except Exception:
            filepath.touch()
        return filepath
