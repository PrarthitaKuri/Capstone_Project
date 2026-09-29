from __future__ import annotations

import logging
from typing import List

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

COLUMN_HEADERS = {
    "A": "Scenario_ID",
    "B": "Email",
    "C": "Password",
    "D": "Search_Term",
    "E": "Quantity",
    "F": "Status",
    "G": "Execution_Time",
    "H": "Screenshot_Path",
    "I": "Remarks",
}

RESULT_COLS = {
    "status": "F",
    "exec_time": "G",
    "screenshot": "H",
    "remarks": "I",
}

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
PASS_FILL = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
PASS_FONT = Font(bold=True, color="006100")
FAIL_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
FAIL_FONT = Font(bold=True, color="9C0006")
CENTER = Alignment(horizontal="center", vertical="center")


def read_dataset(path) -> List[dict]:
    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows: List[dict] = []
    for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row[0]:
            continue
        rows.append(
            {
                "excel_row": idx,
                "scenario": str(row[0]).strip(),
                "email": str(row[1]).strip(),
                "password": str(row[2]).strip(),
                "search_term": str(row[3]).strip(),
                "quantity": int(row[4]),
                "status": "",
                "exec_time": "",
                "screenshot": "",
                "remarks": "",
            }
        )
    wb.close()
    return rows


def write_execution_results(path, results: list[dict]) -> None:
    target = str(path)
    try:
        wb = load_workbook(target)
    except PermissionError:
        backup = str(path).replace(".xlsx", "_results.xlsx")
        logger.warning("Excel file is locked by another program. Writing to %s", backup)
        target = backup
        try:
            wb = load_workbook(target)
        except Exception:
            wb = Workbook()
            ws0 = wb.active
            for col_letter, header in COLUMN_HEADERS.items():
                ws0[f"{col_letter}1"] = header
    ws = wb.active

    for col_letter, header in COLUMN_HEADERS.items():
        cell = ws[f"{col_letter}1"]
        cell.value = header
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER

    for res in results:
        row_num = res.get("row")
        if not row_num:
            continue
        status = res.get("status", "N/A")
        exec_time = res.get("elapsed", "")
        screenshot = res.get("screenshot", "")
        remarks = res.get("remarks", "")

        ws[f"{RESULT_COLS['status']}{row_num}"] = status
        ws[f"{RESULT_COLS['exec_time']}{row_num}"] = f"{exec_time:.2f}s" if isinstance(exec_time, (int, float)) else str(exec_time)
        ws[f"{RESULT_COLS['screenshot']}{row_num}"] = screenshot
        ws[f"{RESULT_COLS['remarks']}{row_num}"] = remarks

        fill = PASS_FILL if status == "PASS" else FAIL_FILL
        font = PASS_FONT if status == "PASS" else FAIL_FONT
        for col in ["F", "G", "H", "I"]:
            c = ws[f"{col}{row_num}"]
            c.fill = fill
            c.font = font
            c.alignment = CENTER

    for col_letter in COLUMN_HEADERS:
        ws.column_dimensions[col_letter].width = 22

    wb.save(target)
    logger.info("Results written to %s", target)
    wb.close()
