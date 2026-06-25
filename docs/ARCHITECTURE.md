# Architecture

## Overview

The plugin is a thin adapter between Hermes Agent's tool system and a local SQLite database. There is no business logic layer — each tool handler executes SQL directly and returns JSON.

## Components

```
plugin.yaml          — Plugin metadata and env requirements
__init__.py          — Registration: maps tool names → schemas + handlers
schemas.py           — 13 tool schemas (what the LLM sees)
tools.py             — 13 tool handlers (the actual SQL queries)
```

### Registration (`__init__.py`)

Hermes calls `register(ctx)` once at startup. The `_TOOL_MAP` list pairs each tool name with its schema (from `schemas.py`) and handler (from `tools.py`). The toolset name `"goodreads"` groups all tools under a single namespace.

### Schemas (`schemas.py`)

Each schema is a dict matching Hermes tool schema format:
- `name`: tool identifier
- `description`: text the LLM reads to decide when/how to call the tool
- `parameters`: JSON Schema object defining required/optional arguments

Descriptions are written from the agent's perspective — the database contains the *user's* Goodreads library, so the agent queries it on their behalf.

### Handlers (`tools.py`)

Every handler follows the same contract:

```python
def handler_name(args: dict, **kwargs) -> str:
    # 1. Extract and validate parameters from args
    # 2. Open a read-only SQLite connection
    # 3. Execute SQL
    # 4. Return JSON string via _ok(data) or _err(msg)
```

## Data Flow

```
User question
  → LLM reads tool descriptions
  → LLM selects tool + arguments
  → Hermes dispatches to handler
  → Handler opens read-only SQLite connection
  → SQL query executes against local database
  → Results serialized to JSON
  → JSON returned to LLM
  → LLM formats answer for user
```

## Database Schema

The plugin reads from these tables (created by `goodreads-user-scraper`):

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `books` | book_id, book_title, book_description, author_id, rating, average_rating, num_pages, year_first_published, exclusive_shelf | Core book data with user's rating and shelf assignment |
| `authors` | author_id, author_name, author_description | Author metadata |
| `book_genres` | book_id, genre | Many-to-many: books ↔ genres |
| `book_shelves` | book_id, shelf_name | Many-to-many: books ↔ custom shelves |
| `book_dates_read` | book_id, date_read | Multiple read dates per book |
| `users` | num_ratings, average_rating, num_reviews | Single-row user profile |

## Dependencies

- Python 3 (standard library only — `sqlite3`, `json`, `os`)
- No third-party packages
- SQLite (via Python's built-in `sqlite3` module)
