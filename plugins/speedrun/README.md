# Speedrun.com Game Data

MCP server for searching speedrun.com — resolve a game, see what categories it has, and pull
ranked leaderboards with real player names, driven by the free, key-free
[speedrun.com API](https://github.com/speedruncomorg/api).

No API key required. speedrun.com enforces a 100 requests/minute rate limit per IP (HTTP 420
if exceeded); this server doesn't throttle proactively, it just surfaces that as a clear error
if it happens.

## Tools

- **`search_game`** — resolve a game title to the ID needed by the other two tools. Prefers an
  exact title match; lists other candidates when the search was ambiguous.
- **`get_categories`** — list every category a game has (Any%, 100%, and whatever
  game-specific categories it defines), each labeled with whether it's a main or
  miscellaneous/legacy category.
- **`get_leaderboard`** — ranked runs for a specific game + category, with real player names
  (not raw IDs), times in seconds, video links, and run pages.

## Zero runtime dependencies

Same design as the CheapShark plugin in this marketplace: `server.py` is written directly
against the [MCP stdio JSON-RPC protocol](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
using only the Python standard library (`urllib` for HTTP) — no third-party packages, so
there's nothing to install at plugin-launch time on any platform.

## Install as a plugin

Requires Python 3.11+ (as `python3` on your PATH).

```
/plugin marketplace add /path/to/this/repo
/plugin install speedrun@cheapshark-marketplace
```

## Run it directly

```bash
cd plugins/speedrun
python3 server.py
```

It sits there speaking MCP over stdio — meant to be launched by an MCP client, not run
interactively.

Run the tests:

```bash
cd plugins/speedrun
uv run --extra dev pytest
```

### Manual MCP config

```json
{
  "mcpServers": {
    "speedrun": {
      "command": "python3",
      "args": ["C:/path/to/this/repo/plugins/speedrun/server.py"]
    }
  }
}
```

(On Windows, if `python3` isn't on your PATH, use `python` instead.)

## Try asking

- "What speedrun categories does Hades have?"
- "Who holds the world record for Celeste?"
- "Show me the top 5 fastest Any% runs of Hades, with video links."
- "Is there an Early Access category for Hades, or just the current release?"

## Notes

- Categories are entirely game-specific free text (Hades has "Any Heat," "Fresh File," "OwO" —
  not a universal "Any%/100%" template), so don't assume naming conventions transfer between
  games.
- `get_leaderboard` requires `embed=players` on the underlying API call — without it, runs only
  carry opaque player IDs, not names. Leaderboard embeds don't nest into each run the way
  embeds work elsewhere in this API; they come back as one flat player list at the top level,
  which the server joins against each run's player ID(s) itself.
- Not every runner is a registered user — some runs list a guest by name instead of an ID.
  `get_leaderboard` falls back to the inline guest name when no ID lookup is available.
- Only full-game leaderboards are supported (`GET /leaderboards/{game}/category/{category}`),
  not individual-level leaderboards.
- Not built: run submission, moderation actions, or anything beyond reading public game/
  category/leaderboard data — this server only ever makes GET requests.
