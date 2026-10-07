# AI Prompts Log — Campus Customs (HW4)

> **Reminder:** Update this file after every problem. Paste the exact prompt you typed (in your own words — no page URLs, no screenshots of the problems). If the first prompt didn't get it done, add the follow-up prompt and one sentence on what was missing.

---

## Problem 1

### 1. Problem number and name
Problem 1 — Vibe coder prompts

### 2. Prompt
> yo whats up, i need to start this hw assignment. can u help me make a log file called AI_prompts.md in the main folder? we're working on problem 1 from the assignment. this problem should be called "Vibe coder prompts".
>
> i need it set up to log all the stuff i type to u while working on this. make sections for Problems 1 thru 13. for each prob, put subheadings for:
> 1. problem number and name
> 2. at least one prompt i typed (in my own words)
> 3. a follow up prompt if i needed one, plus 1 sentence on what was missing after the 1st one
>
> also put a quick reminder note at the top so i dont forget to keep updating it as we go along. thanks!

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 2

### 1. Problem number and name
Problem 2 — Analyze the database

### 2. Prompt
> hey, we're on problem 2 now, "Analyze the database". take a look at the sqlite db at data/campus_customs.db. check out all the tables, specially catalogue, inventory, and users.
>
> then start a new file called output/harness.md and break down the schema for me:
> 1. list every table and all its columns/fields
> 2. write 1 short line for each field explaining why it matters for the shop or chatbot
> 3. leave some blank sections at the bottom of output/harness.md for Models, Tools, Safety, and Specs since we gotta fill those in later
>
> make sure everything is clear n accurate!

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 3

### 1. Problem number and name
Problem 3 — Build the Campus Customs website

### 2. Prompt
> yo! moving on to problem 3, "Build the Campus Customs website". help me set up a react front end with vite and typescript in a folder called frontend/ for this store "Campus Customs".
>
> heres what i need on it:
> 1. top nav bar with links to: Home, Products, About Us, Log in, Create account
> 2. home & about pages: write some cool text inspired by yalebulldogblue.com, but write it in our own voice (dont just copy paste the site text)
> 3. products page: show a grid of product cards with images from the db (use the image paths in the db), basic info like name, price, short description
> 4. single item page: clicking a product card should open a page for just that item, big image on one side and full info on the other (description, price, sizes/stock if we have it)
> 5. chat widget: put a floating chat panel in the bottom right corner. it can just be a stub for now that doesn't fully work yet
> 6. simple backend: start a basic fastapi app in backend/main.py just to serve images and fetch products from data/campus_customs.db for the front end
>
> lets get this running, thx!

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 4

### 1. Problem number and name
Problem 4 — Create account and login

### 2. Prompt
> okay now we're doing problem 4, "Create account and login". i need a normal account creation and login setup connected to data/campus_customs.db.
>
> front end stuff:
> - create account form: first name, last name, email, password, and confirm password
> - login form: email and password
>
> back end stuff:
> - save new users into the users table
> - hash the passwords securely (use bcrypt or argon2 or whatever passlib stuff) so passwords arent stored in plain text!! very important
>
> also test if it works with the seed test user: test@campuscustoms.yale.edu with password "password". make sure that one works and a new account works too.
>
> then update output/harness.md explaining how auth works and how we protect passwords.

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 5

### 1. Problem number and name
Problem 5 — PydanticAI agent backend

### 2. Prompt
> yo, time for problem 5, "PydanticAI agent backend". lets build the actual chatbot backend using PydanticAI and FastAPI for our chat widget.
>
> put the api app in backend/main.py (so we can run it with uvicorn). keep the agent code organized in these 4 files right next to it:
> - backend/prompts/prompt.md (system prompt w/ store voice & safety basics)
> - backend/agent.py (agent entry & setup)
> - backend/tools.py (tools agent can use)
> - backend/models.py (pydantic types for chat replies / cards)
>
> in main.py, make a chat route so sending a message from the site gets a reply from the agent. make sure it uses our api key properly.
>
> test that i can run it from backend/ folder using: uvicorn main:app --reload --port 8000
>
> and update output/harness.md on how frontend talks to fastapi and how the agent is loaded.

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 6

### 1. Problem number and name
Problem 6 — Tools: product info and stock

### 2. Prompt
> hey! working on problem 6 here, "Tools: product info and stock". we need to give our agent real tools in backend/tools.py so it can query campus_customs.db directly.
>
> it needs tools to lookup:
> - product description
> - price
> - stock quantity (by size when asked)
>
> the agent HAS to use the db and not just guess or hallucinate prices/stock! if something is out of stock in a size, it should tell the user clearly.
>
> update backend/prompts/prompt.md so the agent knows when to call these tools. update models.py if needed.
>
> then in output/harness.md, list all the tools and explain what model fields you picked for the lookup results and why.

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 7

### 1. Problem number and name
Problem 7 — Chat search that updates the page

