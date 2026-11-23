"""Run the redactor on the sample documents and chats the way your app would, with its calls going to Sous. Sous
passes each one to gpt-6.1-terra, the model's teacher, and keeps the call and its answer to train a smaller model on.

    export SOUS_API_KEY=hk_... SOUS_MODEL=<your Sous model's id>
    python collect.py

What each call found goes to outputs/collected/. Once you switch to the model Sous trains, the same calls go to it.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path

from openai import OpenAI

from pii import find_pii

HERE = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser(description="Redact the samples with gpt-6.1-terra while Sous learns.")
    parser.add_argument("--workers", type=int, default=8, help="calls at once")
    parser.add_argument("--limit", type=int, help="only the first N documents and the first N chats")
    args = parser.parse_args()

    model = os.environ.get("SOUS_MODEL")
    if not (model and os.environ.get("SOUS_API_KEY")):
        sys.exit("Set SOUS_API_KEY to a Sous API key and SOUS_MODEL to your Sous model's id.")
    base = (os.environ.get("SOUS_BASE_URL") or "https://api.sousml.com").rstrip("/").removesuffix("/v1")
    client = OpenAI(api_key=os.environ["SOUS_API_KEY"], base_url=f"{base}/v1", max_retries=4, timeout=600)
    documents = sorted(p for p in (HERE / "samples" / "documents").glob("*.jpg")
                       if not p.stem.endswith((".redacted", ".review")))[:args.limit]  # not redact.py's copies
    with open(HERE / "samples" / "conversations.jsonl") as rows:
        chats = [json.loads(row) for row in rows][:args.limit]
    jobs = [(path.stem, {"image": path}) for path in documents] + [(chat["id"], {"text": chat["text"]})
                                                                   for chat in chats]
    out = HERE / "outputs" / "collected"
    out.mkdir(parents=True, exist_ok=True)

    def redact(name: str, given: dict) -> tuple[int, float]:
        started = time.monotonic()
        found = find_pii(client, model=model, **given)
        (out / f"{name}.json").write_text(json.dumps(found, indent=1, ensure_ascii=False))
        return len(found), time.monotonic() - started

    failed = 0
    with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
        running = {pool.submit(redact, name, given): name for name, given in jobs}
        for done, future in enumerate(concurrent.futures.as_completed(running), 1):
            try:
                count, seconds = future.result()
                print(f"[{done}/{len(jobs)}] {running[future]}: {count} found in {seconds:.0f}s", flush=True)
            except Exception as exc:  # noqa: BLE001 - one failed call shouldn't stop the rest
                failed += 1
                print(f"[{done}/{len(jobs)}] {running[future]} failed: {exc}", file=sys.stderr, flush=True)

    print(f"Done: {len(jobs) - failed} calls for Sous model {model}. With Train on its own on, Sous starts training "
          "a few minutes after the last call; Train now on the model's page starts sooner.")


if __name__ == "__main__":
    main()
