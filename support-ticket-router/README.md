# Support ticket router

Send each support ticket to the queue it belongs in (billing, bug, feature_request, account or other) and flag the
urgent ones: security problems, and outages that stop customers from working or paying. One call per ticket, to a
small model Sous trained from a spreadsheet of tickets.

```python
from route import route_ticket, sous_client

client = sous_client()  # SOUS_API_KEY from the environment
route_ticket(client, "<your model's id>", "Can't log in", "Someone changed my account email and my password is gone.")
# {"route": "account", "urgent": True}
```

This is the support ticket router in the [Sous sandbox](https://sandbox.sousml.com/models/05856571): how Sous
designed it, every ticket it was tested on, and a playground to try it.

## How it was made

`tickets.csv` was uploaded to Sous, with the job described in a sentence:

> Route each support ticket to billing, bug, feature_request, account or other, and flag it as urgent if it's about
> a security problem (a hacked account, leaked data or credentials, phishing) or an outage that stops customers from
> working or paying.

Sous designed the model from that: it reads each ticket's subject and body, and answers with two fields, `route` and
`urgent`, under instructions it wrote for edge cases (an outage at checkout is a bug, and urgent; a routine password
reset isn't). gpt-6.1-terra labeled the 420 tickets. Sous held back 84, trained three small models on the other 336,
and tested each on the 84:

| Model | Same answers as gpt-6.1-terra | Per 1,000 calls |
| --- | --- | --- |
| gpt-6.1-terra | | $0.71 |
| Qwen3-VL 2B | 85% | $0.03 |
| **Qwen3-VL 4B**, which Sous recommended | **95%** | **$0.06** |
| Qwen3-VL 8B | 94% | $0.14 |

Training cost $2.40. With the 4B model answering, `score.py` on the same 84 tickets:

| | The 4B model |
| --- | --- |
| Same route as gpt-6.1-terra | 98.8% |
| Same urgency | 98.8% |
| Both the same | 97.6% |
| Seconds per ticket (median, 8 at once) | 0.9 |

Its page says 95% and this says 97.6% on the same tickets: the page has the answers from when it was tested, and a
small model can answer a ticket differently from one call to the next.

## What's here

| File | What it is |
| --- | --- |
| `tickets.csv` | 420 made-up tickets for Ledgerly, an invoicing app: `id`, `subject`, `body`, `plan`, `channel` |
| `tickets-labeled.csv` | The same tickets with the `route` and `urgent` gpt-6.1-terra gave them, and `split`: the 84 Sous held out are `test` |
| `make_tickets.py` | Writes `tickets.csv`. The seed is fixed, so it writes the same tickets each time |
| `route.py` | `route_ticket()`, and a command line to route one ticket or the first rows of a CSV |
| `score.py` | Scores a Sous model on the held-out tickets against gpt-6.1-terra's labels |

## Run it

1. Install the requirements, from the top of this repo: `pip install -r requirements.txt`.

2. Train your own router. In Sous, **New model**: upload `tickets.csv` and describe the job, in the words above or
   your own. Sous drafts the model, shows gpt-6.1-terra's labels on a few tickets so you can check them, and gives
   the price before you start training.

   Have labels already? Upload `tickets-labeled.csv` instead, and say the `route` and `urgent` columns hold the
   answers. Sous then trains on those as they are, and gpt-6.1-terra answers only the held-out tickets, to compare.

3. Call it. Sous gives each call the instructions the model was trained with, so a call sends just the ticket,
   written the way the model saw tickets in training: `subject: ...` and `body: ...` on their own lines.

   ```sh
   export SOUS_API_KEY=hk_... SOUS_MODEL=<the model's id>
   python route.py "Charged twice" "I was billed \$49 twice on Monday. Can you refund one?"
   python route.py --csv tickets.csv --limit 5
   ```

   The model's server sleeps after 2 minutes without calls. The next call wakes it, which takes about 3 minutes;
   after that, answers take about a second.

4. Score it, or one of the other small models Sous trained (`<id>:c1`), on the held-out tickets:

   ```sh
   python score.py
   python score.py --model "$SOUS_MODEL:c1"
   ```

   A router you train yourself holds out its own fifth of the tickets, so some of these 84 may be ones it trained
   on: its page has the fairest numbers for it.
