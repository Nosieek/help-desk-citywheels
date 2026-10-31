import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "bookings.json"


class BookingDataUnavailable(Exception):
    """The bookings file is missing or corrupted."""


class BookingNotFound(Exception):
    """No booking exists with the given ID."""


def load_bookings() -> list:
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        raise BookingDataUnavailable(
            "Booking data is temporarily unavailable, please try again later"
        ) from e


def normalize_booking_id(booking_id: str) -> str:
    """Accept '1001', 'cw1001' or 'cw-1001' and normalize to 'CW-1001'."""
    cleaned = booking_id.strip().upper()
    if re.fullmatch(r"\d+", cleaned):
        return f"CW-{cleaned}"
    if re.fullmatch(r"CW\d+", cleaned):
        return f"CW-{cleaned[2:]}"
    return cleaned


def get_booking(booking_id: str) -> dict:
    """Find a booking by its ID; short forms like '1001' are accepted."""
    normalized = normalize_booking_id(booking_id)
    for booking in load_bookings():
        if booking["id"].upper() == normalized:
            return booking

    raise BookingNotFound(f"Booking {normalized} not found")
