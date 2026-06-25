# Goodreads Plugin for Hermes Agent

A [Hermes Agent](https://hermes-agent.nousresearch.com) plugin that gives your LLM agent read-only access to a user's Goodreads library data. It translates natural-language questions about books, authors, shelves, and reading habits into SQL queries against a local SQLite database — no SQL knowledge required.

## What it does

The plugin registers 14 tools under the `goodreads` toolset:

| Tool | Purpose |
|------|---------|
| `get_reading_stats` | High-level overview: book counts per shelf, average rating, review count |
| `get_top_rated_books` | Books the user rated most highly |
| `get_books_by_shelf` | List books on a specific shelf, sorted by rating (supports count-only mode) |
| `get_shelf_list` | All shelves with book counts |
| `get_books_by_genre` | Books matching a genre, optionally filtered by shelf or rating (supports count-only mode) |
| `get_genre_preferences` | Genre breakdown with average ratings and top-rated book per genre |
| `get_author_stats` | Per-author reading stats: books read, average rating, titles |
| `get_book_details` | Full details for a single book by ID or title |
| `search_books` | Full-text search across titles, authors, and descriptions |
| `lookup_book` | Exact case-insensitive title + author match (precise yes/no lookup) |
| `lookup_books` | Batch version of lookup_book — check multiple title+author pairs in one call |
| `get_reading_timeline` | Books grouped by year or month, with date-read metadata (supports count-only mode) |
| `get_rating_distribution` | Star-rating histogram with counts and percentages |
| `get_unrated_read_books` | Finished books with no user rating |

When the plugin is active, the agent can answer questions like "What are my highest-rated sci-fi books?", "How many books did I read last year?", or "Do I have Salvos by V.A. Lewis in my library?" without you needing to write any SQL.

## Prerequisites

1. **Hermes Agent** installed and working. See the [Hermes documentation](https://hermes-agent.nousresearch.com/docs) for setup instructions.

2. **A Goodreads SQLite database** — the plugin reads from a local SQLite file created by a companion scraper (e.g. [goodreads-user-scraper](https://github.com/danj2k/goodreads-hermes-plugin)). The database must contain these tables:

   | Table | Purpose |
   |-------|---------|
   | `books` | Core book data: title, author, rating, description, shelf, page count, year |
   | `authors` | Author names and descriptions |
   | `book_genres` | Books-to-genres mapping |
   | `book_shelves` | Books-to-custom-shelves mapping |
   | `book_dates_read` | Read dates per book |
   | `users` | Single-row user profile (rating count, average, reviews) |

## Installation

This plugin is installed as a **user plugin** — a folder placed in Hermes's plugin directory.

### Step 1: Clone or copy the plugin

Clone this repository (or copy the folder) into your Hermes plugins directory. The folder **must** be named exactly `goodreads` to match the `name` field in `plugin.yaml`:

```bash
git clone https://github.com/danj2k/goodreads-hermes-plugin ~/.hermes/plugins/goodreads
```

Alternatively, if you already have the source:

```bash
cp -r /path/to/goodreads ~/.hermes/plugins/goodreads
```

Your directory tree should look like:

```
~/.hermes/plugins/
  goodreads/
    plugin.yaml
    __init__.py
    schemas.py
    tools.py
    docs/
    README.md
```

### Step 2: Set the environment variable

The plugin requires `GOODREADS_DB_PATH` to point to your SQLite database. Set it in your shell profile or in Hermes's `.env` file:

```bash
# In ~/.bashrc, ~/.zshrc, or similar:
export GOODREADS_DB_PATH="/path/to/your/goodreads.db"

# Or in ~/.hermes/.env:
GOODREADS_DB_PATH=/path/to/your/goodreads.db
```

If this variable is not set, every tool call will return an error explaining the missing configuration.

### Step 3: Restart Hermes

Hermes discovers plugins at startup. Restart the agent so it loads the new plugin:

```bash
# CLI:
hermes restart

# Or just start a new session — Hermes auto-discovers plugins on launch.
```

### Step 4: Verify

Start a conversation and ask something like:

> "What's on my to-read shelf?"
> "How many books are on my to-read shelf?"
> "How many LitRPG books have I read?"
> "How many books did I read in 2023?"
> "Do I have Salvos by V.A. Lewis in my library?"

The agent should call the appropriate tool and return your books. The second, third, and fourth examples use `count_only` mode to return just the number without the full list. You can also check that the tools are registered by running `hermes tools` and looking for tools prefixed with `goodreads:`.

## How it works

```
User question about books
  → LLM reads the tool descriptions registered by the plugin
  → LLM selects the appropriate tool and arguments
  → Hermes dispatches to the tool handler in tools.py
  → Handler opens a read-only SQLite connection
  → SQL query runs against the local database
  → Results are serialised to JSON and returned to the LLM
  → LLM formats a natural-language answer for the user
```

The plugin is read-only by design — it uses SQLite's `?mode=ro` URI flag and never executes `INSERT`, `UPDATE`, or `DELETE` statements. Your data is safe.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GOODREADS_DB_PATH` | Yes | Absolute path to the Goodreads SQLite database file |

No other configuration is needed. The plugin has no API keys, no network access, and no third-party dependencies — it uses only Python's standard library (`sqlite3`, `json`, `os`).

## Project structure

```
goodreads/
├── plugin.yaml           # Plugin manifest: name, version, env requirements
├── __init__.py           # register(): wires schemas to handlers
├── schemas.py            # Tool schemas (what the LLM sees)
├── tools.py              # Tool handlers (SQL queries that run)
├── README.md             # This file
└── docs/
    ├── PROJECT.md            # Purpose, goals, non-goals, constraints
    ├── ARCHITECTURE.md       # System overview, components, data flow
    ├── DESIGN_DECISIONS.md   # Key decisions and rationale
    └── IMPLEMENTATION_NOTES.md # Non-obvious details and edge cases
```

## Troubleshooting

**"GOODREADS_DB_PATH environment variable is not set"**

Set the `GOODREADS_DB_PATH` environment variable (see [Step 2](#step-2-set-the-environment-variable) above). The agent will see this as a tool error.

**"no such table: books"**

The SQLite database doesn't match the expected schema. The plugin expects tables created by a Goodreads export scraper. Verify your database with:

```bash
sqlite3 /path/to/your/goodreads.db ".tables"
```

You should see `books`, `authors`, `book_genres`, `book_shelves`, `book_dates_read`, and `users`.

**Tools don't appear after installation**

Ensure the folder is at `~/.hermes/plugins/goodreads/` (not nested deeper, and not with a different name). Restart Hermes after placing the plugin.

**"database is locked" errors**

Unlikely since the plugin opens read-only connections, but can happen if another process has the database open in WAL mode with a long-running write. Try again — SQLite WAL is designed for concurrent reads.

## Design details

For deeper context on architecture, design decisions, and implementation notes, see the [docs/](docs/) directory.

## License

See repository for licence details.
