import json
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


def get_booking(booking_id: str) -> dict:
    """Find a booking by its ID (case-insensitive)."""
    for booking in load_bookings():
        if booking["id"].upper() == booking_id.upper():
            return booking

    raise BookingNotFound(f"Booking {booking_id} not found")
