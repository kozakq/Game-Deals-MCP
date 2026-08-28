# CheapShark Marketplace

A [Claude Code plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
containing one plugin: an MCP server that gives Claude access to live PC game deals and price
history via the [CheapShark](https://www.cheapshark.com/) API — deals across Steam, GOG,
Epic, Humble, and every other major storefront it tracks, plus historical-low pricing so an
LLM can actually reason about whether a deal is good, not just report a number.

No API key required — CheapShark is a fully public, anonymous API.

```
.claude-plugin/marketplace.json   # marketplace catalog (this repo)
plugins/cheapshark/               # the plugin itself
```

## Tools

- **`search_deals`** — search and filter current deals (by title, store, price range,
  Metacritic/Steam rating, sort order). Accepts store names ("Steam", "GOG") directly.
- **`get_game`** — look up a game by title and get its current price at every store plus its
  all-time historical low, so you can tell if now is actually a good time to buy.
- **`list_stores`** — list the storefronts CheapShark tracks.

## Install as a plugin

Requires [`uv`](https://docs.astral.sh/uv/) on your PATH — it's what runs the server and
resolves its (pure-Python) dependencies on demand, so there's no separate install step.

In Claude Code:

```
/plugin marketplace add /path/to/this/repo
/plugin install cheapshark@cheapshark-marketplace
```

(or point `marketplace add` at this repo's GitHub URL once it's pushed). This is also what
lets the plugin sync in the Claude Desktop app via Cowork. Restart, and the three tools above
are available.

## Run it directly (without the plugin system)

Requires Python 3.11+ and `uv`.

```bash
cd plugins/cheapshark
uv run server.py
```

Run the tests:

```bash
cd plugins/cheapshark
uv run --extra dev pytest
```

### Manual MCP config

If you'd rather wire it up by hand than through `/plugin install` — e.g. in Claude Desktop's
`claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cheapshark": {
      "command": "uv",
      "args": ["run", "--project", "C:/path/to/this/repo/plugins/cheapshark", "C:/path/to/this/repo/plugins/cheapshark/server.py"]
    }
  }
}
```

## Try asking

- "Is Hades a good deal right now, or should I wait for a sale?"
- "What's on sale on Steam right now under $15 with a Metacritic score above 80?"
- "Compare current Elden Ring prices across every store CheapShark tracks."
- "Has Baldur's Gate 3 ever been cheaper than it is today?"

## Notes

- CheapShark rejects requests with a missing or generic `User-Agent` header — the client sets
  one on every request (`plugins/cheapshark/cheapshark_client.py`). If you fork this and start
  seeing mysterious API errors, that's the first thing to check.
- The store list is fetched once, on first use, and cached in memory for the life of the
  process — it's fetched from CheapShark just once, not on every call.
- Not built: email price-alert endpoints and a standalone deal-by-id lookup. Both are out of
  scope for what this server is trying to do (the fields you need for a specific deal are
  already in `search_deals` results).
