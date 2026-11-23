"""Pull the company, date, address, and total from one receipt's OCR text.

    export SOUS_API_KEY=hk_... SOUS_MODEL=798db1a3
    python extract.py receipt.txt
    python extract.py --csv test.csv --limit 5

Sous gives each call the instructions the model was trained with, so a call sends only the OCR
text, one line per box, top to bottom.
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
FIELDS = ("company", "date", "address", "total")


def sous_client(**options: Any) -> OpenAI:
    """An OpenAI client for the Sous API, from SOUS_API_KEY and SOUS_BASE_URL."""
    if not os.environ.get("SOUS_API_KEY"):
        sys.exit("Set SOUS_API_KEY to a Sous API key. Make one in Sous, under API keys.")
    base = (os.environ.get("SOUS_BASE_URL") or DEFAULT_BASE_URL).rstrip("/").removesuffix("/v1")
    return OpenAI(api_key=os.environ["SOUS_API_KEY"], base_url=f"{base}/v1", **{"max_retries": 4, **options})


def parse(reply: str) -> dict:
    """{"company", "date", "address", "total"} from the model's reply."""
    answer = json.loads(reply[reply.find("{"):reply.rfind("}") + 1])
    return {field: "" if answer.get(field) is None else str(answer.get(field)).strip() for field in FIELDS}


def extract_receipt(client: OpenAI, model: str, ocr: str) -> dict:
    """The four fields for one receipt."""
    response = client.chat.completions.create(model=model, messages=[{"role": "user", "content": ocr}])
    return parse(response.choices[0].message.content or "")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract company, date, address, and total from receipt OCR.")
    parser.add_argument("ocr", nargs="?", help="a file of OCR text, one line per box")
    parser.add_argument("--csv", help="extract the receipts in a CSV with an ocr column instead")
    parser.add_argument("--limit", type=int, default=5, help="with --csv, how many receipts (default 5)")
    parser.add_argument("--model", default=os.environ.get("SOUS_MODEL", "798db1a3"),
                        help="the Sous model's id, or one student as <id>:c3 (default SOUS_MODEL, else 798db1a3)")
    args = parser.parse_args()
    if not args.ocr and not args.csv:
        parser.error("give an OCR file, or --csv")

    client = sous_client(timeout=600)
    if args.ocr:
        text = open(args.ocr, encoding="utf-8").read()
        print(json.dumps(extract_receipt(client, args.model, text), ensure_ascii=False))
        return
    with open(args.csv, newline="", encoding="utf-8") as rows:
        for row in list(csv.DictReader(rows))[:args.limit]:
            answer = extract_receipt(client, args.model, row["ocr"])
            print(f"{row['id']}  {answer['company'][:40]:<40}  {answer['date']:<16}  {answer['total']}")


if __name__ == "__main__":
    main()
