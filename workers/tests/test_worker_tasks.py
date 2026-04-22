"""Tests for worker database integration (save result / update status)."""

import json
from unittest.mock import MagicMock, patch

import pytest


def _make_extraction_result():
    """Create a sample serialized ExtractionResult dict."""
    return {
        "status": "success",
        "invoice": {
            "invoice_number": "F-2025/001",
            "invoice_date": "2025-03-15",
            "due_date": "2025-04-15",
            "seller": {"pib": "103867028", "name": "Test Seller d.o.o."},
            "buyer": {"pib": "205149832", "name": "Test Buyer d.o.o."},
            "subtotal": "100000.00",
            "tax_rate": "20",
            "tax_amount": "20000.00",
            "total_amount": "120000.00",
            "currency": "RSD",
            "line_items": [
                {"description": "Usluga 1", "quantity": "1", "total": "100000.00"}
            ],
            "raw_text": "Full OCR text here...",
            "raw_structured": {},
        },
        "overall_confidence": 0.92,
        "field_confidences": [
            {"field_name": "seller_pib", "value": "103867028", "confidence": 0.95}
        ],
        "warnings": [],
        "is_blocked": False,
        "processing_time_ms": 1234,
        "ocr_engine": "dots",
        "model_version": "0.1.0",
        "page_count": 1,
        "document_type": "invoice",
    }


INVOICE_ID = "550e8400-e29b-41d4-a716-446655440000"


class TestSaveExtractionResult:
    """Tests for _save_extraction_result()."""

    @patch("ocr_worker.database.get_session")
    def test_updates_invoice_with_correct_params(self, mock_get_session):
        from ocr_worker.tasks import _save_extraction_result

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        result = _make_extraction_result()
        _save_extraction_result(INVOICE_ID, result)

        # _save_extraction_result runs several execute calls — the UPDATE
        # invoices statement plus follow-up line-item persistence. Target
        # the first call (the one we're asserting on).
        assert mock_session.execute.call_args_list, "execute was never called"
        params = mock_session.execute.call_args_list[0][0][1]

        assert params["invoice_id"] == INVOICE_ID
        assert params["invoice_number"] == "F-2025/001"
        assert params["invoice_date"] == "2025-03-15"
        assert params["due_date"] == "2025-04-15"
        assert params["subtotal"] == "100000.00"
        assert params["tax_rate"] == "20"
        assert params["tax_amount"] == "20000.00"
        assert params["total_amount"] == "120000.00"
        assert params["currency"] == "RSD"
        assert params["confidence_score"] == 0.92
        assert params["ocr_engine"] == "dots"
        assert params["processing_time_ms"] == 1234
        assert params["raw_ocr_text"] == "Full OCR text here..."

        # JSON-encoded fields
        seller = json.loads(params["seller"])
        assert seller["pib"] == "103867028"
        buyer = json.loads(params["buyer"])
        assert buyer["pib"] == "205149832"
        line_items = json.loads(params["line_items"])
        assert len(line_items) == 1

    @patch("ocr_worker.database.get_session")
    def test_commits_on_success(self, mock_get_session):
        from ocr_worker.tasks import _save_extraction_result

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        _save_extraction_result(INVOICE_ID, _make_extraction_result())

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

    @patch("ocr_worker.database.get_session")
    def test_rolls_back_on_error(self, mock_get_session):
        from ocr_worker.tasks import _save_extraction_result

        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("DB down")
        mock_get_session.return_value = mock_session

        with pytest.raises(RuntimeError, match="DB down"):
            _save_extraction_result(INVOICE_ID, _make_extraction_result())

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()

    @patch("ocr_worker.database.get_session")
    def test_always_closes_session(self, mock_get_session):
        from ocr_worker.tasks import _save_extraction_result

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        _save_extraction_result(INVOICE_ID, _make_extraction_result())
        mock_session.close.assert_called_once()

    @patch("ocr_worker.database.get_session")
    def test_closes_session_on_error(self, mock_get_session):
        from ocr_worker.tasks import _save_extraction_result

        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("DB down")
        mock_get_session.return_value = mock_session

        with pytest.raises(RuntimeError):
            _save_extraction_result(INVOICE_ID, _make_extraction_result())

        mock_session.close.assert_called_once()

    @patch("ocr_worker.database.get_session")
    def test_handles_missing_optional_fields(self, mock_get_session):
        from ocr_worker.tasks import _save_extraction_result

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # Minimal result with no optional fields
        result = {
            "status": "partial",
            "invoice": {
                "invoice_number": None,
                "raw_text": "",
            },
            "overall_confidence": 0.3,
            "field_confidences": [],
            "warnings": [],
            "ocr_engine": "easyocr",
        }

        _save_extraction_result(INVOICE_ID, result)

        params = mock_session.execute.call_args_list[0][0][1]
        assert params["invoice_number"] is None
        assert params["seller"] is None
        assert params["buyer"] is None
        assert params["line_items"] is None

    @staticmethod
    def _update_params(mock_session: MagicMock) -> dict:
        """Return the params dict passed to the first session.execute call.

        The worker makes several execute calls downstream (line-item
        persistence), so the default call_args (last call) is the wrong one.
        The UPDATE invoices ... statement is always the first execute.
        """
        return mock_session.execute.call_args_list[0][0][1]

    @patch("ocr_worker.database.get_session")
    def test_due_date_defaults_to_invoice_date_when_missing(self, mock_get_session):
        """When OCR doesn't extract a due_date, default it to invoice_date.

        Serbian hospitality invoices without explicit payment terms are almost
        always POS / cash receipts due the same day. Auto-fill keeps the
        past-due rule (due_date < today) meaningful across the dataset without
        requiring every user to manually set the field.
        """
        from ocr_worker.tasks import _save_extraction_result

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        result = _make_extraction_result()
        result["invoice"]["due_date"] = None  # OCR missed it

        _save_extraction_result(INVOICE_ID, result)

        params = self._update_params(mock_session)
        assert params["invoice_date"] == "2025-03-15"
        assert params["due_date"] == "2025-03-15"

    @patch("ocr_worker.database.get_session")
    def test_due_date_not_overwritten_when_present(self, mock_get_session):
        """A due_date extracted by OCR is preserved, not replaced by invoice_date."""
        from ocr_worker.tasks import _save_extraction_result

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        result = _make_extraction_result()
        # Standard result has due_date=2025-04-15, invoice_date=2025-03-15
        _save_extraction_result(INVOICE_ID, result)

        params = self._update_params(mock_session)
        assert params["due_date"] == "2025-04-15"

    @patch("ocr_worker.database.get_session")
    def test_due_date_stays_null_when_invoice_date_also_missing(self, mock_get_session):
        """If invoice_date is also missing, we have nothing to default to — leave null."""
        from ocr_worker.tasks import _save_extraction_result

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        result = _make_extraction_result()
        result["invoice"]["invoice_date"] = None
        result["invoice"]["due_date"] = None

        _save_extraction_result(INVOICE_ID, result)

        params = self._update_params(mock_session)
        assert params["invoice_date"] is None
        assert params["due_date"] is None


