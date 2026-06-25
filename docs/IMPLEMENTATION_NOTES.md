# Implementation Notes

## Database connection pattern

The `_connect()` context manager in `tools.py` uses SQLite's URI mode to open read-only:

```python
conn = sqlite3.connect(f"file:{_db_path()}?mode=ro", uri=True)
conn.row_factory = sqlite3.Row
```

`sqlite3.Row` is set as the row factory so that results can be converted to dicts via `dict(row)`. The `_rows_to_list()` helper does this for batches.

Changing this requires updating every handler that calls `_connect()`.

## `_ok()` and `_err()` helpers

These are the only exit paths from handlers. `_ok(data)` serializes with `json.dumps(data, default=str)` — the `default=str` handles datetime objects and other non-JSON-native types by converting them to strings. `_err(msg)` returns `{"error": "msg"}`.

The contract is: handlers never raise. The LLM receives either valid data or an error message it can relay to the user.

## `get_books_by_shelf` dual-query pattern

This handler runs two queries: one against `books.exclusive_shelf` and one against `book_shelves.shelf_name`. It prefers custom shelf results. The `source` field in the response (`"custom"` or `"exclusive"`) tells the caller which table matched.

This exists because Goodreads has two separate shelf systems: the three exclusive shelves (read/to-read/currently-reading) live on the `books` table directly, while user-created tag shelves live in the `book_shelves` junction table.

## `search_books` relevance ordering

The search query uses a CASE expression to boost exact title matches:

```sql
ORDER BY
    CASE WHEN b.book_title LIKE ? THEN 0 ELSE 1 END,
    b.rating DESC NULLS LAST,
    b.book_title
```

Title matches rank above author/description matches. Within each tier, the user's own rating takes precedence. This produces results where "the book I rated highly whose title contains X" floats to the top.

## `get_book_details` title lookup

When looking up by title (without a `book_id`), the query uses `ORDER BY LENGTH(book_title) LIMIT 1` to prefer the shortest matching title. This is a heuristic — for a query like "The Hobbit", it prefers "The Hobbit" over "The Hobbit, or There and Back Again" without requiring exact match.

## `get_rating_distribution` percentage calculation

The handler pre-fills all five star values plus "None" in the distribution dict, then populates from query results. This ensures the response always has entries for 1-5 stars and unrated, even if some have zero counts. Percentages are calculated against the shelf total.

## `get_reading_timeline` date parsing

Date filtering uses SQLite's `SUBSTR()` to extract year or year-month from `date_read` strings (stored as ISO format). The `LIKE` operator handles partial date matching (e.g., `LIKE '2023%'` matches all of 2023). This avoids SQLite's limited date parsing functions.

## `_db_path()` error handling

If `GOODREADS_DB_PATH` is not set, the function raises `RuntimeError` immediately. This is the one place handlers are allowed to raise — it's a configuration error that should fail loudly rather than returning a confusing "no such table" error.

## Limit clamping

Every handler clamps its `limit` parameter to a hard maximum (100, 200, or 500 depending on the tool). This prevents a misbehaving LLM from requesting millions of rows. The minimum is always 1.

## `lookup_book` exact matching

The `lookup_book` tool uses `LOWER()` on both sides of the comparison (`LOWER(b.book_title) = ?` and `LOWER(a.author_name) = ?`) with the input pre-lowercased in Python. This gives case-insensitive exact matching — "Salvos" matches "Salvos" but not "Salvos 2". The query takes both title and author as required parameters and returns a boolean `found` flag with the matching book details when found. This was added to solve the problem of `search_books` returning too many fuzzy matches when the user needs a precise "does this exact book by this exact author exist?" answer.

## `lookup_books` batch exact matching

The `lookup_books` tool accepts a list of `{title, author}` pairs and runs the same `LOWER() =` exact-match query for each within a single DB connection. This is the batch equivalent of `lookup_book` — same matching semantics, but avoids the overhead of multiple round-trips when checking 10+ books against the library at once.

The iteration approach (one query per pair within a single connection) was chosen over a single multi-OR query because it keeps the mapping from input to results trivial — each input pair produces exactly one result entry with its own `found` flag. The per-query cost is negligible since each is an indexed exact-match lookup.

The response includes aggregate counts (`total`, `found`, `not_found`) so the caller can quickly gauge how many matches there were without counting the results array.
