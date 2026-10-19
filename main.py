"""Interactive command-line entry point for the support resolution agent."""

from __future__ import annotations

import argparse
import os
import uuid

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from agent.graph import build_graph


def parse_args() -> argparse.Namespace:
    """Parse the CLI options."""
    parser = argparse.ArgumentParser(description="Chat with the e-commerce support agent.")
    parser.add_argument("--debug", action="store_true", help="Print tool calls, arguments, and results.")
    return parser.parse_args()


def main() -> int:
    """Load configuration and run a checkpointed interactive chat loop."""
    args = parse_args()
    load_dotenv()
    if not os.getenv("GROQ_API_KEY"):
        print("GROQ_API_KEY is missing. Copy .env.example to .env and add your Groq API key.")
        return 1

    try:
        agent = build_graph(debug=args.debug)
    except Exception as exc:
        print(f"The support agent could not start: {exc}")
        return 1

    thread_id = uuid.uuid4().hex
    print("Support agent ready. Type /new for a fresh conversation or exit to quit.")
    while True:
        try:
            customer_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return 0
        if customer_text.casefold() == "exit":
            print("Goodbye.")
            return 0
        if customer_text == "/new":
            thread_id = uuid.uuid4().hex
            print("Started a new conversation.")
            continue
        if not customer_text:
            continue

        try:
            response = agent.invoke(
                {"messages": [HumanMessage(content=customer_text)]},
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": 30,
                },
            )
        except Exception as exc:
            print(f"Agent error: {exc}. Please try again.")
            continue

        assistant_message = next(
            (message for message in reversed(response.get("messages", [])) if isinstance(message, AIMessage)),
            None,
        )
        print(f"Agent: {assistant_message.content if assistant_message else 'I could not prepare a response.'}")


if __name__ == "__main__":
    raise SystemExit(main())
