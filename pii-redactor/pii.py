"""Find the personal information (PII) in a document image or a long text with one model call: a box around each
item in an image, the character offsets of each item in a text.

    from openai import OpenAI
    from pii import find_pii, redact_image, redact_text

    client = OpenAI(base_url="https://api.sousml.com/v1", api_key=os.environ["SOUS_API_KEY"])
    found = find_pii(client, image="card.jpg", model=model)  # [{"type": "name", "value": "JANICE SAMPLE", "box": ...}]
    found = find_pii(client, text=chat, model=model)  # [{"type": "email", "value": "...", "start": 1204, "end": 1225}]

`model` is your Sous model's id. Until a model Sous trained answers its calls, Sous passes each one to gpt-6.1-terra and
keeps it to learn from; after you switch, the same calls go to the small model. A plain OpenAI client, with the
default model, calls gpt-6.1-terra directly.
"""

from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path
from typing import Any, Union

MODEL = "gpt-6.1-terra"
# Images are sent at most this many pixels on their longer side; boxes come back for the image as given.
MAX_SIDE = 1536

TYPES = ["name", "date_of_birth", "address", "id_number", "phone", "email", "financial", "credential", "ip_address",
         "face", "signature", "machine_readable", "physical_description", "other"]


def _schema(**fields: dict) -> dict:
    item = {"type": "object", "additionalProperties": False, "required": list(fields), "properties": fields}
    return {"type": "object", "additionalProperties": False, "required": ["items"],
            "properties": {"items": {"type": "array", "items": item}}}


_TYPE = {"type": "string", "enum": TYPES}
_BOX = {"type": "object", "additionalProperties": False, "required": ["x0", "y0", "x1", "y1"],
        "properties": {side: {"type": "integer"} for side in ("x0", "y0", "x1", "y1")}}
IMAGE_SCHEMA = _schema(type=_TYPE, value={"type": "string"}, box=_BOX)
TEXT_SCHEMA = _schema(type=_TYPE, value={"type": "string"})

INSTRUCTIONS = """\
Find all the personal information (PII) in the document image or text you're given, in one pass.

PII is anything that identifies a person or opens their accounts:
- name: a person's name, whole or in part (customers, staff, relatives, anyone), not a company's
- date_of_birth
- address: a person's street or mailing address, as one item (a city or country on its own isn't PII)
- id_number: a person's government or account numbers: SSN, passport, driver's license, national ID, tax ID, and \
member, policy, patient, employee, or customer numbers
- phone, email, ip_address
- financial: full card numbers, card security codes, bank account numbers, IBANs
- credential: passwords, PINs, one-time codes, API keys and tokens, answers to security questions
- on documents: face (every photo of the holder, small ones too), signature, machine_readable (MRZ lines, barcodes, \
QR codes), physical_description (sex, height, weight, eye or hair color)
- other: anything else that identifies a person, such as a license plate or a vehicle's VIN

Not PII: amounts and prices; order, ticket, case, claim, booking, invoice, and tracking numbers; flight numbers; dates \
and times other than a birth date, issue and expiry dates included; the last 4 digits of a card or account on their \
own; company, product, and place names; printed field labels; the issuer; license class, restrictions, and \
endorsements; SAMPLE or SPECIMEN marks.

For an image: box is a tight box around the value itself, not its label, in coordinates from 0 to 1000 of the image's \
width (x0, x1) and height (y0, y1). List each place a value appears.
For a text: list every occurrence in the order they appear, repeats included.
value is the text exactly as written, character for character; for a face, signature, or barcode, a few words saying \
what it is."""

ImageInput = Union[str, Path, bytes]
_LABELS = {"date_of_birth": "birth date", "id_number": "ID", "physical_description": "physical",
           "machine_readable": "code", "ip_address": "IP"}


def find_pii(client: Any, *, image: ImageInput | None = None, text: str | None = None,
             model: str = MODEL) -> list[dict]:
    """The PII in an image or a text, from one call to `model`.

    For an image, each item is {"type", "value", "box": [x0, y0, x1, y1]} in the image's pixels. For a text, each is
    {"type", "value", "start", "end"}, where text[start:end] == value. Models don't count characters reliably, so
    the model lists each value as written, in order, and find_pii finds where it is.
    """
    if (image is None) == (text is None):
        raise ValueError("Pass an image or a text.")
    if image is not None:
        url, width, height = _data_url(image)
        content: Any = [{"type": "image_url", "image_url": {"url": url}}]
    else:
        content = text
    schema = IMAGE_SCHEMA if image is not None else TEXT_SCHEMA
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": INSTRUCTIONS}, {"role": "user", "content": content}],
        response_format={"type": "json_schema", "json_schema": {"name": "pii", "strict": True, "schema": schema}},
    )
    choice = response.choices[0]
    if choice.finish_reason == "length":
        raise ValueError("The model's reply was cut off before it finished, so it may not hold all the PII.")
    items = json.loads(choice.message.content or "{}").get("items") or []
    return _boxes(items, width, height) if image is not None else _spans(items, text or "")


