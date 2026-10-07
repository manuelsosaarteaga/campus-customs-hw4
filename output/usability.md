# Usability Improvements — Campus Customs

Four upgrades: two in the front end, two in the agent/backend. Each one is visible on the running site (see "How to see it").

| # | Improvement | Layer |
|---|---|---|
| 1 | Context-aware quick-reply buttons in the chat | Front end |
| 2 | Stock badges on every product card | Front end |
| 3 | Typo-tolerant (fuzzy) product search | Agent / backend |
| 4 | Graceful failure: retries, DB fallback results, and a "Try again" button | Agent / backend |

(Already in place from earlier problems and not counted here: chat auto-scroll and the typing indicator.)

---

## 1. Quick-reply buttons (front end)

**What we added**
- A row of tappable suggestion chips above the chat input. Clicking one sends it as a message.
- The chips change with context:
  - **On an item page:** "Is this in stock in M?", "What colors does it come in?", "Show me similar items".
  - **Anywhere else, at the start of a chat:** "What hoodies do you have?", "Gifts under $40", "Residential college gear", "Harvard–Yale game gear".
  - **After the assistant shows products:** "Anything cheaper?", "Show me navy options", "Which are in stock in L?".

**Why it helps**
- **Shopper:** removes the blank-box problem. New visitors immediately see what the assistant can do, and phone users can ask common questions without typing.
- **Business:** more shoppers start a conversation, and the suggestions steer them toward questions the agent answers well (category browsing, stock checks), which leads into product pages and purchases.

## 2. Stock badges on product cards (front end)

**What we added**
- Every product card (the Products grid, the Home "Layer up" row, and the "From your chat" cards) shows a badge from live inventory:
  - **"Sold out"** when no size is available.
  - **"Only N sizes left"** when just 1–3 of the 6 sizes are in stock (21 of the 102 products right now).
- `GET /api/products` now includes a stock summary per product, computed in one grouped SQL query.

**Why it helps**
- **Shopper:** availability shows up before clicking, so nobody falls for an item that isn't in their size. The badge is honest because it comes straight from the `inventory` table.
- **Business:** fewer dead-end clicks and support questions ("is this in stock?"). Truthful scarcity cues ("Only 2 sizes left") can also prompt a decision without fake urgency.

## 3. Typo-tolerant (fuzzy) search (agent / backend)

**What we added**
- `search_catalogue` in `backend/tools.py` now corrects misspelled words. Any query word that appears nowhere in the catalogue is matched against a vocabulary built from every product's name, tags, garment type, colors, and description, using `difflib` (similarity ≥ 0.8). Examples: "crewnek" → "crewneck", "Brnaford" → "Branford", "lacrose" → "lacrosse".
- Search results include `corrections` (e.g. `{"crewnek": "crewneck"}`), so the agent can say "Showing results for *crewneck*".
- The **Products page search box** now uses the same backend search (`GET /api/products?q=…`), so typos work there too, and it shows "Showing results for …" when it corrected something.

**Why it helps**
- **Shopper:** college and brand names (Berkeley, Branford, Saybrook) are easy to misspell, especially on a phone. They now get results instead of "no matches".
- **Business:** a zero-result search is a lost sale. Fixing typos keeps shoppers in the catalogue, and chat and the search box now find the same products.

## 4. Graceful failure with DB fallback (agent / backend)

**What we added**
- **Bounded waits:** the AI client has a 45-second timeout, so a hung request can't spin forever.
- **Automatic retry:** transient AI errors (rate limit, 5xx, timeout, connection drop) are retried up to 2 times with exponential backoff (OpenAI SDK `max_retries=2`, configured in `agent.py`).
- **Fallback answer instead of an error:** if the agent still fails, or gets stuck (e.g. exhausts its retries), the backend answers with a plain database search on the shopper's message. It returns real matching product cards plus an honest note ("Our assistant is having a moment, but here are items matching your question"), marked `degraded: true`. These turns aren't saved to history, so retrying doesn't duplicate them.
- **"Try again" button:** degraded replies and network errors show a button in the chat that resends the shopper's last message.
- For demos and grading, `CHAT_SIMULATE_OUTAGE=1` makes the agent fail on purpose so the fallback can be seen.

