---
name: speedruns
description: "Answer questions about speedrunning a video game - world records, leaderboards, run categories, personal bests, or how fast a game has been completed - using live speedrun.com data instead of memory or a general web search. Use whenever a game's speedrun categories, leaderboard, world record, or fastest-completion time comes up."
---

# Speedrun.com Lookups

## Keywords

speedrun, world record, WR, leaderboard, personal best, PB, run category, Any%, 100%,
glitchless, fastest completion, how fast can you beat, speedrunning, category extensions

## Overview

This skill drives the bundled `search_game`, `get_categories`, and `get_leaderboard` MCP
tools to ground answers about speedrunning in live data from speedrun.com, rather than
memory (stale — records fall constantly) or a general web search when a purpose-built tool
already exists. Use it proactively whenever the conversation touches a game's speedrun
categories, records, or leaderboard, even if the user doesn't name the tools directly.

## Workflow

1. **Resolve the game first.** Call `search_game` with the title. It returns the game's ID
   plus `other_matches` if the search was ambiguous (e.g. "Hades" also matches "Hades 2,"
   ROM hacks, and unrelated games with "Hades" in the name) — check those before assuming
   the first result is the one the user meant.

2. **"What categories does `<game>` have?"** — Call `get_categories` with the resolved game
   ID. Category names are entirely game-specific (a game might have "Any Heat" and "Fresh
   File" instead of "Any%"), so don't assume standard naming. Each category is labeled
   `miscellaneous: true/false` — prefer the non-miscellaneous ones when just answering "what
   can I ask about," but don't hide the miscellaneous ones if the user asks for everything.

3. **"Who holds the world record for `<game>` `<category>`?" / "Show me the leaderboard"** —
   Call `get_leaderboard` with the game ID and the category ID from the previous step. Use
   `top` to control how many places come back (world record alone is `top=1`). Report real
   times (in seconds, converted to a readable minutes/seconds format for the user) and real
   player names, not raw IDs.

4. **Cite real numbers and names.** Place, time, and who ran it are the point of these
   tools — a vague "someone's done it in about two minutes" is not a useful answer here.

5. **Handle empty/error results gracefully.** A dict with an `"error"` key (no game/category
   matched, or the API is unreachable, including a 100 req/min rate limit) should be
   surfaced in plain language, not silently retried or papered over.

## When NOT to use

- **Submitting, verifying, or moderating runs.** These tools only read public game/category/
  leaderboard data; they can't submit a run or take any moderation action.
- **Individual-level leaderboards.** `get_leaderboard` only covers full-game leaderboards,
  not per-level ones.
- **The tools return an error.** Don't fabricate a time or a record holder if a tool comes
  back with `"error"` — report the error, and fall back to a general web search only if
  useful, saying explicitly that's what you're doing.
