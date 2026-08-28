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

## Design note: zero runtime dependencies

The server is hand-written against the [MCP stdio JSON-RPC protocol](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports)
directly — no `fastmcp`, no `httpx`, nothing beyond the Python standard library.

That wasn't the first version. It started on `fastmcp` + `httpx`, launched via `uv run`
so dependencies resolved on demand. That works fine locally, but plugin/connector installs
in Claude Desktop and Cowork run `.mcp.json`'s `command`/`args` as-is — there's no install
step. `uv run`'s on-demand dependency resolution has nowhere to run in that model, and
`fastmcp`'s real dependency tree turned out to include several platform-specific compiled
packages (`pydantic-core`, `cryptography`, `rpds-py`, ...), which rules out just vendoring
them portably too. Since this server only needs three tools and one JSON-RPC handshake,
writing that ~150 lines directly against stdlib (`server.py`) removes the problem
entirely — there is nothing to install, on any platform, ever.

## Install as a plugin

Requires Python 3.11+ (as `python3` on your PATH — nothing else, no packages to install).

In Claude Code:

```
/plugin marketplace add /path/to/this/repo
/plugin install cheapshark@cheapshark-marketplace
```

(or point `marketplace add` at this repo's GitHub URL). This is also what lets the plugin
sync in the Claude Desktop app via Cowork. Restart, and the three tools above are available.

## Run it directly (without the plugin system)

```bash
cd plugins/cheapshark
python3 server.py
```

It just sits there speaking MCP over stdio — that's expected, it's meant to be launched by
an MCP client, not run interactively.

Run the tests (this needs [`uv`](https://docs.astral.sh/uv/), or just `pip install pytest`
and run `pytest` directly — `uv` is only a dev convenience, never required at runtime):

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
      "command": "python3",
      "args": ["C:/path/to/this/repo/plugins/cheapshark/server.py"]
    }
  }
}
```

(On Windows, if `python3` isn't on your PATH, use `python` instead.)

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
