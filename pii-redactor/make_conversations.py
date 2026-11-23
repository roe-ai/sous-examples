"""Write long, made-up support chats full of personal information, with where each piece is, to score the redactor
on texts no one had to label by hand.

    python make_conversations.py   # samples/conversations.jsonl (80) and samples/test/conversations.jsonl (20)

Every value is fake by construction: phone numbers in 555-0100 to 555-0199, emails at example.com, .org, and .net, IP
addresses from the ranges kept for documentation, SSNs starting with 9 (never issued), card numbers from the 400000
test range, and names drawn at random. The chats also hold things that look like PII but aren't, by the redactor's
rules: order, ticket, and claim numbers, amounts, appointment dates, the last 4 digits of a card.

Each record is {"id", "domain", "text", "pii": [{"type", "value", "start", "end"}]}, with text[start:end] == value.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent

FIRST = """Amara Andre Anika Arjun Beatriz Carmen Chidi Dalia Daniel Dmitri Elena Emeka Esther Farah Felipe Fiona
Gabriel Hana Hassan Imani Ingrid Isabel Jamal Jasmine Javier Jonas Kenji Kwame Laila Lucas Malik Mariana Mateo Mei Nadia
Naomi Nikhil Noor Olga Omar Paolo Priya Rafael Rania Ravi Rosa Samir Sofia Sunita Tariq Tomas Valentina Yara Yusuf
Zainab Zoltan Aisha Bruno Camila Diego Fatima Giulia Hiroshi Ines Joaquin Katarzyna Leon Marisol Nils Oksana Pedro
Quentin Renata Siddharth Thandiwe Ulrich Viktor Wanjiru Ximena Yohannes""".split()
LAST = """Abara Adeyemi Alvarez Andersson Bauer Benali Bianchi Castillo Chen Costa Dubois Eriksen Ferreira Fischer
Garcia Goldberg Haddad Hansen Hoang Ibrahim Ivanova Jensen Kamau Kaur Kim Kowalski Larsen Lindqvist Lopez Mahmoud Mendes
Moreau Murphy Nakamura Nguyen Novak Nwosu Okafor Oliveira Ortiz Osei Park Patel Petrov Quispe Ramirez Rossi Sato Schmidt
Silva Singh Sokolova Tanaka Torres Varga Vasquez Wagner Walsh Yamamoto Yilmaz Zhang Zielinski Bergstrom Castellanos
Delacroix Esposito Fontaine Gallagher Halvorsen Iwasaki Jovanovic""".split()
STREETS = """Maple Oak Cedar Willow Elm Birch Juniper Harbor Lakeview Ridge Sunset Meadow Orchard Highland Riverside
Mill Chestnut Aspen Magnolia Laurel""".split()
STREET_KINDS = ["St", "Ave", "Rd", "Blvd", "Ln", "Dr", "Ct", "Way", "Terrace", "Place"]
CITIES = [("Springfield", "IL", "627"), ("Portland", "OR", "972"), ("Austin", "TX", "787"), ("Columbus", "OH", "432"),
          ("Raleigh", "NC", "276"), ("Madison", "WI", "537"), ("Tucson", "AZ", "857"), ("Boise", "ID", "837"),
          ("Albany", "NY", "122"), ("Richmond", "VA", "232"), ("Denver", "CO", "802"), ("Omaha", "NE", "681"),
          ("Savannah", "GA", "314"), ("Spokane", "WA", "992"), ("Burlington", "VT", "054"), ("Fresno", "CA", "937")]
AREA_CODES = "212 312 415 617 702 206 303 512 404 614 919 608 520 208 518 804".split()
WORDS = "Sunflower Trombone Galaxy Pumpkin Lighthouse Marmalade Pinecone Thunder Velvet Cobalt Saffron Glacier".split()
PETS = ["Biscuit", "Pepper", "Rocket", "Mango", "Waffles", "Juniper", "Pickles", "Luna"]
UPPER = "ABCDEFGHJKLMNPRSTUVWXYZ"
ALNUM = UPPER + "23456789"


def digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def letters(rng: random.Random, n: int, alphabet: str = UPPER) -> str:
    return "".join(rng.choice(alphabet) for _ in range(n))


def phone(rng: random.Random) -> str:
    area, line = rng.choice(AREA_CODES), f"01{digits(rng, 2)}"
    return rng.choice([f"({area}) 555-{line}", f"{area}-555-{line}", f"{area}.555.{line}", f"+1 {area} 555 {line}"])


def card(rng: random.Random) -> str:
    """A 16-digit test card number that passes the Luhn check."""
    body = "400000" + digits(rng, 9)
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch) * (2 if i % 2 == 0 else 1)
        total += d - 9 if d > 9 else d
    full = body + str((10 - total % 10) % 10)
    return rng.choice([" ", "-", ""]).join(full[i:i + 4] for i in range(0, 16, 4))


def iban(rng: random.Random) -> str:
    """A German or Dutch IBAN with correct check digits."""
    country, bban = rng.choice([("DE", digits(rng, 18)), ("NL", letters(rng, 4) + digits(rng, 10))])
    check = 98 - int("".join(str(int(c, 36)) for c in bban + country + "00")) % 97
    raw = f"{country}{check:02d}{bban}"
    return " ".join(raw[i:i + 4] for i in range(0, len(raw), 4))


def address(rng: random.Random) -> str:
    city, state, zip3 = rng.choice(CITIES)
    unit = rng.choice(["", "", f", Apt {rng.randint(1, 30)}{rng.choice('ABCD')}", f", Unit {rng.randint(100, 999)}"])
    return (f"{rng.randint(12, 9890)} {rng.choice(STREETS)} {rng.choice(STREET_KINDS)}{unit}, {city}, {state} "
            f"{zip3}{digits(rng, 2)}")


def birthday(rng: random.Random) -> str:
    born = date(1950, 1, 1) + timedelta(days=rng.randrange(365 * 55))
    return rng.choice([f"{born:%B} {born.day}, {born.year}", f"{born:%m/%d/%Y}", born.isoformat(),
                       f"{born.day} {born:%b} {born.year}"])


def someday(rng: random.Random) -> str:
    day = date(2026, 1, 5) + timedelta(days=rng.randrange(300))
    return rng.choice([f"{day:%B} {day.day}", f"{day:%m/%d/%Y}", day.isoformat(), f"{day:%A}, {day:%B} {day.day}"])


def amount(rng: random.Random) -> str:
    return f"${rng.randint(5, 2400):,}.{rng.choice(['00', '49', '99', digits(rng, 2)])}"


def person(rng: random.Random, domain: dict) -> dict:
    """Who the chats are about, the same in every chat of a conversation: (value, PII type or None) per slot."""
    first, last = rng.choice(FIRST), rng.choice(LAST)
    relative_first, relative_last = rng.choice([n for n in FIRST if n != first]), rng.choice(LAST)
    number = card(rng)
    host = rng.choice(["example.com", "example.org", "example.net", "mail.example.com"])
    email = rng.choice([f"{first}.{last}", f"{first[0]}{last}", f"{first}{rng.randint(2, 99)}", f"{last}.{first[0]}"])
    return {
        "name": (f"{first} {last}", "name"), "first": (first, "name"), "last": (last, "name"),
        "name_caps": (f"{last.upper()}/{first.upper()}", "name"),
        "relative": (f"{relative_first} {relative_last}", "name"), "relative_first": (relative_first, "name"),
        "dob": (birthday(rng), "date_of_birth"),
        "address": (address(rng), "address"), "address2": (address(rng), "address"),
        "phone": (phone(rng), "phone"), "phone2": (phone(rng), "phone"),
        "email": (f"{email.lower()}@{host}", "email"),
        "email2": (f"{first}.{last}@{domain['slug']}.example.com".lower(), "email"),
        "ssn": (f"9{digits(rng, 2)}-{digits(rng, 2)}-{digits(rng, 4)}", "id_number"),
        "passport": (letters(rng, 1) + digits(rng, 8), "id_number"),
        "passport2": (letters(rng, 1) + digits(rng, 8), "id_number"),
        "license": (rng.choice([f"D{digits(rng, 7)}", f"{letters(rng, 1)}{digits(rng, 3)}-{digits(rng, 4)}-"
                                                       f"{digits(rng, 4)}"]), "id_number"),
        "member": (rng.choice([f"MBR{digits(rng, 9)}", f"W{digits(rng, 9)}"]), "id_number"),
        "policy": (f"POL-{digits(rng, 8)}", "id_number"), "policy2": (f"POL-{digits(rng, 8)}", "id_number"),
        "mrn": (digits(rng, 8), "id_number"), "employee": (f"E{digits(rng, 6)}", "id_number"),
        "customer": (digits(rng, 10), "id_number"), "frequent": (letters(rng, 2) + digits(rng, 9), "id_number"),
        "card": (number, "financial"), "cvv": (digits(rng, 3), "financial"),
        "account": (digits(rng, rng.randint(9, 12)), "financial"), "iban": (iban(rng), "financial"),
        "password": (f"{rng.choice(WORDS)}{rng.choice('!@#$%&*')}{digits(rng, rng.randint(2, 4))}", "credential"),
        "pin": (digits(rng, rng.choice([4, 6])), "credential"),
        "answer": (rng.choice(PETS), "credential"),
        "api_key": ("dev_" + letters(rng, 28, ALNUM.lower() + "0123456789"), "credential"),
        "ip": (f"{rng.choice(['192.0.2', '198.51.100', '203.0.113'])}.{rng.randint(2, 254)}", "ip_address"),
        "ip2": (f"{rng.choice(['192.0.2', '198.51.100', '203.0.113'])}.{rng.randint(2, 254)}", "ip_address"),
        "plate": (rng.choice([f"{digits(rng, 1)}{letters(rng, 3)}{digits(rng, 3)}",
                              f"{letters(rng, 3)}-{digits(rng, 4)}"]), "other"),
        "vin": (letters(rng, 17, ALNUM), "other"),
        "last4": (number.replace(" ", "").replace("-", "")[-4:], None),
        "company": (domain["company"], None), "product": (rng.choice(domain["products"]), None),
    }


def session(rng: random.Random, first: str) -> dict:
    """What changes from one chat to the next: the agent, and the orders, dates, and amounts talked about."""
    names = [n for n in FIRST if n != first]
    return {
        "agent": (rng.choice(names), "name"), "colleague": (f"{rng.choice(names)} {rng.choice(LAST)}", "name"),
        "doctor": (rng.choice(LAST), "name"), "otp": (digits(rng, 6), "credential"),
        "order": (f"{rng.choice(['WX', 'NW', 'A', 'CT'])}-{digits(rng, 7)}", None),
        "order2": (f"{rng.choice(['WX', 'NW', 'A', 'CT'])}-{digits(rng, 7)}", None),
        "ticket": (f"TCK-{digits(rng, 7)}", None), "case": (f"CASE-{digits(rng, 6)}", None),
        "claim": (f"CLM-{digits(rng, 8)}", None), "booking": (letters(rng, 6, ALNUM), None),
        "invoice": (f"INV-2026-{digits(rng, 5)}", None), "tracking": (f"1Z{letters(rng, 3)}{digits(rng, 13)}", None),
        "flight": (f"{rng.choice(['UA', 'DL', 'AA', 'BA', 'LH', 'AF'])} {rng.randint(100, 2999)}", None),
        "flight2": (f"{rng.choice(['UA', 'DL', 'AA', 'BA', 'LH', 'AF'])} {rng.randint(100, 2999)}", None),
        "amount": (amount(rng), None), "amount2": (amount(rng), None),
        "day": (someday(rng), None), "day2": (someday(rng), None),
        "time": (rng.choice(["9:15 am", "10:30 am", "11:45 am", "1:00 pm", "2:20 pm", "3:30 pm", "4:45 pm"]), None),
        "city": (rng.choice(CITIES)[0], None),
    }


# A chat is beats: a few lines each, "C:" for the customer and "A:" for the agent, with {slots} filled in.
ANY = [
    ["A: Thanks, give me a moment to pull that up.", "C: Sure, take your time."],
    ["A: I'm still looking into this, thank you for your patience.", "C: No problem."],
    ["C: Sorry, are you still there?", "A: Yes, I'm here! The system is a little slow today."],
    ["A: One moment while I check with my team lead.", "C: Okay.", "A: Thanks for holding, I'm back."],
    ["C: Sorry, my dog is barking at the mail carrier.", "A: Ha, no worries at all!"],
    ["C: I've been trying to sort this out since {day}.", "A: I'm sorry it's taken so long. Let's fix it today."],
    ["C: The weather in {city} has been awful this week.", "A: I've heard that a lot today! Hopefully it clears up."],
]
CLOSE = [
    ["A: Is there anything else I can help with, {first}?", "C: No, that's all. Thanks {agent}!",
     "A: You're welcome. Have a great day!"],
    ["C: That's everything, thanks so much.", "A: Happy to help! You'll get a summary of this chat at {email}."],
    ["A: Anything else today?", "C: Nope. Thanks for your help, {agent}.", "A: Anytime, {first}. Take care!"],
]

DOMAINS = {
    "bank": {
        "company": "Northwind Bank", "slug": "northwind", "products": ["Everyday Checking", "Platinum Rewards card"],
        "open": [
            ["C: Hi, I need help with my account.",
             "A: Hi, thanks for contacting {company}, my name is {agent}. Who am I speaking with?",
             "C: This is {name}."],
            ["C: Hello? Is this {company} support?", "A: It is! I'm {agent}. How can I help you today?",
             "C: Hi {agent}, my name is {name} and I have a problem with my card."],
        ],
        "verify": [
            ["A: Before we start, can you confirm your date of birth and the phone number on the account?",
             "C: Sure, it's {dob}, and the phone is {phone}.", "A: Thank you, {first}. You're verified."],
            ["A: For security, I need the last four of your Social Security number.",
             "C: Here's the whole thing so we don't go back and forth: {ssn}.",
             "A: Thanks, I only needed the last four, but you're verified. Please don't share the full number in "
             "chat."],
            ["A: I've just sent a one-time code to your phone. Can you read it back to me?", "C: It says {otp}.",
             "A: Perfect, that matches."],
        ],
        "middle": [
            ["C: I lost my debit card yesterday, I think at the {city} farmers market.",
             "A: I'm sorry to hear that. Is it the card ending in {last4}?",
             "C: Yes. The full number is {card} if that helps.",
             "A: Thanks. I've blocked it, and a new one will go to {address}. Is that still your address?",
             "C: Yes, that's right."],
            ["C: There's a charge for {amount} on {day} that I didn't make.",
             "A: I see it, from an online store. I've opened dispute {case} for you.",
             "C: Thank you. Will I get the money back?", "A: You'll get a provisional credit within 2 business days."],
            ["C: I need to send a wire to my landlord in Germany.",
             "A: I can help. What's the recipient's name and IBAN?", "C: It's {relative}, IBAN {iban}.",
             "A: And which account should it come from?", "C: My checking, account number {account}.",
             "A: Got it. A wire of {amount2} will go out on {day2}."],
            ["C: Can you also update my email? The new one is {email}.",
             "A: Done. I've also added {phone2} as a backup number, like you asked last time. Is that right?",
             "C: Yes, that's my work phone."],
            ["A: One more security question: what was your first pet's name?", "C: {answer}.", "A: Thank you."],
            ["C: I also got locked out of online banking. I typed {password} like five times.",
             "A: Please don't share your password with anyone, me included. I've sent a reset link to {email}.",
             "C: Oops, sorry. Got the link."],
            ["C: Here's what my statement says:\n"
             "    {day}   POS PURCHASE   GROCERY OUTLET   {amount}\n"
             "    {day2}   ONLINE TRANSFER TO {relative}   {amount2}\n"
             "    ACCOUNT HOLDER: {name}\n    ACCOUNT NUMBER: {account}\n    MAILING ADDRESS: {address}",
             "A: Thanks, that helps. The transfer to {relative_first} went through on {day2}."],
        ],
    },
    "telecom": {
        "company": "Contoso Mobile", "slug": "contoso", "products": ["Nimbus X2 phone", "Aero 5G hotspot"],
        "open": [
            ["C: Hi, I want to move my number to another carrier.",
             "A: Hi, I'm {agent} with {company}. I can help with that. What's the name on the account?", "C: {name}."],
            ["A: Welcome to {company} chat, I'm {agent}. What can I do for you?",
             "C: Hi {agent}, I'm {name}. My bill is way higher than usual."],
        ],
        "verify": [
            ["A: Can you give me your account number and the account PIN?", "C: Account {customer}, PIN {pin}.",
             "A: Thanks, you're verified."],
            ["A: What's the mobile number on the account?",
             "C: {phone}. My husband {relative_first} also has a line on it, {phone2}.",
             "A: Got it, I see both lines."],
        ],
        "middle": [
            ["C: My bill this month was {amount}, it's usually {amount2}.",
             "A: I see international roaming charges from {day}. Were you traveling?",
             "C: Yes, I flew {flight} to Toronto.", "A: I can credit half of the roaming charges as a courtesy."],
            ["A: To move your number you'll need your account number, {customer}, and a transfer PIN. "
             "Your transfer PIN is {otp}.", "C: Thanks, writing that down.", "A: It's valid for 7 days."],
            ["C: I also ordered a {product} last week, order {order}, but it hasn't arrived.",
             "A: It shipped on {day} with tracking number {tracking}. It's going to {address}.",
             "C: Oh, that's my old address! I moved to {address2}.",
             "A: I'll ask the carrier to send it to {address2} instead."],
            ["C: Can I add a line for my daughter, {relative}?",
             "A: Sure. She'll need to be at least 13. How old is she?", "C: She turns 16 next month.",
             "A: Great, I've added the line. Her new number will be {phone2}."],
            ["A: Where should we send the e-bill?", "C: To {email}, please.", "A: Done."],
            ["A: For Wi-Fi calling I need an emergency address.", "C: Use {address}.", "A: Saved."],
        ],
    },
    "clinic": {
        "company": "Fabrikam Health", "slug": "fabrikam", "products": ["patient portal"],
        "open": [
            ["C: Hi, I'd like to reschedule my appointment.",
             "A: Hello, this is {agent} at {company} patient services. May I have the patient's full name and date "
             "of birth?", "C: {name}, born {dob}."],
            ["A: Thanks for contacting {company}, I'm {agent}. Who's the patient today?",
             "C: It's me, {name}. My birthday is {dob}."],
        ],
        "verify": [
            ["A: Thank you. Can you confirm your medical record number? It's on your visit summary.",
             "C: It says MRN {mrn}.", "A: Great, I found your chart."],
            ["A: And what's your insurance member ID?", "C: {member}.", "A: Thanks, your coverage is active."],
        ],
        "middle": [
            ["A: I see your follow-up on {day} at {time} with Dr. {doctor}. When would work better?",
             "C: Anything the week after, ideally in the morning.",
             "A: I have {day2} at {time} with Dr. {doctor}. Does that work?", "C: Perfect."],
            ["A: I'd also like to update your emergency contact. Who should we list?",
             "C: My sister, {relative}. Her number is {phone2}.", "A: Thank you, I've added her."],
            ["C: Can you send my refill to the pharmacy on Main Street in {city}?",
             "A: Sure, it'll be ready after 2 pm on {day2}.", "C: Thanks."],
            ["C: I can't log in to the patient portal. My username is {email}.",
             "A: I've sent a reset link there. It expires in an hour.", "C: Got it."],
            ["C: I also got a bill for {amount} from my visit on {day}.",
             "A: That's your copay. You can pay it online with invoice {invoice}.",
             "C: Okay, can I just give you my card? It's {card}.",
             "A: Please don't share card numbers in chat; you can pay securely in the portal."],
            ["C: Here's the intake form I filled out:\nPatient name: {name}\nDate of birth: {dob}\n"
             "Address: {address}\nPhone: {phone}\nInsurance member ID: {member}\nEmergency contact: {relative}, "
             "{phone2}", "A: Thanks, I've attached it to your chart."],
        ],
    },
    "hr": {
        "company": "Adatum Corporation", "slug": "adatum", "products": ["benefits portal"],
        "open": [
            ["C: Hi, I'm starting next week and I have questions about onboarding.",
             "A: Welcome to {company}! I'm {agent} from the People team. What's your name?",
             "C: {name}. My start date is {day}."],
            ["A: Hi, this is {agent} with {company} People Operations. How can I help?",
             "C: Hi! I'm {name}, a new hire on the data team."],
        ],
        "verify": [
            ["A: Thanks {first}. Your employee ID is {employee}; you'll use it to sign in to the benefits portal.",
             "C: Great, thanks."],
            ["A: Can you confirm your personal email?", "C: It's {email}.", "A: Perfect, that's what we have."],
        ],
        "middle": [
            ["A: For payroll, please enter your SSN in the secure form rather than here.",
             "C: Oh, I already typed it in the form, it's {ssn}.",
             "A: Got it, but please only use the form next time."],
            ["C: For direct deposit, my account number is {account}.",
             "A: Thanks. Please also upload a voided check so we can confirm it.", "C: Will do."],
            ["A: What home address should go on your W-4?", "C: {address}.",
             "A: Thanks. Your first paycheck of {amount} will arrive on {day2}."],
            ["A: Who should we list as your emergency contact?", "C: My partner, {relative}, {phone2}.",
             "A: Added."],
            ["A: IT will ship your laptop with tracking {tracking}. Is {address} the right place?",
             "C: Actually, please send it to my parents' place, {address2}.", "A: Done."],
            ["C: For the I-9, can I use my passport? The number is {passport}.",
             "A: Yes, a passport works. Bring it on your first day; you don't need to send the number here.",
             "C: Okay."],
            ["C: My offer letter says:\nDear {name},\nWe're pleased to offer you the position of Data Analyst at "
             "{company}, starting {day}, at an annual salary of {amount}. Please reply to {email2} with any "
             "questions.\nSincerely,\n{colleague}, Talent Acquisition",
             "A: That's right, {colleague} is your recruiter."],
        ],
    },
    "travel": {
        "company": "Margie's Travel", "slug": "margies", "products": ["flex fare"],
        "open": [
            ["C: Hi, I need to change a flight.",
             "A: Hi, I'm {agent} with {company}. Do you have your booking reference?",
             "C: Yes, it's {booking}. The booking is under {name}."],
            ["A: Thanks for choosing {company}, this is {agent}. How can I help?",
             "C: Hi, I'm {name}. I booked a trip last week and need to make some changes."],
        ],
        "verify": [
            ["A: Thanks. Can you confirm the email on the booking?", "C: {email}.", "A: Got it."],
            ["A: And your frequent flyer number, so the miles post?", "C: {frequent}.", "A: Added."],
        ],
        "middle": [
            ["C: I'm on {flight} on {day}, but I need to leave a day later.",
             "A: I can move you to {flight2} on {day2} at {time}. The fare difference is {amount}.",
             "C: That's fine."],
            ["A: For the international leg, I need your passport details.",
             "C: Passport number {passport}, date of birth {dob}.", "A: Thanks, I've added them to the booking."],
            ["C: My husband {relative} is traveling with me. His passport is {passport2}.",
             "A: Thanks. Do you want seats together?", "C: Yes please."],
            ["A: How would you like to pay the difference?", "C: Card {card}, CVV {cvv}.",
             "A: Thank you, the payment went through. The receipt is on its way to {email}."],
            ["C: Can you also add a hotel in {city} for two nights?",
             "A: Sure. I found one downtown for {amount2} a night. Your confirmation number is {invoice}.",
             "C: Great."],
            ["C: Here's the itinerary email:\nPassenger: {name_caps}\nBooking reference: {booking}\n"
             "{day}  {flight}  departs 7:05 am\n{day2}  {flight2}  departs 6:40 pm\nFrequent flyer: {frequent}\n"
             "Contact: {phone} / {email}", "A: Thanks, I see the same booking."],
        ],
    },
    "insurance": {
        "company": "Litware Insurance", "slug": "litware", "products": ["auto policy"],
        "open": [
            ["C: Hi, I need to file a claim. Someone rear-ended me.",
             "A: I'm sorry to hear that. I'm {agent} with {company}. Is everyone okay?",
             "C: Yes, just shaken up. My name is {name}."],
            ["A: You've reached {company} claims, this is {agent}.",
             "C: Hi {agent}, I'm {name}. I was in a fender bender this morning."],
        ],
        "verify": [
            ["A: Can I have your policy number?", "C: It's {policy}.", "A: Thank you, I see your auto policy."],
            ["A: And your driver's license number?", "C: {license}.", "A: Thanks."],
        ],
        "middle": [
            ["A: I've opened claim {claim} for the accident on {day}.", "C: Thanks. What happens next?",
             "A: An adjuster will call you at {phone} within 2 business days."],
            ["A: Which vehicle was involved?", "C: My sedan, plate {plate}, VIN {vin}.", "A: Got it."],
            ["A: Do you have the other driver's information?",
             "C: Yes, her name is {relative}, phone {phone2}, and her policy number is {policy2}.",
             "A: Thank you, that's very helpful."],
            ["C: Can I take the car to my usual body shop?",
             "A: Yes. Their estimate of {amount} is under review against your deductible."],
            ["A: Your policy covers a rental for up to {amount2} a day.",
             "C: Great, I'll pick one up near my house, {address}.", "A: Okay, noted."],
            ["A: Where should we send the claim payment?", "C: Direct deposit to account {account}, please.",
             "A: Noted."],
            ["C: The police report says:\nReport number: {case}\nDriver 1: {name}, DOB {dob}, license {license}\n"
             "Driver 2: {relative}, phone {phone2}\nLocation: Highway 9 near exit 14\nDate: {day}",
             "A: Thanks, I've added the report to claim {claim}."],
        ],
    },
    "it": {
        "company": "Woodgrove IT Service Desk", "slug": "woodgrove", "products": ["VPN client"],
        "open": [
            ["C: Hi, I can't connect to the VPN since this morning.",
             "A: Hi, I'm {agent} from the {company}. I've opened ticket {ticket}. Can I get your name and "
             "employee ID?", "C: {name}, employee ID {employee}."],
            ["A: {company}, this is {agent}. What's going on?",
             "C: Hi, it's {name}. My account got locked again."],
        ],
        "verify": [
            ["A: What's your work email?", "C: {email2}.", "A: Thanks."],
            ["A: Can you confirm your employee ID?", "C: {employee}.", "A: Got it."],
        ],
        "middle": [
            ["C: I reset my password and now it says it's wrong. The new one is {password}.",
             "A: Please don't post passwords in chat; I'll force a reset. You'll get a code by text at {phone}.",
             "C: Okay, I got the code: {otp}.", "A: Thanks, you're all set."],
            ["C: Here's the error log:\n{day} 08:02:11 vpn-gw01 auth failed for {email2} from {ip}\n"
             "{day} 08:02:45 vpn-gw01 auth failed for {email2} from {ip}\n"
             "{day} 08:05:12 vpn-gw01 session opened for {email2} from {ip2}\n"
             "{day} 08:05:13 vpn-gw01 client version 5.2.1",
             "A: Thanks. {ip2} is your home router, so that one's expected. I'll look into {ip}."],
            ["C: Also, I accidentally pasted our test API key in a public channel: {api_key}",
             "A: Thanks for telling us. I've revoked {api_key} and put a new one in the vault.", "C: Phew, thanks."],
            ["A: Your replacement laptop ships today with tracking {tracking}. Should it go to {address}?",
             "C: Yes, that's my home address.", "A: Great."],
            ["A: Should I update your MFA phone to {phone2}?", "C: Yes, that's my new cell.", "A: Done."],
            ["A: I need your manager's approval for admin rights. Who's your manager?", "C: {colleague}.",
             "A: I've sent {colleague} an approval request."],
        ],
    },
    "shop": {
        "company": "Wide World Importers", "slug": "wideworld", "products": ["Aurora desk lamp", "Terra rug"],
        "open": [
            ["C: Hi, I want to return something.", "A: Hi! I'm {agent} from {company}. What's the order number?",
             "C: It's {order}. The order is under {name}."],
            ["A: Welcome to {company} support, I'm {agent}.",
             "C: Hi {agent}, this is {name}. I have a problem with an order."],
        ],
        "verify": [
            ["A: Can you confirm the email on the order?", "C: {email}.", "A: Thanks, I found it."],
            ["A: And the phone number on the order?", "C: {phone}.", "A: Got it."],
        ],
        "middle": [
            ["C: The {product} arrived broken.",
             "A: I'm sorry! I've created return {case}. A prepaid label will go to {email}.", "C: Thank you."],
            ["A: The refund of {amount} will go back to the card ending in {last4}.",
             "C: Great, how long does that take?", "A: 3 to 5 business days."],
            ["C: I also want to send a gift to my friend {relative} at {address2}.",
             "A: Sure. Do you want a gift message?", "C: Yes: Happy birthday, {relative_first}!", "A: Added."],
            ["C: Please change my shipping address to {address}.",
             "A: Done. Your next order, {order2}, will ship there.", "C: Thanks."],
            ["C: My other order, {order2}, says delivered but I never got it.",
             "A: The carrier marked it delivered on {day} at {time}. Tracking {tracking}.",
             "C: I was home all day!", "A: I'll file a claim with the carrier and call you at {phone} with an update."],
            ["C: Can I pay the difference with a new card? {card}, expires 09/29, CVV {cvv}.",
             "A: Thanks, the payment went through. For your safety, please don't share card details in chat."],
        ],
    },
}


class Chat:
    """A chat transcript as it's written, with where each piece of PII is."""

    def __init__(self, rng: random.Random):
        self.rng, self.parts, self.pii, self.size, self.minute = rng, [], [], 0, rng.randint(8 * 60, 17 * 60)

    def write(self, text: str, kind: str | None = None) -> None:
        if kind:
            self.pii.append({"type": kind, "value": text, "start": self.size, "end": self.size + len(text)})
        self.parts.append(text)
        self.size += len(text)

    def say(self, who: str, template: str, slots: dict) -> None:
        self.minute += self.rng.choice([0, 0, 1, 1, 2, 3])
        self.write(f"[{self.minute // 60 % 24:02d}:{self.minute % 60:02d}] {who}: ")
        for piece in re.split(r"(\{\w+\})", template):
            slot = re.fullmatch(r"\{(\w+)\}", piece)
            if slot:
                self.write(*slots[slot.group(1)])
            elif piece:
                self.write(piece)
        self.write("\n")


