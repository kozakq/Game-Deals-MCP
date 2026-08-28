---
name: game-deals
description: "Answer questions about PC game prices, sales, and whether now is a good time to buy, using live CheapShark data instead of memory or a general web search. Use whenever a game's current price, a storefront sale, a price history / all-time low, or a \"should I buy now or wait\" question comes up for a PC game on Steam, GOG, Epic Games Store, Humble Store, or any other storefront CheapShark tracks."
---

# PC Game Deals (CheapShark)

## Keywords

game deal, is this a good deal, should I buy now or wait, steam sale, GOG sale,
Epic Games Store sale, Humble Bundle price, PC game price, price history,
all-time low, historical low, cheapest price, how much is \[game\] on Steam,
what's on sale, discount, wishlist price check, is it worth buying now

## Overview

This skill drives the bundled `search_deals`, `get_game`, and `list_stores` MCP
tools to ground answers about PC game pricing in live data, rather than
answering from training-data memory (which will be stale — prices and sales
change constantly) or reaching for a general web search when a purpose-built
tool already exists for exactly this. Use it proactively whenever the
conversation is about a PC game's price or whether a deal is good, even if the
user doesn't name the tools or the CheapShark plugin directly.

## Workflow

1. **"Is `<game>` a good deal / should I wait / has it ever been cheaper?"**
   Call `get_game` with the title. It returns the current price at every store
   it's sold on plus the all-time historical-low price and date. Compare the two
   yourself and give a real recommendation — don't just report the current
   price. If the current price is at or near the historical low, say so
   explicitly; if it's well above it, say that too and note the low so the user
   can judge whether to wait.

2. **"What's on sale on `<store>`", "find deals under $X", "highly-rated games
   on sale"** — Call `search_deals` with the relevant filters (`store`,
   `max_price`/`min_price`, `min_metacritic`, `min_steam_rating`, `sort_by`).
   Store names ("Steam", "GOG", "Epic Games Store", "Humble Store", etc.) can be
   passed directly — no need to look up IDs first.

3. **Ambiguous or unfamiliar store name** — call `list_stores` only if you need
   to confirm what CheapShark actually tracks; `search_deals` already resolves
   common store names on its own.

4. **Always cite real numbers** — sale price, normal price, savings percent,
   and (for `get_game`) the historical low and its date. A vague "it's on sale"
   is not a useful answer here; the whole point of these tools is the specific
   figures.

5. **Handle empty/error results gracefully.** An empty list from `search_deals`
   means no deals matched the filters — say so, don't imply the tool failed.
   A dict with an `"error"` key (unmatched store name, or the CheapShark API
   being unreachable) should be surfaced to the user in plain language, not
   silently retried or papered over.

## When NOT to use

- **Non-PC platforms** (console-exclusive titles, mobile). CheapShark only
  tracks PC storefronts — say so rather than guessing at console pricing.
- **Purchasing or redeeming anything.** These tools only search and report
  prices; they can't buy, wishlist, or apply codes.
- **The tools return an error.** Don't fabricate a price or a historical low
  if `get_game`/`search_deals` come back with an `"error"` — report the error
  and, if useful, fall back to a general web search, but say explicitly that
  you're doing that instead of presenting it as CheapShark data.
