# Receipt extractor

Pull the company, the date, the address, and the total out of a scanned receipt's OCR text, in one call.

```python
import os
from extract import extract_receipt, sous_client

client = sous_client()  # SOUS_API_KEY from the environment
extract_receipt(client, os.environ.get("SOUS_MODEL", "798db1a3"), ocr)
# {"company": "RESTORAN WAN SHENG", "date": "16-03-2018", "address": "NO.2, JALAN TEMENGGUNG 19/9, ...", "total": "9.60"}
```

This is the receipt extractor at [app.sousml.com/models/798db1a3](https://app.sousml.com/models/798db1a3).
Sous trained it from 250 labeled receipts, and the fine-tuned Qwen3-VL 8B (`c3`) answers its calls.

## How it was made

`receipts.csv` is 250 receipts from the ICDAR 2019 SROIE dataset: the OCR lines of one receipt, and the company,
date, address, and total from the dataset's labels. 200 were drawn from SROIE's training set and 50 from its test
set. Two receipts with a missing field were left out. The file was uploaded to Sous with the four label columns
named as the answers.

Sous holds out its own fifth of whatever you upload, and it does not train on one set of rows and score another set
you mark. It ignored that sampling, held out the 50 rows whose `split` is `test`, and trained on the other 200.
The labels were used as given. gpt-6.1-terra was only scored on the held-out 50, where it matched the labels on
88% of receipts.

| Model | All four fields | Company | Date | Address | Total | Per 1,000 calls |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen3-VL 2B | 84% | 94% | 100% | 94% | 96% | $0.06 |
| Qwen3-VL 2B, trained longer | 82% | 96% | 100% | 88% | 96% | $0.06 |
| Qwen3-VL 4B | 84% | 96% | 100% | 90% | 96% | $0.12 |
| **Qwen3-VL 8B**, which Sous recommended | **88%** | **98%** | **100%** | **96%** | **94%** | **$0.25** |
| gpt-6.1-terra | 88% | | | | | $1.13 |

Before training, the 8B model matched all four fields on 64% of the same 50 receipts. Training cost $3.34. A call
takes about 3.6 seconds once the server is up, and about 3 minutes the first time after it has slept.

## Fifty receipts it had not seen

`test.csv` is 50 more receipts from SROIE's test set. None of them are in `receipts.csv`. `test-answers.jsonl` is
what the 8B model returned, and every call was answered by that model.

Exact match against the labels, on all four fields: **32 of 50**. Company 92%, date 98%, address 68%, total 98%.
The address is where exact match falls apart. Most of those misses are a space, a comma, or the model repeating a
line the label had normalized.

`test-review.csv` marks each remaining difference:

- `follows_receipt`: the model copied the OCR, and the label says something else.
- `spelling`: the model corrected an obvious misspelling in the OCR and the label.
- `real`: a wrong value.

Spacing and punctuation are ignored on their own, without a row in that file. With those counted as acceptable:
**49 of 50**.

The one real miss is `X510056849111`. The receipt prints `TOTAL RM7.42`, then `ROUNDING -0.02` and `RM7.40` beside
`CASH`. The label is `RM7.42`. The model returned `RM7.40`, the amount after rounding.

```sh
python score.py            # the saved answers: 32 of 50 exact, 49 of 50 acceptable
python score.py --live     # call 798db1a3 again
```

## What's here

| File | What it is |
| --- | --- |
| `receipts.csv` | 250 receipts Sous trained on. `split` is `test` for the 50 it held out |
| `test.csv` | 50 further SROIE test receipts, with the dataset's labels |
| `test-answers.jsonl` | The 8B model's answers on `test.csv` |
| `test-review.csv` | The differences that are not just spacing or punctuation, and which ones still count |
| `extract.py` | `extract_receipt()`, and a command line for one file or a CSV |
| `score.py` | Exact and acceptable scores against the labels |

## Run it

From the top of this repo: `pip install -r requirements.txt`.

```sh
export SOUS_API_KEY=hk_...
export SOUS_MODEL=798db1a3
python extract.py --csv test.csv --limit 5
python score.py
```

Calling `798db1a3` takes the API key of the account that owns it. To train your own, upload `receipts.csv` in Sous
and say that `company`, `date`, `address`, and `total` are the answers and `ocr` is the input. Sous will hold out
its own 50 rows, so they will not be the rows marked `test` here.

The model's server sleeps after 2 minutes without a call. The next call wakes it, which takes about 3 minutes.

## The receipts

The OCR text and the four labels are from the ICDAR 2019 Competition on Scanned Receipt OCR and Information
Extraction (SROIE). The receipt images are not in this repo. SROIE's own training and test split is not the `split`
column: that column is the holdout Sous chose from these 250.
