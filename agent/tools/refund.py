from datetime import datetime, timezone
from agent.config import REFERENCE_NOW

CANCELLABLE_STATUS = "confirmed"
REQUIRED_FIELDS = {"id", "status", "start", "rental_price_eur", "deposit_eur", "paid_with"}


def calculate_refund(booking: dict, now: datetime = REFERENCE_NOW) -> dict:
    """
    Calculates how much customer gets back when cancelling a booking.

    Returns the refund amount, deposit refund and refund method.
    """
    booking_id = booking.get("id", "unknown")

    if "error" in booking:
        return {"error": booking["error"], "booking_id": booking_id}

    missing = REQUIRED_FIELDS - booking.keys()
    if missing:
        return {"error": f"Missing booking fields: {missing}", "booking_id": booking_id}

    status = booking.get("status")
    if status != CANCELLABLE_STATUS:
        return {
            "error": f"Booking cannot be cancelled (status: {status})",
            "booking_id": booking_id,
        }

    try:
        start = datetime.fromisoformat(booking["start"])
    except (ValueError, TypeError):
        return {"error": "Invalid start date format", "booking_id": booking_id}

    # bookings.json always includes timezone offset, but we normalise to UTC as a safety net
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    now_aware = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)

    try:
        hours_until_start = (start - now_aware).total_seconds() / 3600
    except TypeError:
        return {"error": "Timezone mismatch in date comparison", "booking_id": booking_id}

    try:
        rental_price = float(booking["rental_price_eur"])
        deposit = float(booking["deposit_eur"])
    except (TypeError, ValueError):
        return {"error": "Invalid price fields", "booking_id": booking_id}

    if rental_price < 0 or deposit < 0:
        return {"error": "Invalid negative price fields", "booking_id": booking_id}

    if hours_until_start >= 48:
        refund_rental = rental_price
    elif hours_until_start >= 24:
        refund_rental = rental_price * 0.5
    else:
        refund_rental = 0.0

    refund_method = "new_voucher" if booking["paid_with"] == "voucher" else "card"

    return {
        "booking_id": booking_id,
        "refund_rental_eur": round(refund_rental, 2),
        "refund_deposit_eur": round(deposit, 2),
        "refund_total_eur": round(refund_rental + deposit, 2),
        "refund_method": refund_method,
        "hours_until_start": round(hours_until_start, 2),
    }
