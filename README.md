# job104-mcp

An MCP server for searching [104 人力銀行](https://www.104.com.tw) job listings with
natural-language filters. Works with any MCP client — Claude, Cursor, Windsurf, Cline,
Zed, VS Code, and others.

> **Disclaimer:** This is an unofficial, educational/personal-use tool. It is **not
> affiliated with, endorsed by, or sponsored by 104 Corporation**. It calls 104's
> public web endpoints; please respect 104's Terms of Service and use it at a
> reasonable, low frequency. No scraped job data is distributed with this project.

## How it works

104 sits behind Cloudflare bot protection — a plain HTTP request to its JSON API
returns 403. This server uses [`curl_cffi`](https://github.com/lexiforest/curl_cffi)
with `impersonate="chrome"` to match a real browser's TLS fingerprint, so the same
public endpoints return their normal JSON. The AI sees clean structured results; the
104 category/area codes are resolved from Chinese names automatically.

## Prerequisite: install uv

Every install path runs the server through [uv](https://docs.astral.sh/uv/), so it must
be installed first (`uvx` ships with uv):

    # macOS / Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Windows (PowerShell)
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

## Install in any MCP client (Cursor, Windsurf, Cline, Zed, VS Code, …)

MCP is an open protocol, so any MCP-capable client works — not just Claude. Add this to
the client's MCP config (e.g. Cursor's `~/.cursor/mcp.json`); the `command`/`args` form is
what most clients accept:

    {
      "mcpServers": {
        "job104": { "command": "uvx", "args": ["job104-mcp@latest"] }
      }
    }

## Install in Claude Code

    claude mcp add job104 -- uvx job104-mcp@latest

Or from a local clone (no PyPI required):

    claude mcp add job104 -- uv run --project /absolute/path/to/job104-mcp -m job104_mcp

## Install in Claude Desktop (.mcpb bundle)

The `.mcpb` bundle is a Claude-Desktop-only convenience (other clients use the JSON config
above). Download `job104-mcp-vX.Y.Z.mcpb` from the
[Releases](https://github.com/mozzan/job104-mcp/releases) page and double-click it (or drag
it into Claude Desktop → Settings → Extensions).

To build the bundle yourself:

    npx @anthropic-ai/mcpb pack .   # produces job104-mcp.mcpb

## Run manually (stdio)

    uv run job104-mcp
    # or
    uv run python -m job104_mcp

## Tools

- `search_jobs` — search with keyword, area, job category, salary floor, remote,
  recency, experience, education, sort, paging. Use Chinese names for `area`/`jobcat`
  (e.g. `["台北市大安區"]`, `["軟體工程師"]`); they resolve to 104 codes automatically.
  Each result carries a `detail_id`.
- `get_job_detail` — full posting for a `detail_id` from `search_jobs`.
- `lookup_code` — resolve a job-category or area name to its 104 code.

## Refresh code tables

The bundled `jobcat.json` / `area.json` come from 104's public category tool. Regenerate:

    uv run python scripts/fetch_codes.py

## Tests

    uv run pytest            # fast unit tests
    uv run pytest -m live    # hits the real 104 site

## Releasing (maintainer)

Releases are automated by `.github/workflows/release.yml`, triggered when the
version in `pyproject.toml` changes on `main`. It publishes to PyPI, builds the
`.mcpb` bundle, and attaches it to a GitHub Release.

One-time PyPI setup (uses [Trusted Publishing](https://docs.pypi.org/trusted-publishers/),
no API token stored): on <https://pypi.org/manage/account/publishing/> add a pending
publisher with project `job104-mcp`, owner `mozzan`, repo `job104-mcp`, workflow
`release.yml`.

To cut a release: bump `version` in `pyproject.toml`, commit to `main`.

## License

MIT — see [LICENSE](LICENSE). Provided as-is, without warranty.