**Why it helps**
- **Shopper:** never a dead end or a cryptic error. Even during an AI outage they still see relevant products and can retry with one click.
- **Business:** the storefront keeps selling when the AI provider has problems, and support burden stays low. Blocked or broken turns also never pollute saved history.

---

## How to see it (running site)

Start the backend (`cd backend && uvicorn main:app --reload --port 8000`) and the frontend (`cd frontend && npm run dev`), then open http://localhost:5173.

| # | Try this |
|---|---|
| 1 | Open the chat on Home → starter chips. Click "What hoodies do you have?" → after the reply, follow-up chips appear. Open any item page → item chips ("Is this in stock in M?"). |
| 2 | Products page → "Only N sizes left" badges (e.g. Champion Reverse Weave Crewneck: "Only 2 sizes left"). The same badges show on the Home row and the chat result cards. |
| 3 | Products search box: type `saybrok`, `crewnek`, or `brnaford` → results + "Showing results for …". In chat: "show me crewnek sweatshirts from saybrok college". |
| 4 | Restart the backend with `CHAT_SIMULATE_OUTAGE=1 uvicorn main:app --port 8000`, then ask "navy hoodies" → fallback note + real product cards + "Try again" button. Restart without the variable to go back to normal. |

## Verification

Everything below was run against the live site (backend on :8000, Vite on :5173). The browser checks used headless Chrome.

| # | Check | Result |
|---|---|---|
| 1 | Open chat on Home | Starter chips: "What hoodies do you have?", "Gifts under $40", "Residential college gear", "Harvard–Yale game gear" |
| 1 | Click "What hoodies do you have?" | Sent as a message → 12 hoodie cards on the page → follow-up chips "Anything cheaper?", "Show me navy options", "Which are in stock in L?" |
| 1 | Click a card → item page | Item chips: "Is this in stock in M?", "What colors does it come in?", "Show me similar items" |
| 2 | `GET /api/products` | All 102 products carry `available_sizes`, `low_stock_sizes`, `in_stock`; 21 have 1–3 sizes left, 0 fully sold out (matches SQL) |
| 2 | Products grid | 21 cards show a badge, e.g. "Champion Reverse Weave Crewneck: Only 2 sizes left" (DB: only M and XL in stock), "Brooks Brothers Bomber Jacket Yale: Only 3 sizes left" |
| 2 | Chat result cards ("What hoodies…") | Badges appear on the hoodies with 3 sizes left |
| 3 | `GET /api/search?q=crewnek` / `brnaford` / `nvy hoody` / `xyzzy` | → `crewneck` (29 items) / `branford` (Branford 1 4 Zip) / `navy`+`hood` / no matches, no false correction |
| 3 | Products search box: "saybrok" | "Showing results for **saybrook** · you typed 'saybrok'" → the 3 Saybrook items |
| 3 | Chat: "show me crewnek sweatshirts from saybrok college" | `search_products` → "Showing results for 'Saybrook' (corrected from 'saybrok')…" + Saybrook College Crewneck card, $58.00 |
| 3 | `backend/tests/test_tools.py` | 126 tests pass (8 new fuzzy tests: 5 typo corrections, corrected filters, no change to correct words, gibberish finds nothing) |
| 4 | `CHAT_SIMULATE_OUTAGE=1`: "do you have navy hoodies?" | HTTP 200, `degraded: true`, amber note + 8 real navy hoodie cards ("Catalogue matches") + "↻ Try again" |
| 4 | Outage, on `/products/fencing-left-chest-hoodie`: "is this in stock?" | Fallback still shows that item's card |
| 4 | Outage, gibberish message | Friendly "try again / browse Products" note, no cards, no error |
| 4 | Outage, logged in | Saved history unchanged (6 → 6): fallback turns aren't stored |
| 4 | Click "Try again" | Resends the same question; only the newest reply keeps a retry button; quick replies hidden on fallback replies |
| 4 | AI client config | `timeout=45s`, `max_retries=2` confirmed on the live `AsyncOpenAI` client |

(The backend was restarted in normal mode afterward and the DB restored to its original state.)
