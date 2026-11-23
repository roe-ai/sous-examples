"""Synthetic support tickets for a made-up invoicing app, Ledgerly, as tickets.csv (id, subject, body, plan, channel).

Every name, company and amount is made up. The seed is fixed, so it writes the same 420 tickets each time.

    python make_tickets.py
"""

import csv
import random
from pathlib import Path

rng = random.Random(7)

PLANS = ["Free", "Starter", "Growth", "Enterprise"]
CHANNELS = ["email", "chat", "web form", "phone transcript"]
NAMES = ["Priya", "Marcus", "Elena", "Tomás", "Aiko", "Sam", "Fatima", "Jonah", "Lena", "Diego", "Grace", "Omar"]
COMPANIES = ["Brightline Studio", "Okafor & Sons", "Northwind Dental", "Pixel Forge", "Harbor Bakery",
             "Summit Legal", "Greenleaf Farms", "Atlas Freight", "Blue Fern Yoga", "Kestrel Labs"]
FEATURES = ["recurring invoices", "the client portal", "PDF export", "the Stripe integration", "multi-currency",
            "expense tracking", "the mobile app", "time tracking", "late-payment reminders", "the QuickBooks sync"]
BROWSERS = ["Chrome", "Safari", "Firefox", "Edge", "the iOS app", "the Android app"]
ERRORS = ["500", "504", "ERR_SYNC_17", "a blank white page", "'Something went wrong'", "a spinner that never stops"]
GREETINGS = ["Hi,", "Hello team,", "Hey there,", "Hi Ledgerly support,", "Good morning,", "", "", "To whom it may concern,"]
SIGNOFFS = ["Thanks!", "Thanks in advance.", "Cheers,", "Regards,", "", "Appreciate the help.", "Please advise."]


def money() -> str:
    return f"${rng.choice([9, 19, 29, 49, 99, 149, 299, 1200]) + rng.choice([0, 0, 0.5, 0.99]):,.2f}".replace(".00", "")


def fill(text: str) -> str:
    return text.format(
        feature=rng.choice(FEATURES), browser=rng.choice(BROWSERS), error=rng.choice(ERRORS), amount=money(),
        amount2=money(), company=rng.choice(COMPANIES), n=rng.randint(2, 40), day=rng.choice(
            ["Monday", "Tuesday", "yesterday", "this morning", "last Friday", "the 3rd", "the 15th"]),
        name=rng.choice(NAMES))


