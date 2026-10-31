import json
from dataclasses import dataclass, field

import anthropic
from dotenv import load_dotenv

from agent.config import MODEL, MAX_ITERATIONS, MAX_TOKENS
from agent.prompts import SYSTEM_PROMPT
from agent.tools.bookings import get_booking
from agent.tools.refund import calculate_refund
from agent.tools.policies import search_policies

load_dotenv()

FALLBACK_ANSWER = "I was unable to process your request. Please contact our support team."

TOOLS = [
    {
        "name": "get_booking",
        "description": "Retrieve a booking by its ID from the CityWheels database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "booking_id": {
                    "type": "string",
                    "description": "The booking ID, e.g. CW-1001.",
                },
            },
            "required": ["booking_id"],
        },
    },
    {
        "name": "search_policies",
        "description": (
            "Search CityWheels policy documents for information about prices, "
            "cancellations, opening hours, age limits and other rules."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Short English keywords, e.g. 'cancellation refund'.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculate_refund",
        "description": (
            "Calculate the refund a customer would get if the booking were "
            "cancelled now. Does not cancel the booking."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "booking_id": {
                    "type": "string",
                    "description": "The booking ID, e.g. CW-1001.",
                },
            },
            "required": ["booking_id"],
        },
    },
]

TOOL_FUNCTIONS = {
    "get_booking": lambda args: get_booking(args["booking_id"]),
    "search_policies": lambda args: search_policies(args["query"]),
    # the tool looks the booking up itself, so booking data never
    # round-trips through the model and cannot be altered by it
    "calculate_refund": lambda args: calculate_refund(get_booking(args["booking_id"])),
}


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[dict] = field(default_factory=list)
    # full conversation after this turn; pass as `history` to the next
    # run_agent call to support follow-up questions
    messages: list = field(default_factory=list)


def _execute_tools(content: list, tool_calls: list[dict]) -> list:
    """Execute all tool calls in a response and return tool_result blocks."""
    results = []
    for block in content:
        if block.type != "tool_use":
            continue
        tool_fn = TOOL_FUNCTIONS.get(block.name)
        if tool_fn is None:
            output = {"error": f"Unknown tool: {block.name}"}
        else:
            try:
                output = tool_fn(block.input)
            except Exception as e:
                output = {"error": str(e)}

        tool_calls.append({"tool": block.name, "input": block.input, "output": output})
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(output),
        })
    return results


def _extract_text(content: list) -> str:
    """Extract text from a response content list."""
    return " ".join(block.text for block in content if block.type == "text").strip()


def run_agent(
    user_message: str,
    client: anthropic.Anthropic = None,
    history: list = None,
) -> AgentResult:
    """
    Run the agent loop for a single user message.

    Sends the message to Claude, executes tool calls until the model stops
    asking for tools, and returns the final answer plus a trace of every
    tool call made (used by the evaluation). Pass the `messages` of a
    previous result as `history` to ask a follow-up question.
    """
    if client is None:
        client = anthropic.Anthropic()

    messages = list(history) if history else []
    messages.append({"role": "user", "content": user_message})
    tool_calls: list[dict] = []

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            temperature=0,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = _execute_tools(response.content, tool_calls)
            messages.append({"role": "user", "content": tool_results})
            continue

        # end_turn, or an unexpected stop reason such as max_tokens:
        # return whatever text we got instead of re-sending the same request
        text = _extract_text(response.content)
        messages.append({"role": "assistant", "content": response.content})
        return AgentResult(
            answer=text or FALLBACK_ANSWER, tool_calls=tool_calls, messages=messages
        )

    messages.append({"role": "assistant", "content": FALLBACK_ANSWER})
    return AgentResult(
        answer=FALLBACK_ANSWER, tool_calls=tool_calls, messages=messages
    )