def redact_text(text: str, items: list[dict], *, every: bool = True) -> str:
    """The text with each item replaced by its type, like [EMAIL]. With `every`, other places a found value is written
    are replaced too, in case the model listed a repeat only once."""
    out, at = [], 0
    for start, end, kind in hidden(text, items, every=every):
        out += [text[at:start], f"[{kind.upper()}]"]
        at = end
    return "".join(out) + text[at:]


def hidden(text: str, items: list[dict], *, every: bool = True) -> list[tuple[int, int, str]]:
    """What redact_text hides, as (start, end, type) in order, merged where they overlap."""
    spans = [(i["start"], i["end"], i["type"]) for i in items]
    if every:
        for item in items:
            pattern = _whole(item["value"])
            if pattern:
                spans += [(m.start(), m.end(), item["type"]) for m in re.finditer(pattern, text)]
    return _merged(spans)


def redact_image(image: ImageInput, items: list[dict], *, outline: bool = False) -> Any:
    """The image (a PIL image) with a black box over each item, or with each outlined and labeled, to check them."""
    from PIL import ImageDraw, ImageFont

    picture = _open(image).convert("RGB")
    draw = ImageDraw.Draw(picture)
    line = max(2, picture.width // 400)
    font = ImageFont.load_default(size=max(10, picture.width // 90))
    for item in items:
        x0, y0, x1, y1 = item["box"]
        if not outline:
            draw.rectangle((x0, y0, x1, y1), fill="black")
            continue
        draw.rectangle((x0, y0, x1, y1), outline="#e5484d", width=line)
        label = _LABELS.get(item["type"], item["type"])
        left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
        tall = bottom - top + 2 * line
        above = y0 - tall if y0 >= tall else y0
        draw.rectangle((x0, above, x0 + right - left + 2 * line, above + tall), fill="#e5484d")
        draw.text((x0 + line - left, above + line - top), label, fill="white", font=font)
    return picture


def _open(image: ImageInput) -> Any:
    from PIL import Image as PIL
    from PIL import ImageOps

    return ImageOps.exif_transpose(PIL.open(io.BytesIO(image) if isinstance(image, bytes) else image))


def _data_url(image: ImageInput) -> tuple[str, int, int]:
    """The image as a JPEG data URL, at most MAX_SIDE pixels on its longer side, and its own width and height."""
    picture = _open(image)
    width, height = picture.size
    picture = picture.convert("RGB")
    picture.thumbnail((MAX_SIDE, MAX_SIDE))
    buffer = io.BytesIO()
    picture.save(buffer, "JPEG", quality=90)
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}", width, height


def _boxes(items: list[dict], width: int, height: int) -> list[dict]:
    """Items with a box, the box moved from 0-1000 to the image's pixels."""
    out = []
    for item in items:
        box = item.get("box")
        if not box:
            continue
        x0, x1 = sorted(min(max(box[side], 0), 1000) * width / 1000 for side in ("x0", "x1"))
        y0, y1 = sorted(min(max(box[side], 0), 1000) * height / 1000 for side in ("y0", "y1"))
        if x1 - x0 >= 1 and y1 - y0 >= 1:
            out.append({"type": item["type"], "value": item["value"],
                        "box": [round(x0), round(y0), round(x1), round(y1)]})
    return out


def _spans(items: list[dict], text: str) -> list[dict]:
    """Items placed on the text in the order the model listed them: each where its value is next written after the
    item before it, or else the first place no other item took. Items whose value isn't in the text are dropped."""
    out, taken, at = [], set(), 0
    for item in items:
        span = _find(text, item.get("value") or "", at, taken)
        if span is None:
            continue
        taken.add(span)
        at = span[0]
        out.append({"type": item["type"], "value": text[span[0]:span[1]], "start": span[0], "end": span[1]})
    return sorted(out, key=lambda i: (i["start"], i["end"]))


def _find(text: str, value: str, at: int, taken: set) -> tuple[int, int] | None:
    """Where `value` is written in the text, not taken, from `at` on if it can be: on its own as is, as is inside a
    longer word, then the same two in any case and with any spacing."""
    words = value.split()
    if not words:
        return None
    flexible = r"\s+".join(map(re.escape, words))
    for pattern, flags in ((_bounded(re.escape(value), value), 0), (re.escape(value), 0),
                           (_bounded(flexible, value), re.IGNORECASE), (flexible, re.IGNORECASE)):
        found = [m.span() for m in re.finditer(pattern, text, flags) if m.span() not in taken]
        if found:
            return next((span for span in found if span[0] >= at), found[0])
    return None


def _bounded(pattern: str, value: str) -> str:
    """`pattern`, not inside a longer word or number."""
    value = value.strip()
    if value[:1].isalnum():
        pattern = r"(?<![\w])" + pattern
    if value[-1:].isalnum():
        pattern += r"(?![\w])"
    return pattern


def _whole(value: str) -> str | None:
    """A pattern for `value` written on its own. None for values too short to look for safely."""
    return _bounded(re.escape(value), value) if len(value.strip()) >= 4 else None


def _merged(spans: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    merged: list[tuple[int, int, str]] = []
    for start, end, kind in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]), merged[-1][2])
        else:
            merged.append((start, end, kind))
    return merged
