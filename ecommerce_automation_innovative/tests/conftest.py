from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import settings
from core.driver_factory import create_driver
from core.smart_wait import AdWatchdog
from core.visual_highlighter import VisualHighlighter
from data import excel_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

RESULT_STORE: list[dict] = []


def pytest_addoption(parser):
    parser.addoption(
        "--browser",
        action="store",
        default=settings.BROWSER,
        help="Browser to use: chrome | edge",
    )
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode",
    )
    parser.addoption(
        "--excel",
        action="store",
        default=str(settings.EXCEL_PATH),
        help="Path to the test-data Excel workbook",
    )
    parser.addoption(
        "--disable-watchdog",
        action="store_true",
        default=False,
        help="Disable the background ad-overlay watchdog thread",
    )


@pytest.fixture(scope="session")
def dataset(request):
    from data import excel_manager as em
    return em.read_dataset(request.config.getoption("--excel"))


@pytest.fixture(scope="function")
def driver(request):
    browser = request.config.getoption("--browser")
    headless = request.config.getoption("--headless")

    drv = create_driver(browser=browser, headless=headless)

    watchdog = None
    if not request.config.getoption("--disable-watchdog") and settings.AD_WATCHDOG_ENABLED:
        watchdog = AdWatchdog(drv, interval=settings.AD_WATCHDOG_INTERVAL)
        watchdog.start()
    request.node._watchdog = watchdog

    yield drv

    if watchdog:
        watchdog.stop()

    tracker = getattr(request.node, "_exec_tracker", None)
    if tracker and tracker.get("status") == "FAIL" and not tracker.get("screenshot"):
        try:
            hl = VisualHighlighter(drv)
            tracker["screenshot"] = hl.capture(
                tag=f"{tracker.get('scenario', 'failure_audit')}_failure"
            )
        except Exception:
            logger.debug("Could not capture fallback failure screenshot")

    try:
        drv.quit()
    except Exception:
        pass


@pytest.fixture(scope="function", autouse=True)
def execution_tracker(request):
    tracker = {
        "row": None,
        "scenario": None,
        "status": "N/A",
        "elapsed": 0.0,
        "screenshot": "",
        "remarks": "",
    }
    request.node._exec_tracker = tracker
    RESULT_STORE.append(tracker)
    yield tracker


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    tracker = getattr(item, "_exec_tracker", None)
    if tracker is None:
        return

    if rep.when == "call":
        if rep.passed:
            tracker["status"] = "PASS"
        elif rep.skipped:
            tracker["status"] = "SKIP"
        else:
            tracker["status"] = "FAIL"
            tracker["remarks"] = (
                f"{tracker.get('remarks', '')} -> {rep.head_line} :: "
                f"{str(rep.longrepr)[:300]}"
            )
        tracker["elapsed"] = getattr(rep, "duration", 0.0)

    elif rep.when == "setup" and rep.failed:
        tracker["status"] = "FAIL"
        tracker["remarks"] = f"SETUP ERROR :: {str(rep.longrepr)[:300]}"
        tracker["elapsed"] = getattr(rep, "duration", 0.0)


def pytest_sessionfinish(session, exitstatus):
    excel_path = Path(session.config.getoption("--excel"))
    if RESULT_STORE:
        try:
            excel_manager.write_execution_results(excel_path, RESULT_STORE)
            logger.info("Execution results written back to %s", excel_path)
        except Exception as exc:
            logger.error("Failed to write results back to Excel: %s", exc)
            raise


@pytest.hookimpl(optionalhook=True)
def pytest_html_report_title(report):
    report.title = "WIPRO Capstone | E-Commerce Selenium Automation Report"


@pytest.hookimpl(optionalhook=True)
def pytest_html_environment_setup(**kwargs):
    try:
        config = kwargs.get("config")
        browser = config.getoption("--browser") if config else "n/a"
        headless = config.getoption("--headless") if config else False
        import platform

        return [
            ("Application", settings.BASE_URL),
            ("Browser", browser),
            ("Headless", str(headless)),
            ("Platform", platform.platform()),
            ("Python", platform.python_version()),
        ]
    except Exception:
        return None