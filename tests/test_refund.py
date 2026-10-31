import pytest
from datetime import datetime, timezone
from agent.tools.refund import calculate_refund

NOW = datetime(2026, 6, 10, 7, 0, 0, tzinfo=timezone.utc)  # 09:00 Warsaw / 07:00 UTC


def make_booking(**overrides):
    base = {
        "id": "CW-TEST",
        "status": "confirmed",
        "start": "2026-06-13T10:00:00+02:00",  # 73h from NOW
        "end": "2026-06-15T10:00:00+02:00",
        "rental_price_eur": 40.0,
        "booking_fee_eur": 2.0,
        "deposit_eur": 50.0,
        "paid_with": "card",
    }
    base.update(overrides)
    return base


# Bussines rules

def test_refund_over_48h():
    result = calculate_refund(make_booking(), now=NOW)
    assert result["refund_rental_eur"] == 40.0
    assert result["refund_deposit_eur"] == 50.0
    assert result["refund_total_eur"] == 90.0


def test_refund_between_24h_and_48h():
    booking = make_booking(start="2026-06-11T18:00:00+02:00")  # 33h from NOW
    result = calculate_refund(booking, now=NOW)
    assert result["refund_rental_eur"] == 20.0
    assert result["refund_deposit_eur"] == 50.0
    assert result["refund_total_eur"] == 70.0


def test_refund_under_24h():
    booking = make_booking(start="2026-06-10T15:00:00+02:00")  # 6h from NOW
    result = calculate_refund(booking, now=NOW)
    assert result["refund_rental_eur"] == 0.0
    assert result["refund_deposit_eur"] == 50.0
    assert result["refund_total_eur"] == 50.0


# edge cases

def test_refund_exactly_48h():
    booking = make_booking(start="2026-06-12T09:00:00+02:00")  # exactly 48h
    result = calculate_refund(booking, now=NOW)
    assert result["refund_rental_eur"] == 40.0


def test_refund_exactly_24h():
    booking = make_booking(start="2026-06-11T09:00:00+02:00")  # exactly 24h
    result = calculate_refund(booking, now=NOW)
    assert result["refund_rental_eur"] == 20.0


# status

def test_refund_cancelled_status():
    booking = make_booking(status="cancelled")
    result = calculate_refund(booking, now=NOW)
    assert "error" in result


def test_refund_in_progress_status():
    booking = make_booking(status="in_progress")
    result = calculate_refund(booking, now=NOW)
    assert "error" in result


def test_refund_completed_status():
    booking = make_booking(status="completed")
    result = calculate_refund(booking, now=NOW)
    assert "error" in result


# refund method

def test_refund_method_card():
    result = calculate_refund(make_booking(paid_with="card"), now=NOW)
    assert result["refund_method"] == "card"


def test_refund_method_voucher():
    result = calculate_refund(make_booking(paid_with="voucher"), now=NOW)
    assert result["refund_method"] == "new_voucher"


# data validation

def test_refund_missing_field():
    booking = make_booking()
    del booking["rental_price_eur"]
    result = calculate_refund(booking, now=NOW)
    assert "error" in result


def test_refund_invalid_date():
    result = calculate_refund(make_booking(start="not-a-date"), now=NOW)
    assert "error" in result


def test_refund_date_without_timezone():
    result = calculate_refund(make_booking(start="2026-06-13T10:00:00"), now=NOW)
    assert "refund_total_eur" in result


def test_refund_invalid_price_type():
    result = calculate_refund(make_booking(rental_price_eur="free"), now=NOW)
    assert "error" in result


def test_refund_negative_price():
    result = calculate_refund(make_booking(rental_price_eur=-10.0), now=NOW)
    assert "error" in result


def test_refund_booking_fee_not_refunded():
    result = calculate_refund(make_booking(booking_fee_eur=2.0), now=NOW)
    assert result["refund_total_eur"] == result["refund_rental_eur"] + result["refund_deposit_eur"]
