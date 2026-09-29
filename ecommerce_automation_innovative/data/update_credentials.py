from __future__ import annotations

import sys
from pathlib import Path

from openpyxl import load_workbook

EXCEL_PATH = Path(__file__).resolve().parent / "test_data.xlsx"


def stamp_credentials(email: str, password: str, path: Path = EXCEL_PATH) -> None:
    wb = load_workbook(path)
    ws = wb.active
    updated = 0
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value:
            ws.cell(row=r, column=2).value = email
            ws.cell(row=r, column=3).value = password
            updated += 1
    wb.save(path)
    wb.close()
    print(f"Credentials stamped into {updated} row(s) of {path}")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        stamp_credentials(sys.argv[1], sys.argv[2])
    else:
        em = input("Email registered on https://automationexercise.com/: ").strip()
        pw = input("Password: ").strip()
        stamp_credentials(em, pw)