TICKETS = {
    "billing": [
        ("Charged twice this month", "I was billed {amount} twice on {day}. Can you refund the duplicate charge?"),
        ("Refund request", "We downgraded last week but were still charged {amount} for the old plan. Please refund the difference."),
        ("Invoice from Ledgerly is wrong", "Our receipt says {amount} but our plan should be {amount2}. Which is right?"),
        ("Need a VAT invoice", "Our accountant needs a VAT-compliant invoice for the {amount} we paid {day}. Our company is {company}."),
        ("Card declined but money taken", "The app said my card was declined, but my bank shows a pending charge of {amount}."),
        ("Switch to annual billing", "How do we move from monthly to annual billing, and do we get the discount pro-rated?"),
        ("Cancel subscription", "Please cancel our subscription at the end of this billing period. We won't be renewing."),
        ("Update payment method", "Our company card expires next month. Where do I add the new card before the next charge?"),
        ("Unexpected seat charges", "We were charged for {n} seats but only {n} people use Ledgerly. Can you look into it?"),
    ],
    "bug": [
        ("PDF export broken", "Exporting an invoice to PDF gives {error} in {browser}. Started {day}."),
        ("Recurring invoices didn't send", "None of our recurring invoices went out {day}. Clients are asking where they are."),
        ("Sync error with QuickBooks", "The QuickBooks sync fails with {error} for {n} invoices. Nothing has changed on our side."),
        ("Totals don't add up", "Line items add up to {amount} but the invoice total shows {amount2}. Tax seems to be applied twice."),
        ("App crashes on open", "{browser} crashes as soon as I open the dashboard. Reinstalled twice, same result."),
        ("Client portal shows wrong invoices", "One of our clients says the client portal shows another company's invoices. Screenshot attached."),
        ("Reminder emails sent to paid clients", "Late-payment reminders went to {n} clients who already paid. Embarrassing, please fix."),
        ("Currency symbol wrong", "Invoices in EUR show a $ sign since the update {day}."),
        ("Can't upload logo", "Uploading our logo in settings shows {error}. PNG, 200 KB."),
    ],
    "feature_request": [
        ("Feature idea: partial payments", "It would help a lot if clients could pay invoices in installments."),
        ("Please add Xero integration", "We use Xero, not QuickBooks. Any plans to support it?"),
        ("Custom fields on invoices", "We need a custom field for PO numbers on every invoice. Is that on the roadmap?"),
        ("Dark mode?", "Any chance of a dark mode for the dashboard? Our team works late."),
        ("Bulk edit invoices", "Being able to bulk edit due dates on {n} invoices at once would save us hours."),
        ("More languages for invoices", "Our clients are in Germany and Japan. Can invoices be generated in other languages?"),
        ("API webhook for paid invoices", "We'd love a webhook when an invoice is paid so we can update our CRM."),
        ("Better reports", "Could the reports page show revenue by client over time? Right now it's only monthly totals."),
    ],
    "account": [
        ("Can't log in", "I reset my password but the login page keeps saying my credentials are invalid."),
        ("Change account owner", "{name} left the company. How do we transfer ownership of the account to me?"),
        ("Add a teammate", "How do I invite our new bookkeeper to the account with view-only access?"),
        ("Two-factor codes not arriving", "I'm not receiving the 2FA text message, so I'm locked out."),
        ("Delete my data", "We're closing {company}. Please delete our account and all of our data."),
        ("Change company email", "We rebranded. How do I change the login email for everyone on our team?"),
        ("Merge two accounts", "We accidentally created two Ledgerly accounts. Can they be merged?"),
    ],
    "other": [
        ("Partnership inquiry", "I run an accounting firm with {n} clients. Do you have a partner or reseller program?"),
        ("Do you offer nonprofit pricing?", "We're a registered nonprofit. Is there a discount?"),
        ("Question about data residency", "Where is our data stored? We need it to stay in the EU for compliance."),
        ("Interview request", "I'm writing an article about invoicing tools for small businesses. Could someone from your team chat?"),
        ("Compliment", "Just wanted to say the new dashboard is great. Our team loves it."),
        ("Job application", "Are you hiring support staff? I'd love to work at Ledgerly."),
    ],
}

URGENT = [
    ("Someone else logged into our account", "We got a login alert from a country we've never been to, and {n} invoices were changed. Is our account hacked?"),
    ("Possible data breach", "One of our clients received an invoice email with another customer's bank details on it."),
    ("Entire app is down", "Nobody on our team can load Ledgerly. We get {error} everywhere. We have invoices due today."),
    ("Payments not going through for anyone", "None of our clients can pay invoices since {day}. The pay button gives {error}."),
    ("Phishing email pretending to be you", "Our clients are getting emails that look like Ledgerly invoices asking for card details. They're fake."),
    ("API keys exposed", "We accidentally pushed our Ledgerly API key to a public GitHub repo. What should we do right now?"),
]


def ticket(plan: str, subject: str, body: str) -> tuple[str, str]:
    greeting, signoff = rng.choice(GREETINGS), rng.choice(SIGNOFFS)
    text = fill(body)
    if rng.random() < 0.3:
        text += " " + fill(rng.choice([
            "We're on the {plan} plan if that matters.", "This is urgent for us, our month-end close is {day}.",
            "I already tried clearing the cache.", "My colleague {name} saw the same thing.",
            "We've been customers for {n} months.", "Not a big deal, just curious."]).replace("{plan}", plan))
    parts = [p for p in (greeting, text, signoff, rng.choice(NAMES) if signoff else "") if p]
    return fill(subject), "\n\n".join(parts) if rng.random() < 0.5 else " ".join(parts)


rows = []
weights = {"billing": 0.25, "bug": 0.25, "feature_request": 0.17, "account": 0.15, "other": 0.1, "urgent": 0.08}
for i in range(420):
    kind = rng.choices(list(weights), weights=list(weights.values()))[0]
    plan = rng.choice(PLANS)
    subject, body = ticket(plan, *rng.choice(URGENT if kind == "urgent" else TICKETS[kind]))
    rows.append({"id": f"T-{10432 + i}", "subject": subject, "body": body, "plan": plan,
                 "channel": rng.choice(CHANNELS)})

with open(Path(__file__).with_name("tickets.csv"), "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["id", "subject", "body", "plan", "channel"])
    writer.writeheader()
    writer.writerows(rows)
print(len(rows), "tickets")
