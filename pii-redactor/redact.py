"""Redact a document image or a text file with one model call.

    python redact.py card.jpg            # card.redacted.jpg, with a black box over each piece of PII
    python redact.py card.jpg --review   # card.review.jpg, with each one outlined and labeled
    python redact.py chat.txt            # chat.redacted.txt, with [NAME], [EMAIL], ... in place of the PII
    python redact.py chat.txt --json     # what was found, as JSON

With SOUS_MODEL and SOUS_API_KEY set, the call goes to your Sous model: to gpt-6.1-terra while Sous learns from it,
and to the model Sous trained once you switch to it. Without them, it's a plain call to gpt-6.1-terra, with
OPENAI_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from openai import OpenAI

from pii import MODEL, find_pii, redact_image, redact_text

IMAGES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Redact the PII in an image or a text file.")
    parser.add_argument("path", type=Path, help="an image, or a text file")
    parser.add_argument("--review", action="store_true", help="outline and label what was found instead of hiding it")
    parser.add_argument("--json", action="store_true", help="print what was found instead of writing a file")
    args = parser.parse_args()

    model = os.environ.get("SOUS_MODEL")
    if model:
        base = (os.environ.get("SOUS_BASE_URL") or "https://api.sousml.com").rstrip("/").removesuffix("/v1")
        client = OpenAI(api_key=os.environ.get("SOUS_API_KEY"), base_url=f"{base}/v1", max_retries=4, timeout=600)
    else:
        client = OpenAI(max_retries=4, timeout=600)
    image = args.path.suffix.lower() in IMAGES
    text = None if image else args.path.read_text()
    given = {"image": args.path} if image else {"text": text}
    found = find_pii(client, model=model or MODEL, **given)
    if args.json:
        json.dump(found, sys.stdout, indent=1, ensure_ascii=False)
        print()
        return
    if image:
        out = args.path.with_suffix(f".{'review' if args.review else 'redacted'}.jpg")
        redact_image(args.path, found, outline=args.review).save(out, quality=90)
    else:
        out = args.path.with_suffix(".redacted" + args.path.suffix)
        out.write_text(redact_text(text or "", found))
    print(f"Found {len(found)}; wrote {out}")


if __name__ == "__main__":
    main()
