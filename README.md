# CheapShark MCP Server

An MCP server that gives Claude (or any MCP client) access to live PC game deals and price
history via the [CheapShark](https://www.cheapshark.com/) API — deals across Steam, GOG,
Epic, Humble, and every other major storefront it tracks, plus historical-low pricing so an
LLM can actually reason about whether a deal is good, not just report a number.

No API key required — CheapShark is a fully public, anonymous API.

## Tools

- **`search_deals`** — search and filter current deals (by title, store, price range,
  Metacritic/Steam rating, sort order). Accepts store names ("Steam", "GOG") directly.
- **`get_game`** — look up a game by title and get its current price at every store plus its
  all-time historical low, so you can tell if now is actually a good time to buy.
- **`list_stores`** — list the storefronts CheapShark tracks.

## Setup

Requires Python 3.11+.

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -e .
```

Run it directly (mostly useful for a quick sanity check — it just sits there speaking MCP
over stdio):

```bash
python server.py
```

Run the tests:

```bash
pip install -e ".[dev]"
pytest
```

## Connect it to Claude

Add this to your Claude Desktop config (`claude_desktop_config.json`) or Claude Code MCP
config (`.mcp.json`), using the absolute path to this project's `server.py` and the Python
interpreter from the venv you created above:

```json
{
  "mcpServers": {
    "cheapshark": {
      "command": "C:/path/to/cheapshark-mcp/.venv/Scripts/python.exe",
      "args": ["C:/path/to/cheapshark-mcp/server.py"]
    }
  }
}
```

Or with the Claude Code CLI:

```bash
claude mcp add cheapshark -- C:/path/to/cheapshark-mcp/.venv/Scripts/python.exe C:/path/to/cheapshark-mcp/server.py
```

Restart Claude Desktop / Claude Code and the three tools above will be available.

## Try asking

- "Is Hades a good deal right now, or should I wait for a sale?"
- "What's on sale on Steam right now under $15 with a Metacritic score above 80?"
- "Compare current Elden Ring prices across every store CheapShark tracks."
- "Has Baldur's Gate 3 ever been cheaper than it is today?"

## Notes

- CheapShark rejects requests with a missing or generic `User-Agent` header — this server
  sets one on every request (`cheapshark_client.py`). If you fork this and start seeing
  mysterious API errors, that's the first thing to check.
- The store list is fetched once, on first use, and cached in memory for the life of the
  process — it's fetched from CheapShark just once, not on every call.
- Not built: email price-alert endpoints and a standalone deal-by-id lookup. Both are out of
  scope for what this server is trying to do (the fields you need for a specific deal are
  already in `search_deals` results).
