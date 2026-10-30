import pytest
from unittest.mock import patch
from agent.tools.bookings import get_booking

SAMPLE_BOOKINGS = [
    {"id": "CW-1001", "status": "confirmed", "bike_type": "city", "bikes": 1,
     "start": "2026-06-13T10:00:00+02:00", "end": "2026-06-15T10:00:00+02:00",
     "add_ons": [], "rental_price_eur": 40.0, "booking_fee_eur": 2.0,
     "deposit_eur": 50.0, "paid_with": "card"},
    {"id": "CW-1005", "status": "cancelled", "bike_type": "e-bike", "bikes": 1,
     "start": "2026-06-14T10:00:00+02:00", "end": "2026-06-14T14:00:00+02:00",
     "add_ons": [], "rental_price_eur": 36.0, "booking_fee_eur": 2.0,
     "deposit_eur": 150.0, "paid_with": "card"},
    {"id": "CW-1008", "status": "in_progress", "bike_type": "city", "bikes": 1,
     "start": "2026-06-10T08:00:00+02:00", "end": "2026-06-10T12:00:00+02:00",
     "add_ons": [], "rental_price_eur": 16.0, "booking_fee_eur": 2.0,
     "deposit_eur": 50.0, "paid_with": "card"},
    {"id": "CW-1006", "status": "completed", "bike_type": "kids", "bikes": 2,
     "start": "2026-06-07T10:00:00+02:00", "end": "2026-06-07T13:00:00+02:00",
     "add_ons": [], "rental_price_eur": 12.0, "booking_fee_eur": 0.0,
     "deposit_eur": 60.0, "paid_with": "card"},
]


@pytest.fixture
def mock_bookings():
    with patch("agent.tools.bookings.load_bookings", return_value=SAMPLE_BOOKINGS):
        yield

def test_get_booking_confirmed(mock_bookings):
    result = get_booking("CW-1001")
    assert result["id"] == "CW-1001"
    assert result["status"] == "confirmed"


def test_get_booking_cancelled(mock_bookings):
    result = get_booking("CW-1005")
    assert result["id"] == "CW-1005"
    assert result["status"] == "cancelled"


def test_get_booking_in_progress(mock_bookings):
    result = get_booking("CW-1008")
    assert result["id"] == "CW-1008"
    assert result["status"] == "in_progress"


def test_get_booking_completed(mock_bookings):
    result = get_booking("CW-1006")
    assert result["id"] == "CW-1006"
    assert result["status"] == "completed"


def test_get_booking_not_found(mock_bookings):
    result = get_booking("CW-9999")
    assert "error" in result
    assert result["booking_id"] == "CW-9999"


def test_get_booking_case_insensitive(mock_bookings):
    result = get_booking("cw-1001")
    assert result["id"] == "CW-1001"


def test_get_booking_empty_id(mock_bookings):
    result = get_booking("")
    assert "error" in result


def test_get_booking_file_not_found():
    with patch("agent.tools.bookings.load_bookings", side_effect=FileNotFoundError):
        result = get_booking("CW-1001")
    assert "error" in result


def test_get_booking_corrupted_json():
    with patch("agent.tools.bookings.load_bookings", return_value=[]):
        result = get_booking("CW-1001")
    assert "error" in result
