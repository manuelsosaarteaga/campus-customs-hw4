# Design — Campus Customs

**Goal:** look like a real, trustworthy Yale shop, and make every screen nudge the shopper toward a product page or a chat.

| Area | What we styled | Why it keeps shoppers on the page and buying |
|---|---|---|
| **Type** | Fraunces (collegiate serif) for headlines and prices; Inter for body and UI | Feels like heritage campus merch, not a template. A clear serif/sans split makes the hierarchy (headline → price → details) instant to scan. |
| **Color** | Yale navy + warm cream + a small gold accent (eyebrows, nav underline, scarcity badges), defined as CSS tokens | On-brand and calm. Gold is used sparingly, so it only draws the eye to what matters (section labels, "Only 2 sizes left"). |
| **Header** | Announcement bar (licensed · 57 Broadway · ask our assistant), frosted sticky nav that gains a shadow on scroll, gold hover underline, hamburger menu on phones | Trust cues up front. Navigation is always reachable without covering content. |
| **Home** | Editorial hero with floating real product photos, trust stats (102 styles · 11 college crests · XS–XXL live stock), shop-by-category tiles with counts, value pillars, featured grid, navy "Not sure what to get?" chat banner | The visitor sees real products in the first second, and there are three paths deeper: Shop, a category tile, or "Ask our assistant". |
| **Shop page** | Category chips with live counts, "In stock" toggle, sort (price/name), search with icon, sticky toolbar, shimmer loading skeletons, friendly empty state | Narrowing 102 items to "Hoodies · in stock · low to high" takes two taps, so shoppers find their item before giving up. Skeletons make loading feel fast. |
| **Product cards** | Category eyebrow, color swatches, bold price, gold "Only N sizes left" / dark "Sold out" badges, hover lift + image zoom + "View details →" pill | Hover feedback invites the click. Swatches and stock badges answer "is it in my color/size?" before the click, which cuts bounce from dead ends. |
| **Item page** | Breadcrumb, sticky image, serif price, selectable size pills (sold out struck through, low stock flagged), live size note, **"Ask about this item"** (opens the chat with the question pre-typed), "More crewnecks", perks list | The page is built around the decision: pick a size, see availability, and get any doubt answered without leaving. Breadcrumb and "More …" keep shoppers browsing instead of exiting. |
| **Chat** | Branded header (avatar, green "live stock & prices" dot), "Ask us" launcher with icon, tailed bubbles (navy = you, white = assistant), divider labels for saved history, pill quick replies, round send button, pop-in animation | Looks like a real support channel, so people trust and use it. Quick replies and the on-page result cards turn questions into product views. |
| **Motion** | Short eased transitions (~0.2–0.7s): sections fade/slide in as they scroll into view, cards lift, hero tiles float, chat pops in. All disabled under `prefers-reduced-motion` | Makes the site feel alive and responsive without slowing anyone down, and it stays accessible. |
| **Responsive** | Phone layout: hamburger menu, swipeable category chips, two-column grid, stacked hero/detail, full-width chat. Verified: no horizontal scroll at 390px | Most students shop on their phones, and a clean mobile experience keeps them from bouncing. |

**Honesty in the design:** every badge, count, and stat comes from the database (e.g. the hero says 11 college crests because the catalogue has 11, not "all 14"), so the polish never overpromises.
