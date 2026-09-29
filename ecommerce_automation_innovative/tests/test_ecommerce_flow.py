from __future__ import annotations

import base64
import os

import pytest
import pytest_html

from config import settings
from core.smart_wait import AdDismissalEngine
from core.visual_highlighter import VisualHighlighter
from data import excel_manager as em
from workflows.auth_flow import AuthFlow
from workflows.cart_flow import CartFlow
from workflows.search_flow import SearchFlow


def _load_dataset():
    path = os.environ.get("TEST_DATA_XLSX") or str(settings.EXCEL_PATH)
    data = em.read_dataset(path)
    if not data:
        raise RuntimeError(f"No test rows found in workbook: {path}")
    return data


TEST_DATA = _load_dataset()


def _embed_html(path: str, title: str) -> str:
    try:
        with open(path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("utf-8")
        return (
            f'<div style="margin:8px 0">'
            f'<b>{title}</b><br>'
            f'<img style="max-height:280px;border:1px solid #bbb;border-radius:4px" '
            f'src="data:image/png;base64,{b64}"/></div>'
        )
    except OSError:
        return f"<div><b>{title}</b> (screenshot missing)</div>"


@pytest.mark.regression
@pytest.mark.parametrize("row", TEST_DATA, ids=[r["scenario"] for r in TEST_DATA])
def test_full_ecommerce_flow(driver, execution_tracker, row, extras):
    tracker = execution_tracker
    tracker["row"] = row["excel_row"]
    tracker["scenario"] = row["scenario"]

    hl = VisualHighlighter(driver)

    driver.get(settings.BASE_URL)
    AdDismissalEngine.dismiss_all(driver)

    AuthFlow(driver).login(row["email"], row["password"])

    cart = CartFlow(driver)
    cart.reset_cart()

    search = SearchFlow(driver)
    product_id, term = search.search_and_add_to_cart(row["search_term"])
    tracker["remarks"] = f"product_id={product_id} search='{term}'"

    cart = CartFlow(driver)
    cart.open_cart()

    qty_target = int(row["quantity"])
    cart.update_quantity(qty_target)
    qty_element = cart.get_quantity_element()
    hl.highlight(qty_element, color=settings.GREEN, border_px=2, duration_ms=1500)

    result = cart.verify_totals(expected_qty=qty_target)
    total_element = cart.get_total_element()

    shot = hl.highlight_and_capture(
        total_element,
        status=result["all_ok"],
        tag=f"{tracker['scenario']}_cart_total",
        extra_elements=[qty_element],
    )
    tracker["screenshot"] = shot
    extras.append(
        pytest_html.extras.html(
            _embed_html(shot, f"Cart Total Audit - {row['scenario']}")
        )
    )

    cart_summary = cart.get_cart_summary()
    tracker["remarks"] = (
        f"{tracker['remarks']} | grand_total=Rs.{cart_summary['grand_total']:.2f}"
    )

    assert result["all_ok"], (
        f"Cart reconciliation FAILED for '{result['product']}': "
        f"qty={result['actual_qty']} (expected {result['expected_qty']}) | "
        f"total=Rs.{result['actual_total']:.2f} (expected Rs.{result['expected_total']:.2f})"
    )