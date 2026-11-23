"""Score the redactor on the samples Sous never saw (samples/test): gpt-6.1-terra, the model Sous trained, or both.

    python score.py                              # both, with the model that answers SOUS_MODEL's calls
    python score.py --sous-model "$SOUS_MODEL:c2"   # a model Sous trained, before you switch to it
    python score.py --only sous                  # without an OpenAI key: just the model Sous trained
    python score.py --only teacher               # just gpt-6.1-terra, with OPENAI_API_KEY

Chats are scored against the PII make_conversations.py wrote into them. Documents have no answer key, so the trained
model's boxes are compared with gpt-6.1-terra's, and outputs/score/compare/ shows the two side by side. Answers are
saved in outputs/score/, so a rerun only makes the calls it hasn't made yet (--fresh makes them all again).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import statistics
import sys
import time
from pathlib import Path

import openai
from openai import OpenAI

from pii import MODEL, find_pii, hidden, redact_image

HERE = Path(__file__).parent
OUT = HERE / "outputs" / "score"
DEFAULT_BASE_URL = "https://api.sousml.com"


def sous_client() -> tuple[OpenAI, str]:
    """A client for the Sous OpenAI-compatible API. It says the caller has a model of its own, so while the Sous
    model's server starts, Sous says so (503, Retry-After) rather than answer with gpt-6.1-terra in its place."""
    if not os.environ.get("SOUS_API_KEY"):
        sys.exit("Set SOUS_API_KEY to a Sous API key, or pass --only teacher.")
    base = (os.environ.get("SOUS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/").removesuffix("/v1")
    client = OpenAI(api_key=os.environ["SOUS_API_KEY"], base_url=f"{base}/v1", max_retries=0, timeout=900,
                    default_headers={"x-sous-own-model": "1"})
    return client, base


def check_trained(client: OpenAI, model: str) -> None:
    """Stops with what to do when no model Sous trained answers `model` yet."""
    if ":" in model:
        return
    try:
        card = client.models.retrieve(model)
    except openai.APIStatusError as exc:
        sys.exit(f"Sous has no model {model} for this API key ({exc.status_code}).")
    if getattr(card, "answered_by", None) != "student":
        sys.exit(f"No model Sous trained answers {model}'s calls yet. Switch to one on the model's page, or score a "
                 f"candidate before you do: --sous-model {model}:c1")


def patiently(call):
    """call(), waiting out a Sous model's server while it starts."""
    while True:
        try:
            return call()
        except openai.APIStatusError as exc:
            if exc.status_code != 503:
                raise
            wait = float(exc.response.headers.get("retry-after") or 30)
            print(f"  The model's server is starting; trying again in {min(wait, 60):.0f}s.", flush=True)
            time.sleep(min(max(wait, 5), 60))


def answers(who: str, client: OpenAI, model: str, jobs: list[tuple[str, dict]], fresh: bool, workers: int) -> dict:
    """What `model` found in each sample, from outputs/score/<who>/ when it's there."""
    folder = OUT / who.replace(":", "-")
    folder.mkdir(parents=True, exist_ok=True)

    def run(name: str, given: dict) -> dict:
        path = folder / f"{name}.json"
        if path.exists() and not fresh:
            return json.loads(path.read_text())
        started = time.monotonic()
        try:
            found = patiently(lambda: find_pii(client, model=model, **given))
        except (ValueError, openai.APIError) as exc:  # scored as finding nothing, and tried again next run
            print(f"  {who} {name} failed: {exc}", flush=True)
            return {"found": [], "seconds": round(time.monotonic() - started, 2), "failed": True}
        result = {"found": found, "seconds": round(time.monotonic() - started, 2)}
        path.write_text(json.dumps(result, indent=1, ensure_ascii=False))
        return result

    out = {}
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        running = {pool.submit(run, name, given): name for name, given in jobs}
        for done, future in enumerate(concurrent.futures.as_completed(running), 1):
            out[running[future]] = future.result()
            print(f"  {who} [{done}/{len(jobs)}] {running[future]}", flush=True)
    return out


def covered(size: int, spans: list[tuple[int, int]]) -> bytearray:
    mask = bytearray(size)
    for start, end in spans:
        mask[start:end] = b"\x01" * (end - start)
    return mask


def inside(mask: bytearray, start: int, end: int) -> float:
    return sum(mask[start:end]) / max(1, end - start)


def chat_scores(chats: list[dict], got: dict) -> dict:
    """Scored on what redact_text hides. PII hidden: true items at least 90% hidden. Hidden that is PII: hidden spans
    at least half inside true PII. PII characters hidden: of all the true PII's characters."""
    found = items = right = given = chars = total = 0
    for chat in chats:
        text, pii = chat["text"], [(item["start"], item["end"]) for item in chat["pii"]]
        marks = [(start, end) for start, end, _ in hidden(text, got[chat["id"]]["found"])]
        truth, ours = covered(len(text), pii), covered(len(text), marks)
        found += sum(inside(ours, *span) >= 0.9 for span in pii)
        items += len(pii)
        right += sum(inside(truth, *span) >= 0.5 for span in marks)
        given += len(marks)
        chars += sum(a & b for a, b in zip(truth, ours))
        total += sum(truth)
    return {"PII hidden": found / max(1, items), "Hidden that is PII": right / max(1, given),
            "PII characters hidden": chars / max(1, total)}


def overlap(a: list[int], b: list[int]) -> float:
    width = min(a[2], b[2]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[1], b[1])
    if width <= 0 or height <= 0:
        return 0.0
    area = lambda box: (box[2] - box[0]) * (box[3] - box[1])  # noqa: E731
    return width * height / (area(a) + area(b) - width * height)


def agreement(reference: list[dict], other: list[dict]) -> tuple[int, int, int]:
    """How many boxes in `other` match one in `reference` (overlap of at least half, one each), of how many in each."""
    pairs = sorted(((overlap(r["box"], o["box"]), i, j) for i, r in enumerate(reference)
                    for j, o in enumerate(other)), reverse=True)
    used_r, used_o = set(), set()
    for score, i, j in pairs:
        if score >= 0.5 and i not in used_r and j not in used_o:
            used_r.add(i)
            used_o.add(j)
    return len(used_r), len(reference), len(other)


def side_by_side(path: Path, left: list[dict], right: list[dict], titles: tuple[str, str]) -> None:
    from PIL import Image, ImageDraw, ImageFont

    a, b = redact_image(path, left, outline=True), redact_image(path, right, outline=True)
    bar = max(24, a.height // 14)
    sheet = Image.new("RGB", (a.width * 2 + 12, a.height + bar), "white")
    sheet.paste(a, (0, bar))
    sheet.paste(b, (a.width + 12, bar))
    font = ImageFont.load_default(size=int(bar * 0.6))
    draw = ImageDraw.Draw(sheet)
    for x, title in ((0, titles[0]), (a.width + 12, titles[1])):
        draw.text((x + 4, bar * 0.15), title, fill="black", font=font)
    folder = OUT / "compare"
    folder.mkdir(parents=True, exist_ok=True)
    sheet.save(folder / f"{path.stem}.jpg", quality=88)


def main() -> None:
    parser = argparse.ArgumentParser(description="Score gpt-6.1-terra and the model Sous trained on held-out samples.")
    parser.add_argument("--sous-model", default=os.environ.get("SOUS_MODEL"),
                        help="the Sous model, or one of its candidates as <model>:<candidate> (default SOUS_MODEL)")
    parser.add_argument("--only", choices=["teacher", "sous"])
    parser.add_argument("--fresh", action="store_true", help="make every call again")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    documents = sorted(p for p in (HERE / "samples" / "test" / "documents").glob("*.jpg")
                       if not p.stem.endswith((".redacted", ".review")))  # not redact.py's copies
    with open(HERE / "samples" / "test" / "conversations.jsonl") as rows:
        chats = [json.loads(row) for row in rows]
    jobs = [(path.stem, {"image": path}) for path in documents] + [(c["id"], {"text": c["text"]}) for c in chats]

    runs: dict[str, dict] = {}
    if args.only != "sous":
        runs[MODEL] = answers(MODEL, OpenAI(max_retries=4, timeout=600), MODEL, jobs, args.fresh, args.workers)
    if args.only != "teacher":
        if not args.sous_model:
            sys.exit("Say which Sous model to score: set SOUS_MODEL or pass --sous-model.")
        client, _ = sous_client()
        check_trained(client, args.sous_model)
        runs[args.sous_model] = answers(args.sous_model, client, args.sous_model, jobs, args.fresh, args.workers)

    names = list(runs)
    rows: list[tuple[str, list[str]]] = [(f"Chats ({len(chats)}, {sum(len(c['pii']) for c in chats)} pieces of PII)",
                                          ["" for _ in names])]
    scores = [chat_scores(chats, runs[name]) for name in names]
    for metric in scores[0]:
        rows.append((f"  {metric}", [f"{s[metric]:.1%}" for s in scores]))
    rows.append(("  Seconds per chat (median)",
                 [f"{statistics.median(runs[n][c['id']]['seconds'] for c in chats):.1f}" for n in names]))
    rows.append((f"Documents ({len(documents)})", ["" for _ in names]))
    per_document = [sum(len(runs[n][p.stem]["found"]) for p in documents) / len(documents) for n in names]
    rows.append(("  Items found per document", [f"{count:.1f}" for count in per_document]))
    if MODEL in runs and len(names) > 1:
        other = names[1]
        matched = [agreement(runs[MODEL][p.stem]["found"], runs[other][p.stem]["found"]) for p in documents]
        same, theirs, ours = (sum(m[k] for m in matched) for k in range(3))
        rows.append((f"  Boxes {MODEL} drew that it also drew", ["", f"{same / max(1, theirs):.1%}"]))
        rows.append((f"  Its boxes {MODEL} also drew", ["", f"{same / max(1, ours):.1%}"]))
        for path in documents:
            side_by_side(path, runs[MODEL][path.stem]["found"], runs[other][path.stem]["found"], (MODEL, other))
    rows.append(("  Seconds per document (median)",
                 [f"{statistics.median(runs[n][p.stem]['seconds'] for p in documents):.1f}" for n in names]))
    failed = [sum(bool(result.get("failed")) for result in runs[n].values()) for n in names]
    if any(failed):
        rows.append(("Replies that failed (scored as finding nothing)", [str(count) for count in failed]))

    width = max(len(label) for label, _ in rows) + 2
    columns = [max(len(n), 8) + 2 for n in names]
    print("\n" + " " * width + "".join(n.rjust(c) for n, c in zip(names, columns)))
    for label, values in rows:
        print(label.ljust(width) + "".join(v.rjust(c) for v, c in zip(values, columns)))
    if MODEL in runs and len(names) > 1:
        print(f"\nSide by side: {(OUT / 'compare').relative_to(HERE)}/")


if __name__ == "__main__":
    main()
