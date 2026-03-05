"""CSV export generator with UTF-8 BOM and configurable delimiter."""

import csv
import logging
from io import BytesIO, StringIO

from app.models.invoice import Invoice
from app.services.export.core import (
    INVOICE_HEADERS_SR,
    extract_invoice_row,
)

logger = logging.getLogger(__name__)

# UTF-8 BOM for Excel compatibility
UTF8_BOM = b"\xef\xbb\xbf"

# Delimiter mapping
DELIMITER_MAP = {
    "semicolon": ";",
    "comma": ",",
    "tab": "\t",
}


def generate_csv(
    invoices: list[Invoice],
    date_format: str = "DD.MM.YYYY",
    decimal_separator: str = ",",
    delimiter: str = "semicolon",
) -> BytesIO:
    """Generate CSV file with UTF-8 BOM.

    Args:
        invoices: List of Invoice instances.
        date_format: Date format string.
        decimal_separator: Decimal separator for numbers.
        delimiter: CSV delimiter ('semicolon', 'comma', 'tab').

    Returns:
        BytesIO buffer containing the CSV file with BOM.
    """
    delim_char = DELIMITER_MAP.get(delimiter, ";")
    string_buffer = StringIO()
    writer = csv.writer(string_buffer, delimiter=delim_char)

    # Header row
    writer.writerow(list(INVOICE_HEADERS_SR.values()))

    # Data rows
    for inv in invoices:
        row_data = extract_invoice_row(inv, date_format, decimal_separator)
        writer.writerow([row_data[key] for key in INVOICE_HEADERS_SR])

    # Encode to bytes with BOM
    buffer = BytesIO()
    buffer.write(UTF8_BOM)
    buffer.write(string_buffer.getvalue().encode("utf-8"))
    buffer.seek(0)
    return buffer