class TestUpdateInvoiceStatus:
    """Tests for _update_invoice_status()."""

    @patch("ocr_worker.database.get_session")
    def test_updates_status(self, mock_get_session):
        from ocr_worker.tasks import _update_invoice_status

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        _update_invoice_status(INVOICE_ID, "review")

        mock_session.execute.assert_called_once()
        params = mock_session.execute.call_args[0][1]
        assert params["invoice_id"] == INVOICE_ID
        assert params["status"] == "review"
        assert "warnings" not in params

    @patch("ocr_worker.database.get_session")
    def test_updates_status_with_error_message(self, mock_get_session):
        from ocr_worker.tasks import _update_invoice_status

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        _update_invoice_status(INVOICE_ID, "error", "OCR timeout")

        params = mock_session.execute.call_args[0][1]
        assert params["status"] == "error"
        warnings = json.loads(params["warnings"])
        assert len(warnings) == 1
        assert warnings[0]["message"] == "OCR timeout"
        assert warnings[0]["severity"] == "error"

    @patch("ocr_worker.database.get_session")
    def test_commits_on_success(self, mock_get_session):
        from ocr_worker.tasks import _update_invoice_status

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        _update_invoice_status(INVOICE_ID, "review")

        mock_session.commit.assert_called_once()

    @patch("ocr_worker.database.get_session")
    def test_rolls_back_on_error(self, mock_get_session):
        from ocr_worker.tasks import _update_invoice_status

        mock_session = MagicMock()
        mock_session.execute.side_effect = RuntimeError("DB down")
        mock_get_session.return_value = mock_session

        with pytest.raises(RuntimeError):
            _update_invoice_status(INVOICE_ID, "error")

        mock_session.rollback.assert_called_once()

    @patch("ocr_worker.database.get_session")
    def test_always_closes_session(self, mock_get_session):
        from ocr_worker.tasks import _update_invoice_status

        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        _update_invoice_status(INVOICE_ID, "review")
        mock_session.close.assert_called_once()
