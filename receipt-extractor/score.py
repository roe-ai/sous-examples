"""Score the receipt extractor on test.csv, or on the rows Sous held out of receipts.csv.

    python score.py                         # the saved answers in test-answers.jsonl
    python score.py --live                  # call the model again
    python score.py --csv receipts.csv --split test --live

Exact match compares the four fields to the SROIE labels, character for character after stripping
the ends. A field also counts as acceptable when the only differences are capitalization and
punctuation, or when test-review.csv marks that field follows_receipt or spelling. The one field
marked real stays wrong.

While a model's server starts, Sous says so and this waits for it, rather than let the teacher
answer in its place.
"""

from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

import openai

from extract import FIELDS, parse, sous_client

HERE = Path(__file__).parent
ACCEPTABLE = {"follows_receipt", "spelling"}


def squash(value: str) -> str:
    """Letters and digits only, so spacing and punctuation do not count."""
    return re.sub(r"[^a-z0-9]", "", value.casefold())


def load_review(path: Path) -> dict[tuple[str, str], str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as rows:
        return {(row["id"], row["field"]): row["verdict"] for row in csv.DictReader(rows)}


def field_kind(receipt_id: str, field: str, gold: str, pred: str, review: dict[tuple[str, str], str],
               saved: str | None) -> str:
    """exact, punctuation, acceptable, or miss.

    A follows_receipt or spelling note counts only while the prediction is still the one that was reviewed.
    """
    if gold.strip() == pred.strip():
        return "exact"
    if squash(gold) == squash(pred):
        return "punctuation"
    verdict = review.get((receipt_id, field))
    reviewed = saved is None or saved.strip() == pred.strip()
    if verdict in ACCEPTABLE and reviewed:
        return "acceptable"
    return "miss"


def ask(client: openai.OpenAI, model: str, row: dict) -> tuple[dict | None, str, float]:
    """The model's four fields, who answered, and how long it took."""
    started = time.monotonic()
    while True:
        try:
            raw = client.chat.completions.with_raw_response.create(
                model=model, messages=[{"role": "user", "content": row["ocr"]}])
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
    except (json.JSONDecodeError, ValueError):
        answer = None
    return answer, answered_by, time.monotonic() - started


def saved_answers(path: Path) -> dict[str, dict]:
    answers = {}
    with path.open(encoding="utf-8") as rows:
        for line in rows:
            if line.strip():
                row = json.loads(line)
                answers[row["id"]] = row["pred"]
    return answers


def main() -> None:
    parser = argparse.ArgumentParser(description="Score the receipt extractor against SROIE labels.")
    parser.add_argument("--csv", default=str(HERE / "test.csv"), help="receipts with ocr and the four label columns")
    parser.add_argument("--split", choices=["test", "train", "all"], default="all",
                        help="with a split column, which rows to score (default all)")
    parser.add_argument("--answers", default=str(HERE / "test-answers.jsonl"), help="saved predictions, as JSON lines")
    parser.add_argument("--review", default=str(HERE / "test-review.csv"))
    parser.add_argument("--live", action="store_true", help="call the model instead of reading --answers")
    parser.add_argument("--model", default=os.environ.get("SOUS_MODEL", "798db1a3"))
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    with open(args.csv, newline="", encoding="utf-8") as rows:
        receipts = [row for row in csv.DictReader(rows) if args.split == "all" or row.get("split", "all") == args.split]
    if not receipts:
        sys.exit(f"No rows in {args.csv} for split {args.split}.")
    review = load_review(Path(args.review))
    saved = saved_answers(Path(args.answers)) if Path(args.answers).exists() else {}

    predictions: dict[str, dict | None] = {}
    answered_by: dict[str, str] = {}
    seconds: dict[str, float] = {}
    if args.live:
        if not os.environ.get("SOUS_API_KEY"):
            sys.exit("Set SOUS_API_KEY to call the model, or run without --live to score the saved answers.")
        client = sous_client(timeout=900, max_retries=2, default_headers={"x-sous-own-model": "1"})
        with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
            running = {pool.submit(ask, client, args.model, row): row["id"] for row in receipts}
            for done, future in enumerate(concurrent.futures.as_completed(running), 1):
                receipt_id = running[future]
                answer, who, took = future.result()
                predictions[receipt_id] = answer
                answered_by[receipt_id] = who
                seconds[receipt_id] = took
                if done % 10 == 0 or done == len(receipts):
                    print(f"  [{done}/{len(receipts)}]", flush=True)
    else:
        missing = [row["id"] for row in receipts if row["id"] not in saved]
        if missing:
            sys.exit(f"{len(missing)} receipts have no saved answer, starting with {missing[0]}. Use --live to call the model.")
        predictions = {row["id"]: saved[row["id"]] for row in receipts}

    exact = collections.Counter()
    ok = collections.Counter()
    all_exact = all_ok = unreadable = 0
    misses = []
    for row in receipts:
        pred = predictions[row["id"]]
        if not pred:
            unreadable += 1
            continue
        field_exact = []
        field_ok = []
        prior = saved.get(row["id"]) or {}
        for field in FIELDS:
            kind = field_kind(row["id"], field, row[field], pred.get(field, ""), review, prior.get(field))
            field_exact.append(kind == "exact")
            field_ok.append(kind != "miss")
            exact[field] += kind == "exact"
            ok[field] += kind != "miss"
            if kind == "miss":
                misses.append((row["id"], field, row[field], pred.get(field, "")))
        all_exact += all(field_exact)
        all_ok += all(field_ok)

    n = len(receipts)
    print(f"\n{n} receipts from {Path(args.csv).name}:")
    print(f"  All four fields, exact:        {all_exact / n:.0%}  ({all_exact})")
    print(f"  All four fields, acceptable:   {all_ok / n:.0%}  ({all_ok})")
    for field in FIELDS:
        print(f"  {field:<8} exact {exact[field] / n:.0%}   acceptable {ok[field] / n:.0%}")
    if seconds:
        print(f"  Seconds per receipt:           {statistics.median(seconds.values()):.1f} (median)")
        by = collections.Counter(answered_by.values())
        print(f"  Answered by:                   {', '.join(f'{name} {count}' for name, count in by.most_common())}")
    if unreadable:
        print(f"  Replies that were not JSON:    {unreadable}")
    for receipt_id, field, gold, pred in misses:
        print(f"  {receipt_id} {field}")
        print(f"    label {gold}")
        print(f"    model {pred}")


if __name__ == "__main__":
    main()
