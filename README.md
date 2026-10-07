# Campus Customs — Shop + AI Chatbot

A customer website for **Campus Customs** (officially licensed Yale apparel, 57 Broadway, New Haven) with a shopping assistant that answers honestly about price and stock from a local database.

- **Front end:** React + Vite + TypeScript (`frontend/`). Browse products, single-item pages, create an account / log in, and a floating chat whose search results appear as product cards on the page.
- **Back end:** Python FastAPI (`backend/main.py`) whose brain is a **PydanticAI** agent (`gpt-5.6-luna` via Portkey) with tools that query SQLite for descriptions, prices, and stock by size.

> MGT 409 · HW4. Full technical documentation: [`output/harness.md`](output/harness.md). Grader screenshots: open [`output/app_check.html`](output/app_check.html).

---

## 1. Put the data pack in place

The database and product images are **not** in this repo. Unzip the course data pack into `hw4/` so you have:

```
hw4/
└── data/
    ├── campus_customs.db     # SQLite: catalogue, inventory, users, chat_messages
    └── products/             # product images (paths match the catalogue table)
```

## 2. Add your API key

```bash
cp .env.example .env
# edit .env and set PORTKEY_API_KEY=<your Portkey key>
```

`.env` is gitignored. The backend also accepts `PORTKEY_API_KEY` exported in your shell.

## 3. Run the back end (terminal 1)

Requires Python 3.12+.

```bash
cd hw4
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cd backend
uvicorn main:app --reload --port 8000
```

Check it: <http://localhost:8000/api/health> → `{"status":"ok","chat_model":"gpt-5.6-luna"}`

## 4. Run the front end (terminal 2)

Requires Node 20+.

```bash
cd hw4/frontend
npm install
npm run dev
```

Open **<http://localhost:5173>**. The Vite dev server forwards `/api` and `/static` requests to the backend on port 8000.

**Try it:**
- **Shop:** filter by category, search (typos like `saybrok` work), open any product.
- **Chat:** ask *"What hoodies do you have?"* and cards appear on the page. On an item page ask *"Do you have this in XL?"*
- **Account:** log in with the seed user `test@campuscustoms.yale.edu` / `password`, or create a new account. Logged-in chats are saved and reload when you come back.

Stop each server with **Ctrl+C**. Before restarting, make sure nothing is still on port 8000 (`lsof -ti :8000`).

## Tests (optional)

```bash
cd hw4/backend
python -m pytest tests -q        # 134 tests; no AI calls
```

To see the AI-outage fallback, start the back end with `CHAT_SIMULATE_OUTAGE=1 uvicorn main:app --port 8000`.

---

## Project structure

```
hw4/
├── AI_prompts.md             # prompts used for each problem
├── README.md
├── requirements.txt          # backend Python dependencies
├── .env.example              # copy to .env and add your key
├── .gitignore                # keeps .env, data/, the database, and images out of git
├── frontend/                 # Vite React TypeScript app
│   └── src/                  # pages/, components/, api.ts, auth.tsx, chatResults.tsx, index.css
├── backend/
│   ├── main.py               # FastAPI app — run with: uvicorn main:app --reload --port 8000
│   ├── agent.py              # PydanticAI agent: model, instructions, validators, fallback, audit
│   ├── models.py             # Pydantic types: tool results, chat API, cards, audit entries
│   ├── tools.py              # agent tools + SQLite access, fuzzy search, chat memory
│   ├── auth.py               # sign up / log in (Argon2id), session tokens
│   ├── audit.py              # append-only audit trail + PII redaction
│   ├── prompts/
│   │   └── prompt.md         # system prompt: store voice, tool rules, safety rules
│   └── tests/                # pytest suite
└── output/
    ├── harness.md            # full documentation (schema, auth, agent, tools, models, safety, specs)
    ├── design.md             # styling decisions
    ├── usability.md          # usability improvements
    ├── app_check.html        # grader page (double-click to open)
    ├── app_check_images/     # screenshots linked from app_check.html
    └── audit_trail.json      # append-only log of agent activity
```

Not committed (local only): `data/`, `data.zip`, `.env`, `.venv/`, `frontend/node_modules/`, `frontend/dist/`.
