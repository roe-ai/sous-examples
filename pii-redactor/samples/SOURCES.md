# Sample documents

Every document here is a specimen: an image an issuer publishes to show what its card looks like, with a sample name
(JANICE SAMPLE, MUSTERFRAU), sample numbers, and a model's photo. None holds a real person's information. They were
collected for a set of ID specimens and scaled down to at most 1024 pixels on a side. Check each publisher's terms
before you redistribute them.

`documents/` holds the 47 the redactor runs on while Sous learns (`collect.py`). `test/documents/` holds 12 more from
other issuers that Sous never sees, for `score.py`.

| File | Document | Published by |
| --- | --- | --- |
| documents/act-learner-licence.jpg | Learner driver licence | Access Canberra |
| documents/alaska-driver-license.jpg | Driver license | Alaska DMV |
| documents/alberta-driver-licence.jpg | Driver's licence | Government of Alberta |
| documents/arizona-driver-license.jpg | Driver license | Arizona MVD |
| documents/arkansas-driver-license.jpg | Driver license | Arkansas DFA |
| documents/belgium-national-id.jpg | Electronic identity card | Belgian FPS Interior (EU Council PRADO) |
| documents/california-driver-license.jpg | Driver license | California DMV |
| documents/connecticut-driver-license.jpg | Driver license | Connecticut DMV |
| documents/dc-driver-license.jpg | Driver license | District of Columbia DMV |
| documents/greece-national-id.jpg | Identity card | Hellenic Police |
| documents/guam-driver-license.jpg | Driver license | Guam DMV |
| documents/idaho-driver-license.jpg | Driver license | Idaho Transportation Department |
| documents/kansas-driver-license.jpg | Driver license | Kansas Department of Revenue |
| documents/kansas-id.jpg | Nondriver identification card | Kansas Department of Revenue |
| documents/kentucky-driver-license.jpg | Driver license | Kentucky Transportation Cabinet |
| documents/louisiana-driver-license.jpg | Personal driver's license | Louisiana Office of Motor Vehicles |
| documents/manitoba-driver-licence.jpg | Driver's licence | Manitoba Public Insurance |
| documents/manitoba-id.jpg | Identification card, photographed | Manitoba Public Insurance |
| documents/maryland-driver-license.jpg | Driver license | Maryland MVA |
| documents/mexico-voter-id.jpg | Voter credential | Instituto Nacional Electoral |
| documents/michigan-driver-license.jpg | Driver license | Michigan Secretary of State |
| documents/minnesota-driver-license.jpg | Driver license | Minnesota Driver and Vehicle Services |
| documents/minnesota-driver-license-under-21.jpg | Driver license, under-21 vertical design | Minnesota Driver and Vehicle Services |
| documents/mississippi-driver-license.jpg | Driver license | Mississippi DPS |
| documents/navajo-nation-id.jpg | Tribal identification card | Navajo Nation |
| documents/nebraska-driver-license.jpg | Driver license | Nebraska DMV |
| documents/nevada-driver-license.jpg | Driver license | Nevada DMV |
| documents/new-brunswick-driver-licence.jpg | Driver's licence | Service New Brunswick |
| documents/new-hampshire-driver-license.jpg | Driver license | New Hampshire DMV |
| documents/new-hampshire-driver-license-2.jpg | Driver license, another design | New Hampshire DMV |
| documents/new-jersey-driver-license.jpg | Driver license | New Jersey MVC |
| documents/north-carolina-driver-license.jpg | Driver license | North Carolina DMV |
| documents/northern-mariana-islands-driver-license.jpg | Driver license | CNMI Bureau of Motor Vehicles |
| documents/nova-scotia-driver-licence.jpg | Driver's licence | Nova Scotia Registry of Motor Vehicles |
| documents/pennsylvania-driver-license.jpg | Driver license | PennDOT |
| documents/puerto-rico-driver-license.jpg | Driver license | Puerto Rico DTOP |
| documents/saskatchewan-driver-licence.jpg | Driver's licence | SGI |
| documents/south-carolina-driver-license.jpg | Driver license | South Carolina DMV |
| documents/spain-national-id.jpg | DNI identity card | Spanish National Police (EU Council PRADO) |
| documents/tennessee-driver-license.jpg | Driver license | Tennessee Department of Safety |
| documents/us-employment-authorization-card.jpg | Employment authorization card | USCIS |
| documents/us-permanent-resident-card.jpg | Permanent resident card | USCIS |
| documents/us-virgin-islands-driver-license.jpg | Driver license | USVI Bureau of Motor Vehicles |
| documents/vermont-driver-privilege-card.jpg | Driver privilege card | Vermont DMV |
| documents/virginia-driver-license.jpg | Driver license | Virginia DMV |
| documents/washington-driver-license.jpg | Driver license | Washington DOL |
| documents/west-virginia-driver-license.jpg | Driver license | West Virginia DMV |
| test/documents/argentina-national-id.jpg | DNI identity card | RENAPER |
| test/documents/austria-national-id.jpg | Identity card | Republic of Austria (EU Council PRADO) |
| test/documents/canada-passport.jpg | Passport | Immigration, Refugees and Citizenship Canada |
| test/documents/colorado-driver-license.jpg | Driver license | Colorado DMV |
| test/documents/croatia-id.jpg | Identity card | Croatian Ministry of the Interior |
| test/documents/israel-id.jpg | Biometric identity card | Population and Immigration Authority |
| test/documents/lithuania-id.jpg | Identity card | Migration Department of Lithuania |
| test/documents/massachusetts-id.jpg | Identification card | Massachusetts RMV |
| test/documents/missouri-driver-license.jpg | Driver license | Missouri Department of Revenue |
| test/documents/rhode-island-driver-license.jpg | Driver license | Rhode Island DMV |
| test/documents/utah-driver-license.jpg | Driver license | Utah Driver License Division |
| test/documents/vermont-id.jpg | Non-driver identification card | Vermont DMV |

The chats in `conversations.jsonl` and `test/conversations.jsonl` are made up by `make_conversations.py`; see its
docstring for how each value is kept fake.
