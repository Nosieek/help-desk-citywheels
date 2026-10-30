import json
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "bookings.json"


def load_bookings() -> list[dict]:
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def get_booking(booking_id: str) -> dict:
    """
    Finds a booking by its ID

    Returns booking details if found, otherwise an error message
    """
    try:
        bookings = load_bookings()
    except FileNotFoundError:
        return {"error": "Bookings data unavailable", "booking_id": booking_id}

    for booking in bookings:
        if booking["id"].upper() == booking_id.upper():
            return booking

    return {"error": "Booking not found", "booking_id": booking_id}