### 2. Prompt
> yo, let's tackle problem 7, "Chat search that updates the page". this feature is super cool, help me set it up:
> when a customer asks about a category in chat (like "what hoodies do you have?"), the agent should search the catalogue and the site should dynamically display those matching items as product cards on the page!
>
> so the agent needs to return structured product data that the front end can render.
>
> IMPORTANT: make sure those dynamic cards still open the single-item view page when clicked (large image + full info), just like in problem 3!
>
> update backend/prompts/prompt.md and output/harness.md so its clear how search results get sent to the front end.

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 8

### 1. Problem number and name
Problem 8 — Customer memory

### 2. Prompt
> hey, working on problem 8 now, "Customer memory". need to add memory to the chatbot.
>
> 1. chat history: if a user is logged in, save their chat messages in the database and load them back up when they come back. (guests don't need saved history).
> 2. user info: pass who is logged in (name, email) into agent deps/tools so the chatbot knows who its talking to.
> 3. page context: pass context about what page the user is looking at. so if they're looking at a specific item page and ask "do you have this in pink?", the agent knows what item "this" refers to.
>
> document all of this in output/harness.md (how history is stored, user info passed, and page context handling).

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 9

### 1. Problem number and name
Problem 9 — Usability improvements

### 2. Prompt
> yo, time for problem 9, "Usability improvements". let's add 4 usability upgrades to make the app feel way better:
> - 2 front-end ones (like auto scroll chat, typing indicator, quick reply buttons, or stock badges)
> - 2 agent / backend ones (like fuzzy search tool, prompt trimming, or error handling)
>
> before/while we code this, create output/usability.md and write down for each one:
> - what we added
> - why it helps the shopper or the business
>
> make sure all 4 improvements actually work and show up on the running site so graders can see them!

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 10

### 1. Problem number and name
Problem 10 — Style the website

### 2. Prompt
> hey, let's do problem 10, "Style the website". the site needs some styling polish so it looks like a real online shop!
>
> add some creative design—nice fonts, cool color scheme, better hierarchy, smooth hover/motion stuff, and a clean chat layout. make it feel legit and engaging.
>
> then write a short file at output/design.md explaining what was styled and why it helps keep customers on the page and buying stuff. keep it brief and to the point.

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 11

### 1. Problem number and name
Problem 11 — Site testing (app check)

### 2. Prompt
> i need to work on problem 11 next, "Site testing (app check)". make a simple HTML test page at output/app_check.html so graders can double click open it and grade my work.
>
> put screenshot images into output/app_check_images/ and link them with relative paths.
>
> include screenshots and 1-2 sentence captions for:
> 1. chat checking real inventory level from DB (honest stock & price)
> 2. dynamic search result cards showing up on the page after asking for a category (e.g. hoodies)
> 3. one of the usability features we built in problem 9
>
> make the HTML page clean with clear headings for each check so its super easy to grade!

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 12

### 1. Problem number and name
Problem 12 — Audit trail, safety, finish harness

### 2. Prompt
> almost done! let's work on problem 12, "Audit trail, safety, finish harness". i need to wrap up logging and harness documentation.
>
> 1. audit trail: create an append-only JSON file at output/audit_trail.json that logs agent activity (timestamp, tool called, args/result, stop reason). don't wipe it when restarting the app!
> 2. safety: add some safety rules to backend/prompts/prompt.md so the agent stays on topic and doesn't do weird stuff.
> 3. finish harness: complete output/harness.md so everything is documented:
>    - model fields in models.py & why we chose em
>    - tools list
>    - safety rules
>    - specs (loop limits, result caps, models used, how to run front & back)

### 3. Follow-up prompt (if needed)
_None needed._

**What was missing after the first prompt:** _N/A_

---

## Problem 13

### 1. Problem number and name
Problem 13 — Push to GitHub and submit the URL

### 2. Prompt
> yo last step, problem 13: "Push to GitHub and submit the URL"! help me clean up the repo folder `hw4` so its ready to push to github.
>
> 1. check .gitignore to make sure real .env, campus_customs.db, and product images aren't tracked!
> 2. make a .env.example file with fake placeholder values.
> 3. double check folder structure looks like this:
>
> ```
> hw4/
> ├── AI_prompts.md
> ├── requirements.txt
> ├── .env.example
> ├── .gitignore
> ├── README.md
> ├── frontend/                 # Vite React TypeScript app
> ├── backend/
> │   ├── main.py               # FastAPI app — run with: uvicorn main:app --reload --port 8000
> │   ├── agent.py
> │   ├── models.py
> │   ├── tools.py
> │   └── prompts/
> │       └── prompt.md
> └── output/
>     ├── harness.md
>     ├── design.md
>     ├── usability.md
>     ├── app_check.html
>     ├── app_check_images/     # screenshots linked from app_check.html
>     └── audit_trail.json
> ```
>
> 4. write a simple README.md explaining how to run the front end and backend after putting the data pack (data/campus_customs.db and data/products/) in place.

### 3. Follow-up prompt (if needed)
> push it

**What was missing after the first prompt:** The first prompt only got the folder ready (gitignore, .env.example, README, structure), but the code still wasn't on GitHub, so I had to ask it to actually create the public repo and push.
