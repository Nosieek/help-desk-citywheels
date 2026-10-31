import argparse
import os
import sys

import anthropic

from agent.loop import run_agent


def ask(question: str, history: list = None) -> tuple:
    """Ask the agent one question; returns the answer and the updated history."""
    try:
        result = run_agent(question, history=history)
        return result.answer, result.messages
    except anthropic.APIError:
        message = "Sorry, the service is temporarily unavailable. Please try again in a moment."
        return message, history or []


def interactive():
    print("CityWheels Help Desk. Type your question or 'exit' to quit.\n")
    history = []
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            return
        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            return
        if not question:
            continue
        answer, history = ask(question, history)
        print(f"Agent: {answer}\n")


def main():
    parser = argparse.ArgumentParser(
        prog="citywheels",
        description="Help desk agent for the CityWheels bike rental shop.",
        epilog="Run without arguments for interactive mode with conversation memory.",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="a single question to ask, e.g. citywheels \"How much is an e-bike per day?\"",
    )
    args = parser.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Missing ANTHROPIC_API_KEY. Copy .env.example to .env and add your key.")
        sys.exit(1)

    if args.question:
        answer, _ = ask(" ".join(args.question))
        print(answer)
    else:
        interactive()


if __name__ == "__main__":
    main()
