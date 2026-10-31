import os
import sys

import anthropic

from agent.loop import run_agent


def ask(question: str, history: list = None) -> tuple[str, list]:
    """Ask the agent one question; returns the answer and the updated history."""
    try:
        result = run_agent(question, history=history)
        return result.answer, result.messages
    except anthropic.APIError:
        message = "Sorry, the service is temporarily unavailable. Please try again in a moment."
        return message, history or []


def main():
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Missing ANTHROPIC_API_KEY. Copy .env.example to .env and add your key.")
        sys.exit(1)

    if len(sys.argv) > 1:
        answer, _ = ask(" ".join(sys.argv[1:]))
        print(answer)
        return

    print("CityWheels Help Desk. Type your question or 'exit' to quit.\n")
    history = []
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        if not question:
            continue
        answer, history = ask(question, history)
        print(f"Agent: {answer}\n")


if __name__ == "__main__":
    main()
