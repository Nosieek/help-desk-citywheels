import json
from agent.loop import run_agent, MAX_ITERATIONS, FALLBACK_ANSWER


# Minimal fakes mimicking the anthropic SDK response objects
# No network, no API key: the fake client returns scripted responses

class FakeTextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class FakeToolUseBlock:
    type = "tool_use"

    def __init__(self, name, input, id="toolu_test_1"):
        self.name = name
        self.input = input
        self.id = id


class FakeResponse:
    def __init__(self, stop_reason, content):
        self.stop_reason = stop_reason
        self.content = content


class FakeMessages:
    def __init__(self, responses, calls):
        self._responses = responses
        self._calls = calls

    def create(self, **kwargs):
        # snapshot the messages list like the real SDK serializing a request,
        # so later appends by the loop don't change what we recorded
        self._calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return self._responses.pop(0)


class FakeClient:
    """Stands in for anthropic.Anthropic, returning scripted responses in order."""

    def __init__(self, responses):
        self.calls = []
        self.messages = FakeMessages(list(responses), self.calls)


def text_response(text):
    return FakeResponse("end_turn", [FakeTextBlock(text)])


def tool_response(name, input, id="toolu_test_1"):
    return FakeResponse("tool_use", [FakeToolUseBlock(name, input, id)])


def test_direct_answer_without_tools():
    client = FakeClient([text_response("We are open 08:00-20:00.")])

    result = run_agent("When are you open?", client=client)

    assert result.answer == "We are open 08:00-20:00."
    assert result.tool_calls == []
    assert len(client.calls) == 1
    assert client.calls[0]["temperature"] == 0  # eval needs deterministic runs


def test_tool_call_result_is_fed_back_to_model():
    client = FakeClient([
        tool_response("get_booking", {"booking_id": "CW-1001"}),
        text_response("Your booking CW-1001 is confirmed."),
    ])

    result = run_agent("What is the status of CW-1001?", client=client)

    assert result.answer == "Your booking CW-1001 is confirmed."
    assert len(client.calls) == 2

    # The second API call must contain the real tool result for CW-1001.
    messages = client.calls[1]["messages"]
    tool_result = messages[-1]["content"][0]
    assert tool_result["type"] == "tool_result"
    assert tool_result["tool_use_id"] == "toolu_test_1"
    booking = json.loads(tool_result["content"])
    assert booking["id"] == "CW-1001"
    assert booking["status"] == "confirmed"


def test_tool_calls_are_traced():
    client = FakeClient([
        tool_response("get_booking", {"booking_id": "CW-1001"}),
        text_response("Your booking CW-1001 is confirmed."),
    ])

    result = run_agent("What is the status of CW-1001?", client=client)

    assert len(result.tool_calls) == 1
    call = result.tool_calls[0]
    assert call["tool"] == "get_booking"
    assert call["input"] == {"booking_id": "CW-1001"}
    assert call["output"]["id"] == "CW-1001"


def test_calculate_refund_takes_only_a_booking_id():
    # The tool looks the booking up itself: CW-1001 starts 73h after the
    # reference date, so the full rental (40) plus deposit (50) comes back.
    client = FakeClient([
        tool_response("calculate_refund", {"booking_id": "CW-1001"}),
        text_response("You would get 90 EUR back."),
    ])

    result = run_agent("How much back if I cancel CW-1001?", client=client)

    output = result.tool_calls[0]["output"]
    assert output["refund_total_eur"] == 90.0


def test_calculate_refund_unknown_booking_returns_error():
    client = FakeClient([
        tool_response("calculate_refund", {"booking_id": "CW-9999"}),
        text_response("I could not find that booking."),
    ])

    result = run_agent("Refund for CW-9999?", client=client)

    assert "error" in result.tool_calls[0]["output"]


def test_unknown_tool_returns_error_instead_of_crashing():
    client = FakeClient([
        tool_response("delete_all_bookings", {}),
        text_response("Sorry, I cannot do that."),
    ])

    result = run_agent("Delete everything", client=client)

    assert result.answer == "Sorry, I cannot do that."
    tool_result = client.calls[1]["messages"][-1]["content"][0]
    assert "error" in json.loads(tool_result["content"])


def test_tool_exception_returns_error_result():
    # get_booking called without booking_id raises KeyError inside the tool.
    client = FakeClient([
        tool_response("get_booking", {}),
        text_response("Please provide your booking number."),
    ])

    result = run_agent("Check my booking", client=client)

    assert result.answer == "Please provide your booking number."
    tool_result = client.calls[1]["messages"][-1]["content"][0]
    assert "error" in json.loads(tool_result["content"])


def test_max_iterations_returns_fallback_message():
    client = FakeClient(
        [tool_response("search_policies", {"query": "prices"})] * MAX_ITERATIONS
    )

    result = run_agent("Tell me everything", client=client)

    assert len(client.calls) == MAX_ITERATIONS
    assert result.answer == FALLBACK_ANSWER


def test_unexpected_stop_reason_does_not_loop_forever():
    # e.g. stop_reason == "max_tokens": return the partial text, no re-send
    client = FakeClient([FakeResponse("max_tokens", [FakeTextBlock("Partial answer")])])

    result = run_agent("Long question", client=client)

    assert result.answer == "Partial answer"
    assert len(client.calls) == 1


def test_follow_up_question_sees_previous_turns():
    client = FakeClient([
        text_response("Booking CW-1002 is confirmed."),
        text_response("It is an e-bike."),
    ])

    first = run_agent("What is the status of CW-1002?", client=client)
    second = run_agent("And what bike type is it?", client=client, history=first.messages)

    assert second.answer == "It is an e-bike."
    # the second API call must carry the full conversation so far
    messages = client.calls[1]["messages"]
    assert messages[0] == {"role": "user", "content": "What is the status of CW-1002?"}
    assert messages[1]["role"] == "assistant"
    assert messages[2] == {"role": "user", "content": "And what bike type is it?"}


def test_history_is_not_mutated():
    client = FakeClient([text_response("First."), text_response("Second.")])

    first = run_agent("Question one", client=client)
    before = len(first.messages)
    run_agent("Question two", client=client, history=first.messages)

    assert len(first.messages) == before
