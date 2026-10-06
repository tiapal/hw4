# Campus Customs

A Yale merch shop with an AI shopping assistant. The website (React) shows the catalogue, product pages, a cart,
and accounts. A small tape-measure chat widget talks to a PydanticAI agent that answers from the shop's database:
price, description, stock by size, sizing advice, and live search results on the Products page.

| | |
|---|---|
| Website | React + Vite + TypeScript, in `frontend/` |
| API and agent | FastAPI + PydanticAI, in `backend/` |
| Model | `gpt-5.6-luna` (OpenAI) through the Portkey gateway |
| Database | SQLite (a local data pack, not in this repository) |

## What's in this repository

```
.
├── AI_prompts.md        # every prompt used to build this, by problem
├── requirements.txt     # Python packages
├── .env.example         # placeholders only: copy to .env and add your own key
├── .gitignore
├── README.md
├── frontend/            # Vite React TypeScript app
├── backend/
│   ├── main.py          # FastAPI app. Run with: uvicorn main:app --reload --port 8000
│   ├── agent.py         # the agent: model, prompt, loop, audit
│   ├── tools.py         # the tools the agent can call
│   ├── models.py        # the typed data the system passes around
│   ├── prompts/
│   │   └── prompt.md    # the agent's instructions and safety rules
│   ├── auth.py          # accounts and sessions (Argon2id password hashes)
│   ├── safety.py        # removes card numbers and passwords from messages
│   ├── audit.py         # append-only audit trail writer
│   └── size_chart.json  # the sizing chart, as data
├── scripts/             # optional helpers (white-background photos, live-site check)
└── output/
    ├── harness.md       # how the whole system works (start here)
    ├── design.md        # the restyle and why
    ├── usability.md     # four usability improvements and why
    ├── app_check.html   # live-site test report (open it in a browser)
    ├── app_check_images/  # screenshots linked from app_check.html
    └── audit_trail.json # append-only record of what the agent did
```

## The data pack (kept on your computer, not in git)

The database and the product photos are not in this repository. Put them here before you run anything:

```
data/
├── campus_customs.db
└── products/            # the product photos named in the catalogue
```

`.env` (your real API key) is also never committed. Only `.env.example` is, and it has placeholders.

Optional: `scripts/whiten_product_photos.py` makes copies of the photos with white backgrounds in
`data/products_white/`. The site uses them automatically when that folder exists, and falls back to `data/products/` when it doesn't.

## Run it

You need Python 3.12 or newer and Node.js. Run these from the top of the repository.

**1. One-time setup**

```bash
python3 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then open .env and replace the placeholder with your PORTKEY_API_KEY

cd frontend && npm install && cd ..
```

**2. Start the back end** (terminal 1). Run it from inside `backend/` so the imports work:

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

**3. Start the front end** (terminal 2):

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173**. The site sends every `/api` request on to the back end on port 8000.

The first time the back end starts it adds a few things to the database (a `sessions` table, an account column, a
`fit` column, an index). Your data is not changed.

## Try these in the chat

- "What hoodies do y'all have?" puts the matching cards on the Products page.
- "How much is the Baseball Left Chest Crewneck, and do you have it in medium?" answers from the database.
- Open a product page and ask "do you have this in pink?"
- "I'm usually a medium, what should I get?" asks which fit you want and checks the size chart and stock.

Create an account to have your chat history saved. Guests can chat, but nothing is saved for them.

## Checks

```bash
cd frontend && npm run build        # type-checks and builds the site
```

`scripts/export_for_github.py` makes a clean copy of the project for publishing when git isn't available, and checks it
for secrets, the database, and product photos before you upload it.

`scripts/app_check.py` drives the live site in a browser and rewrites `output/app_check.html` with screenshots
(needs `pip install playwright` and `python -m playwright install chromium`).

## How it works

Read `output/harness.md`. It covers the database, the model fields, the tools, the safety rules, the limits, and how to run everything.
The safety rules the agent follows are in `backend/prompts/prompt.md`, and `output/audit_trail.json` records what it did.
