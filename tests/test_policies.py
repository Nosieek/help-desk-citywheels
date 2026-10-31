import pytest
from unittest.mock import patch
from agent.tools.policies import search_policies, load_policy


def test_search_cancellation_policy():
    result = search_policies("cancellation refund")
    assert "cancellations.md" in result
    assert "Cancelling a booking" in result


def test_search_opening_hours():
    result = search_policies("opening hours saturday")
    assert "faq.md" in result
    assert "When are you open" in result
    assert "Saturday" in result


def test_search_bike_prices():
    result = search_policies("bike rental prices")
    assert "prices.md" in result
    assert "Bike rental" in result


def test_search_no_relevant_policy():
    result = search_policies("something completely unrelated xyz")
    assert "No relevant" in result


def test_search_empty_query():
    assert "No query provided" in search_policies("")
    assert "No query provided" in search_policies("   ")


def test_search_missing_policy_file():
    original_load = load_policy

    def mock_load(filename):
        if filename == "prices.md":
            return ""
        return original_load(filename)

    with patch("agent.tools.policies.load_policy", side_effect=mock_load):
        result = search_policies("cancellation refund")
    assert "cancellations.md" in result


def test_search_returns_best_match_first():
    result = search_policies("cancelling booking refund")
    first_section = result.split("---")[1] if "---" in result else result
    assert "cancellations" in first_section


@pytest.mark.parametrize("query", [
    "cancel booking refund",
    "cancelling booking refund",
    "cancellation booking refund",
    "cancel my reservation",
])
def test_search_cancellation_word_variants(query):
    result = search_policies(query)
    assert "cancellations.md" in result
    assert "Cancelling a booking" in result


# realistic phrasings that the old keyword-dictionary search got wrong
@pytest.mark.parametrize("query,expected_section", [
    ("how much does a city bike cost per day", "City bike"),
    ("do you accept credit cards", "How can I pay"),
    ("reschedule my rental", "Changing a booking"),
    ("storm refund", "Bad weather"),
    ("are you open on sunday", "When are you open"),
])
def test_search_tricky_phrasings(query, expected_section):
    assert expected_section in search_policies(query)
