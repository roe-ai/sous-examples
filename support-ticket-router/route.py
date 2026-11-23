"""Route a support ticket with your Sous model: which queue it goes to (billing, bug, feature_request, account or
other) and whether it's urgent, from one call.

    export SOUS_API_KEY=hk_... SOUS_MODEL=<your model's id>
    python route.py "Charged twice" "I was billed $49 twice on Monday. Can you refund one?"
    python route.py --csv tickets.csv --limit 5

Sous gives each call the instructions the model was trained with, so a call sends only the ticket, written the way
the model saw tickets in training: "subject: ..." and "body: ..." on their own lines.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from typing import Any

from openai import OpenAI

DEFAULT_BASE_URL = "https://api.sousml.com"
ROUTES = ("billing", "bug", "feature_request", "account", "other")


def sous_client(**options: Any) -> OpenAI:
    """An OpenAI client for the Sous API, from SOUS_API_KEY and SOUS_BASE_URL."""
    if not os.environ.get("SOUS_API_KEY"):
        sys.exit("Set SOUS_API_KEY to a Sous API key. Make one in Sous, under API keys.")
    base = (os.environ.get("SOUS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/").removesuffix("/v1")
    return OpenAI(api_key=os.environ["SOUS_API_KEY"], base_url=f"{base}/v1", **{"max_retries": 4, **options})


def ticket_text(subject: str, body: str) -> str:
    return f"subject: {subject}\nbody: {body}"


def parse(reply: str) -> dict:
    """The model's answer, {"route", "urgent"}, from its reply."""
    answer = json.loads(reply[reply.find("{"):reply.rfind("}") + 1])
    if answer.get("route") not in ROUTES:
        raise ValueError(f"Not a route: {answer.get('route')!r}")
    return {"route": answer["route"], "urgent": answer.get("urgent") is True}


def route_ticket(client: OpenAI, model: str, subject: str, body: str) -> dict:
    """{"route": "billing", "urgent": False}, for one ticket."""
    response = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": ticket_text(subject, body)}])
    return parse(response.choices[0].message.content or "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Route support tickets with your Sous model.")
    parser.add_argument("subject", nargs="?", help="the ticket's subject")
    parser.add_argument("body", nargs="?", default="", help="the ticket's body")
    parser.add_argument("--csv", help="route the tickets in a CSV with subject and body columns instead")
    parser.add_argument("--limit", type=int, default=10, help="with --csv, how many tickets (default 10)")
    parser.add_argument("--model", default=os.environ.get("SOUS_MODEL"),
                        help="your Sous model's id, or one of its students as <id>:c2 (default SOUS_MODEL)")
    args = parser.parse_args()
    if not args.model:
        sys.exit("Say which Sous model to call: set SOUS_MODEL or pass --model.")
    if not args.subject and not args.csv:
        parser.error("give a subject and a body, or --csv")

    client = sous_client(timeout=600)
    if not args.csv:
        print(json.dumps(route_ticket(client, args.model, args.subject, args.body)))
        return
    with open(args.csv, newline="") as rows:
        for row in list(csv.DictReader(rows))[:args.limit]:
            answer = route_ticket(client, args.model, row["subject"], row["body"])
            flag = " URGENT" if answer["urgent"] else ""
            print(f"{row.get('id', ''):>8}  {answer['route']:<15}{flag:<8} {row['subject']}")


if __name__ == "__main__":
    main()
