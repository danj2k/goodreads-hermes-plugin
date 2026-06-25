# Design Decisions

## 1. Read-only database access

**Decision**: All connections use SQLite URI mode (`file:path?mode=ro`).

**Why**: This plugin only reads data. Enforcing read-only at the connection level prevents accidental mutations and makes the safety guarantee explicit, even if future handlers have bugs.

**Alternative considered**: Trust handlers not to write. Rejected because it's a brittle contract.

## 2. One connection per handler call

**Decision**: Each handler opens and closes its own SQLite connection via the `_connect()` context manager.

**Why**: Hermes may dispatch tool calls from different threads or async contexts. SQLite connections are not safe to share across threads. Opening per-call is simple, correct, and the overhead is negligible for a read-only local database.

**Alternative considered**: A global connection pool. Overkill for this use case and adds complexity around thread safety.

## 3. JSON string return type

**Decision**: Every handler returns a JSON string (via `_ok()` or `_err()`), never raises exceptions.

**Why**: Hermes expects tool handlers to return parseable results. Wrapping all output in `json.dumps()` with a `default=str` fallback ensures non-serializable types (dates, None) don't crash the pipeline. Errors return `{"error": "..."}` rather than raising, so the LLM can interpret and report them gracefully.

## 4. Partial, case-insensitive matching

**Decision**: Genre, shelf, and author name parameters use `LIKE %term%` matching.

**Why**: Users think in fuzzy terms — they'd search for "scifi" or "rowling" without worrying about exact casing or full names. The LLM also generates approximate queries. Partial matching makes the tools feel forgiving rather than brittle.

**Trade-off**: Could return unexpected matches for very short search terms (e.g., "a" matches everything). This is acceptable because the LLM controls what it searches for and can refine.

## 5. Custom shelves take priority over exclusive shelves

**Decision**: `get_books_by_shelf` queries custom shelves first; only falls back to exclusive shelves if no custom match exists.

**Why**: Custom shelves are more specific and more likely what the user means when they name a shelf. Exclusive shelves ("read", "to-read") are better accessed via dedicated tools or the `shelf` filter on other tools.

## 6. NULLS LAST ordering

**Decision**: Queries use `ORDER BY rating DESC NULLS LAST`.

**Why**: Books the user hasn't rated (NULL) should sink to the bottom rather than floating to the top or causing sort instability. This produces more intuitive results — rated books appear first, ordered by rating.

## 7. No caching layer

**Decision**: There is no in-memory cache between calls.

**Why**: The database is local and fast. The plugin is called infrequently (once per user question). Caching would add complexity around invalidation with no meaningful performance gain.

## 8. Schema-driven tool descriptions

**Decision**: Tool descriptions in `schemas.py` are written as natural language paragraphs explaining *when* to use the tool, not just what it does.

**Why**: The LLM selects tools based on these descriptions. Phrases like "Use this when someone asks..." and "This is the best tool to answer..." guide the model toward correct tool selection without requiring it to infer intent from parameter signatures alone.
