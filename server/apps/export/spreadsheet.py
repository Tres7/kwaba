"""CSV files opened in a spreadsheet (Excel, LibreOffice, Google Sheets)."""
import csv
import io
from collections.abc import Iterable

from django.http import HttpResponse

# First characters that make a spreadsheet read a cell as a formula
FORMULA_STARTS = ('=', '+', '-', '@', '\t', '\r')


def safe_cell(value):
    """A text cell that starts like a formula is written as text, behind an apostrophe: a name, an email or a
    summary may contain "=HYPERLINK(…)". Other values (numbers, dates) are left as they are."""
    if isinstance(value, str) and value.startswith(FORMULA_STARTS):
        return f"'{value}"
    return value


def safe_row(cells) -> list:
    return [safe_cell(cell) for cell in cells]


def csv_response(header: list[str], rows: Iterable[list], filename: str) -> HttpResponse:
    """Download of a CSV for a spreadsheet: separator ;, UTF-8 with BOM for Excel, every cell made safe, never cached."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(safe_row(header))
    for row in rows:
        writer.writerow(safe_row(row))
    response = HttpResponse('﻿' + buffer.getvalue(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'private, no-store'
    return response
