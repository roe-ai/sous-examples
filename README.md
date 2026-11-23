# Sous examples

Three models [Sous](https://sousml.com) trained, with the code that calls them and the data they learned from. Sous
distills the frontier model your app calls into a small open model for one job, tests it on examples it never saw,
and switches your app over when it's ready.

The redactor and the router are in the [Sous sandbox](https://sandbox.sousml.com), where you can look through how
they trained and try them, without an account. The receipt extractor is the model trained for this example,
[`798db1a3`](https://app.sousml.com/models/798db1a3), and calling it takes that account's API key.

| Example | The job | What Sous learned from | Its small model | Per 1,000 calls |
| --- | --- | --- | --- | --- |
| [PII redactor](pii-redactor) | Find the personal information in ID photos and support chats | 127 calls an app made to gpt-6.1-terra, 47 of them with an image | Qwen3-VL 4B, 83% the same answers | $0.65, against $5.55 |
| [Support ticket router](support-ticket-router) | Send each ticket to the right queue and flag the urgent ones | A spreadsheet of 420 tickets, labeled by gpt-6.1-terra | Qwen3-VL 4B, 95% the same answers | $0.06, against $0.71 |
| [Receipt extractor](receipt-extractor) | Pull company, date, address, and total from a receipt's OCR | 250 SROIE receipts, with the dataset's own labels | Qwen3-VL 8B, 88% of the labels | $0.25, against $1.13 |

"The same answers" is how often the small model answered like gpt-6.1-terra on the examples Sous held out from
training. On the receipts, 88% is how often the 8B model matched the SROIE labels on the 50 receipts Sous held out;
gpt-6.1-terra matched those same labels 88% of the time. Training cost $5.02 for the redactor, $2.40 for the
router, and $3.34 for the receipt extractor.

## Set up

Python 3.9 or later:

```sh
pip install -r requirements.txt
```

Calling Sous takes an API key. Sous is letting people in from its waitlist: join at [sousml.com](https://sousml.com),
and once you're in, make a key in Sous under **API keys**. Every account starts with $20 of credit.

```sh
export SOUS_API_KEY=hk_...
```

Without a key, you can still read the data, run the generators, and run the PII redactor straight against OpenAI
with your own `OPENAI_API_KEY`.

## Calling a Sous model

Sous speaks OpenAI's API. Point an OpenAI client at it and call your model by its id:

```python
import os
from openai import OpenAI

client = OpenAI(base_url="https://api.sousml.com/v1", api_key=os.environ["SOUS_API_KEY"])
reply = client.chat.completions.create(model="<your model's id>", messages=[{"role": "user", "content": "..."}])
```

Until a small model answers a model's calls, Sous passes them to the frontier model it learns from and keeps each
one to train on. Once you switch, the same code calls the small model. `<id>:c2` calls one of the small models Sous
trained by name, before you switch to it. The [docs](https://sousml.com/docs) have the rest of the API.

## The data

- `pii-redactor/samples/`: 59 specimen ID documents, which their issuers publish to show what their cards look like
  ([sources](pii-redactor/samples/SOURCES.md)), and 100 made-up support chats with where each piece of PII is in
  them. `samples/answers.jsonl` holds gpt-6.1-terra's answer to each of the 127 calls Sous learned from.
- `support-ticket-router/tickets.csv`: 420 made-up tickets for an invoicing app. `tickets-labeled.csv` adds the route
  and the urgency gpt-6.1-terra gave each one, and which 84 Sous held out to test on.
- `receipt-extractor/receipts.csv`: 250 SROIE receipts, OCR text plus company, date, address, and total. `split`
  says which 50 Sous held out. `test.csv` is 50 further receipts from SROIE's own test set.

## License

The code, the chats, and the tickets are [MIT licensed](LICENSE). The ID documents are their issuers' specimens, not
ours: check each publisher's terms before you use them anywhere else. The receipt text and labels come from the
ICDAR 2019 SROIE dataset; the images are not included.
