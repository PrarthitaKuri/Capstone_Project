from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

HEADERS = [
    "Scenario_ID",
    "Email",
    "Password",
    "Search_Term",
    "Quantity",
    "Status",
    "Execution_Time",
    "Screenshot_Path",
    "Remarks",
]

SAMPLE_ROWS = [
    ["TC_001", "capstone.qa01@automation.test", "Wipro@2024!", "Top", 3],
    ["TC_002", "capstone.qa02@automation.test", "Wipro@2024!", "Jeans", 2],
    ["TC_003", "capstone.qa03@automation.test", "Wipro@2024!", "Polo", 4],
    ["TC_004", "capstone.qa04@automation.test", "Wipro@2024!", "Sleeve", 5],
]

HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
CENTER = Alignment(horizontal="center", vertical="center")

EXCEL_PATH = Path(__file__).resolve().parent / "test_data.xlsx"


def create_workbook(path: Path = EXCEL_PATH) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "TestData"

    for idx, header in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=idx, value=header)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = CENTER

    for r_idx, record in enumerate(SAMPLE_ROWS, start=2):
        for c_idx, value in enumerate(record, start=1):
            cell = ws.cell(row=r_idx, column=c_idx, value=value)
            cell.alignment = CENTER

    for c_idx in range(1, len(HEADERS) + 1):
        ws.column_dimensions[get_column_letter(c_idx)].width = 22

    wb.save(path)
    print(f"Sample test-data workbook created: {path}")
    print("Rows written:")
    for record in SAMPLE_ROWS:
        print(f"   {record[0]:8} | {record[1]:30} | term={record[3]:8} | qty={record[4]}")
    print("\nNOTE: Overwrite the email/password columns with accounts you")
    print("registered at https://automationexercise.com/ (Signup is free).")
    return path


if __name__ == "__main__":
    create_workbook()