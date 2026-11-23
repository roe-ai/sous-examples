"""Score a Sous model on the 84 tickets Sous held out when it trained the sandbox's router: how often it gives the
route and the urgency gpt-6.1-terra gave them (tickets-labeled.csv, split "test").

    python score.py                 # the model that answers SOUS_MODEL's calls
    python score.py --model 05856571:c1
    python score.py --split all     # every ticket, the ones it trained on too

A model you trained on these tickets held out its own fifth, so its page has the fairest numbers; this checks any
model on the same tickets. While a model's server starts, Sous says so and this waits for it, rather than let
gpt-6.1-terra answer in its place.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import os
import statistics
import sys
import time
from pathlib import Path

import openai

from route import parse, sous_client, ticket_text

HERE = Path(__file__).parent


def ask(client: openai.OpenAI, model: str, row: dict) -> tuple[dict | None, str, float]:
    """The model's answer to one ticket, who answered it, and how long it took."""
    started = time.monotonic()
    while True:
        try:
            raw = client.chat.completions.with_raw_response.create(
                model=model, messages=[{"role": "user", "content": ticket_text(row["subject"], row["body"])}])
            break
        except openai.APIStatusError as exc:
            if exc.status_code != 503:
                raise
            wait = min(max(float(exc.response.headers.get("retry-after") or 30), 5), 60)
            print(f"  The model's server is starting; trying again in {wait:.0f}s.", flush=True)
            time.sleep(wait)
    answered_by = raw.headers.get("x-sous-answered-by") or "?"
    try:
        answer = parse(raw.parse().choices[0].message.content or "")
    except ValueError:
        answer = None
    return answer, answered_by, time.monotonic() - started


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a Sous model on the router's held-out tickets.")
    parser.add_argument("--model", default=os.environ.get("SOUS_MODEL"),
                        help="your Sous model's id, or one of its students as <id>:c2 (default SOUS_MODEL)")
    parser.add_argument("--split", choices=["test", "train", "all"], default="test")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not args.model:
        sys.exit("Say which Sous model to score: set SOUS_MODEL or pass --model.")

    with open(HERE / "tickets-labeled.csv", newline="") as rows:
        tickets = [r for r in csv.DictReader(rows) if args.split == "all" or r["split"] == args.split]
    # x-sous-own-model: while the model's server starts, Sous answers 503 instead of passing the call to the teacher.
    client = sous_client(timeout=900, max_retries=2, default_headers={"x-sous-own-model": "1"})

    results: dict[str, tuple[dict | None, str, float]] = {}
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        running = {pool.submit(ask, client, args.model, row): row["id"] for row in tickets}
        for done, future in enumerate(concurrent.futures.as_completed(running), 1):
            results[running[future]] = future.result()
            if done % 10 == 0 or done == len(tickets):
                print(f"  [{done}/{len(tickets)}]", flush=True)

    route = urgent = both = unreadable = 0
    misroutes: collections.Counter = collections.Counter()
    for row in tickets:
        answer = results[row["id"]][0]
        if answer is None:
            unreadable += 1
            continue
        same_route, same_urgent = answer["route"] == row["route"], answer["urgent"] == (row["urgent"] == "true")
        route += same_route
        urgent += same_urgent
        both += same_route and same_urgent
        if not same_route:
            misroutes[(row["route"], answer["route"])] += 1
    n = len(tickets)
    by = collections.Counter(results[row["id"]][1] for row in tickets)
    print(f"\n{args.model} on {n} tickets ({args.split}), against gpt-6.1-terra's labels:")
    print(f"  Same route:          {route / n:.1%}")
    print(f"  Same urgency:        {urgent / n:.1%}")
    print(f"  Both the same:       {both / n:.1%}")
    print(f"  Seconds per ticket:  {statistics.median(r[2] for r in results.values()):.1f} (median)")
    print(f"  Answered by:         {', '.join(f'{k} {v}' for k, v in by.most_common())}")
    if unreadable:
        print(f"  Replies that weren't a route: {unreadable}")
    for (expected, got), count in misroutes.most_common(5):
        print(f"  {count} {expected} ticket{'s' if count > 1 else ''} routed to {got}")


if __name__ == "__main__":
    main()
