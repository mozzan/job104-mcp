# job104-mcp

An MCP server for searching [104 人力銀行](https://www.104.com.tw) job listings with
natural-language filters, for use with Claude Desktop, Cursor, and other MCP clients.

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

## Install

    uv sync

## Run (stdio)

    uv run job104-mcp

## Add to Claude Desktop

Add to `claude_desktop_config.json`:

    {
      "mcpServers": {
        "job104": {
          "command": "uv",
          "args": ["--directory", "/absolute/path/to/job104-mcp", "run", "job104-mcp"]
        }
      }
    }

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

## License

MIT — see [LICENSE](LICENSE). Provided as-is, without warranty.