def conversation(rng: random.Random, key: str, index: int) -> dict:
    domain = DOMAINS[key]
    who = person(rng, domain)
    chat = Chat(rng)
    for number in range(rng.choice([1, 2, 2, 3, 3, 4])):
        slots = {**who, **session(rng, who["first"][0])}
        chat.minute = rng.randint(8 * 60, 17 * 60)
        chat.write(f"{'' if number == 0 else chr(10)}--- Chat with {domain['company']}, ")
        chat.write(*slots["day"])
        chat.write(" ---\n")
        middle = rng.sample(domain["middle"], rng.randint(4, len(domain["middle"])))
        body = middle + rng.sample(ANY, rng.randint(2, 4))
        rng.shuffle(body)
        for beat in [rng.choice(domain["open"]), rng.choice(domain["verify"]), *body, rng.choice(CLOSE)]:
            for line in beat:
                speaker, template = line.split(": ", 1)
                chat.say("Customer" if speaker == "C" else "Agent", template, slots)
    text = "".join(chat.parts)
    assert all(text[p["start"]:p["end"]] == p["value"] for p in chat.pii)
    return {"id": f"chat-{index:03d}", "domain": key, "text": text, "pii": chat.pii}


def main() -> None:
    parser = argparse.ArgumentParser(description="Write made-up support chats with their PII marked.")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--test", type=int, default=20, help="how many of them to hold out for score.py")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    keys = list(DOMAINS)
    chats = [conversation(rng, keys[i % len(keys)], i + 1) for i in range(args.count)]
    held = HERE / "samples" / "test"
    held.mkdir(parents=True, exist_ok=True)
    for path, rows in ((HERE / "samples" / "conversations.jsonl", chats[:-args.test]),
                       (held / "conversations.jsonl", chats[-args.test:])):
        path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
        sizes = sorted(len(row["text"]) for row in rows)
        print(f"{path.relative_to(HERE)}: {len(rows)} chats, {sizes[0]:,}-{sizes[-1]:,} characters, "
              f"{sum(len(row['pii']) for row in rows):,} pieces of PII")
    (held / "chat.txt").write_text(chats[-args.test]["text"])


if __name__ == "__main__":
    main()
