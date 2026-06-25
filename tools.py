"""
Goodreads plugin — tool handlers.

Every public function in this module:
  • Accepts (args: dict, **kwargs)
  • Returns a JSON string (never raises)
  • Opens and closes its own DB connection (thread-safe; SQLite WAL is read-only here)

The database path is read from the GOODREADS_DB_PATH environment variable,
which is required by plugin.yaml.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _db_path() -> str:
    path = os.environ.get("GOODREADS_DB_PATH", "")
    if not path:
        raise RuntimeError(
            "GOODREADS_DB_PATH environment variable is not set. "
            "Point it at your Goodreads SQLite database file."
        )
    return path


@contextmanager
def _connect():
    """Yield a read-only SQLite connection; always close it."""
    conn = sqlite3.connect(f"file:{_db_path()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def _rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]


def _ok(data: Any) -> str:
    return json.dumps(data, default=str)


def _err(msg: str) -> str:
    return json.dumps({"error": msg})


# ---------------------------------------------------------------------------
# 1. get_reading_stats
# ---------------------------------------------------------------------------

def get_reading_stats(args: dict, **kwargs) -> str:
    """High-level reading statistics."""
    try:
        with _connect() as conn:
            # Books per exclusive shelf
            shelf_counts = _rows_to_list(conn.execute(
                "SELECT exclusive_shelf, COUNT(*) AS count "
                "FROM books GROUP BY exclusive_shelf"
            ).fetchall())

            # User profile
            user = dict(conn.execute(
                "SELECT num_ratings, average_rating, num_reviews FROM users LIMIT 1"
            ).fetchone() or {})

            # Read books stats
            read_stats = dict(conn.execute(
                """
                SELECT
                    COUNT(*)                     AS books_read,
                    ROUND(AVG(rating), 2)        AS avg_user_rating,
                    ROUND(AVG(num_pages), 0)     AS avg_pages,
                    SUM(num_pages)               AS total_pages,
                    COUNT(DISTINCT author_id)    AS unique_authors
                FROM books
                WHERE exclusive_shelf = 'read'
                """
            ).fetchone() or {})

            # Custom shelf count
            custom_shelf_count = conn.execute(
                "SELECT COUNT(DISTINCT shelf_name) FROM book_shelves"
            ).fetchone()[0]

            return _ok({
                "user": user,
                "shelves": shelf_counts,
                "read_books": read_stats,
                "custom_shelf_count": custom_shelf_count,
            })
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 2. get_top_rated_books
# ---------------------------------------------------------------------------

def get_top_rated_books(args: dict, **kwargs) -> str:
    """Books the user rated most highly."""
    try:
        shelf = args.get("shelf")
        min_rating = int(args.get("min_rating", 4))
        limit = min(int(args.get("limit", 10)), 100)

        params: list = [min_rating]
        where = "b.rating >= ?"
        if shelf:
            where += " AND b.exclusive_shelf = ?"
            params.append(shelf)

        sql = f"""
            SELECT
                b.book_id, b.book_title, a.author_name,
                b.rating AS user_rating, b.average_rating AS global_avg,
                b.year_first_published, b.num_pages, b.exclusive_shelf
            FROM books b
            LEFT JOIN authors a USING (author_id)
            WHERE {where}
            ORDER BY b.rating DESC, b.average_rating DESC, b.book_title
            LIMIT ?
        """
        params.append(limit)

        with _connect() as conn:
            rows = _rows_to_list(conn.execute(sql, params).fetchall())

        return _ok({"books": rows, "count": len(rows)})
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 3. get_books_by_genre
# ---------------------------------------------------------------------------

def get_books_by_genre(args: dict, **kwargs) -> str:
    """Books in a specific genre."""
    try:
        genre = args.get("genre", "").strip()
        if not genre:
            return _err("'genre' parameter is required.")

        shelf = args.get("shelf")
        min_rating = args.get("min_rating")
        limit = min(int(args.get("limit", 20)), 200)

        params: list = [f"%{genre}%"]
        extra = ""
        if shelf:
            extra += " AND b.exclusive_shelf = ?"
            params.append(shelf)
        if min_rating is not None:
            extra += " AND b.rating >= ?"
            params.append(int(min_rating))

        sql = f"""
            SELECT
                b.book_id, b.book_title, a.author_name,
                b.rating AS user_rating, b.average_rating AS global_avg,
                b.year_first_published, b.exclusive_shelf,
                GROUP_CONCAT(g2.genre, ', ') AS all_genres
            FROM book_genres g
            JOIN books b ON b.book_id = g.book_id
            LEFT JOIN authors a ON a.author_id = b.author_id
            LEFT JOIN book_genres g2 ON g2.book_id = b.book_id
            WHERE g.genre LIKE ?{extra}
            GROUP BY b.book_id
            ORDER BY b.rating DESC NULLS LAST, b.average_rating DESC
            LIMIT ?
        """
        params.append(limit)

        with _connect() as conn:
            rows = _rows_to_list(conn.execute(sql, params).fetchall())

        return _ok({"genre_query": genre, "books": rows, "count": len(rows)})
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 4. get_genre_preferences
# ---------------------------------------------------------------------------

def get_genre_preferences(args: dict, **kwargs) -> str:
    """Genre breakdown with average ratings and book counts."""
    try:
        shelf = args.get("shelf", "read")
        min_books = int(args.get("min_books", 1))
        limit = min(int(args.get("limit", 20)), 100)

        sql = """
            SELECT
                g.genre,
                COUNT(DISTINCT b.book_id)     AS book_count,
                ROUND(AVG(b.rating), 2)       AS avg_user_rating,
                ROUND(AVG(b.average_rating), 2) AS avg_global_rating,
                MAX(b.book_title)             AS example_book
            FROM book_genres g
            JOIN books b ON b.book_id = g.book_id
            WHERE b.exclusive_shelf = ?
            GROUP BY g.genre
            HAVING book_count >= ?
            ORDER BY avg_user_rating DESC NULLS LAST, book_count DESC
            LIMIT ?
        """

        with _connect() as conn:
            rows = _rows_to_list(conn.execute(sql, [shelf, min_books, limit]).fetchall())

        return _ok({"shelf": shelf, "genres": rows})
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 5. get_author_stats
# ---------------------------------------------------------------------------

def get_author_stats(args: dict, **kwargs) -> str:
    """Per-author reading statistics."""
    try:
        shelf = args.get("shelf")
        sort_by = args.get("sort_by", "avg_rating")
        min_books = int(args.get("min_books", 1))
        limit = min(int(args.get("limit", 20)), 200)
        author_name = args.get("author_name", "").strip()

        order = "avg_user_rating DESC NULLS LAST" if sort_by != "book_count" else "book_count DESC"

        params: list = []
        extra = ""
        if shelf:
            extra += " AND b.exclusive_shelf = ?"
            params.append(shelf)
        if author_name:
            extra += " AND a.author_name LIKE ?"
            params.append(f"%{author_name}%")

        sql = f"""
            SELECT
                a.author_id,
                a.author_name,
                COUNT(b.book_id)              AS book_count,
                ROUND(AVG(b.rating), 2)       AS avg_user_rating,
                GROUP_CONCAT(b.book_title, ' | ') AS titles_read
            FROM authors a
            JOIN books b ON b.author_id = a.author_id
            WHERE 1=1{extra}
            GROUP BY a.author_id
            HAVING book_count >= ?
            ORDER BY {order}
            LIMIT ?
        """
        params += [min_books, limit]

        with _connect() as conn:
            rows = _rows_to_list(conn.execute(sql, params).fetchall())

        return _ok({"authors": rows, "count": len(rows)})
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 6. get_books_by_shelf
# ---------------------------------------------------------------------------

def get_books_by_shelf(args: dict, **kwargs) -> str:
    """List books on a named shelf."""
    try:
        shelf = args.get("shelf", "").strip()
        if not shelf:
            return _err("'shelf' parameter is required.")
        limit = min(int(args.get("limit", 25)), 500)

        with _connect() as conn:
            # Try exclusive shelf first
            rows = _rows_to_list(conn.execute(
                """
                SELECT b.book_id, b.book_title, a.author_name,
                       b.rating AS user_rating, b.average_rating AS global_avg,
                       b.year_first_published, b.num_pages, b.exclusive_shelf
                FROM books b
                LEFT JOIN authors a USING (author_id)
                WHERE b.exclusive_shelf LIKE ?
                ORDER BY b.rating DESC NULLS LAST, b.book_title
                LIMIT ?
                """,
                [f"%{shelf}%", limit],
            ).fetchall())

            # Also check custom shelves (book_shelves table)
            custom_rows = _rows_to_list(conn.execute(
                """
                SELECT b.book_id, b.book_title, a.author_name,
                       b.rating AS user_rating, b.average_rating AS global_avg,
                       b.year_first_published, b.num_pages, b.exclusive_shelf,
                       bs.shelf_name AS custom_shelf
                FROM book_shelves bs
                JOIN books b ON b.book_id = bs.book_id
                LEFT JOIN authors a ON a.author_id = b.author_id
                WHERE bs.shelf_name LIKE ?
                ORDER BY b.rating DESC NULLS LAST, b.book_title
                LIMIT ?
                """,
                [f"%{shelf}%", limit],
            ).fetchall())

        # Merge; prefer custom if both returned results for a non-exclusive name
        if custom_rows:
            return _ok({"shelf": shelf, "source": "custom", "books": custom_rows, "count": len(custom_rows)})
        return _ok({"shelf": shelf, "source": "exclusive", "books": rows, "count": len(rows)})
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 7. get_shelf_list
# ---------------------------------------------------------------------------

def get_shelf_list(args: dict, **kwargs) -> str:
    """All shelves and their book counts."""
    try:
        with _connect() as conn:
            exclusive = _rows_to_list(conn.execute(
                "SELECT exclusive_shelf AS shelf, COUNT(*) AS book_count "
                "FROM books GROUP BY exclusive_shelf ORDER BY book_count DESC"
            ).fetchall())

            custom = _rows_to_list(conn.execute(
                "SELECT shelf_name AS shelf, COUNT(*) AS book_count "
                "FROM book_shelves GROUP BY shelf_name ORDER BY book_count DESC"
            ).fetchall())

        return _ok({
            "exclusive_shelves": exclusive,
            "custom_shelves": custom,
        })
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 8. get_reading_timeline
# ---------------------------------------------------------------------------

def get_reading_timeline(args: dict, **kwargs) -> str:
    """Books grouped or filtered by read-date."""
    try:
        year = args.get("year")
        start_date = args.get("start_date")
        end_date = args.get("end_date")
        aggregate_by = args.get("aggregate_by", "none")
        limit = min(int(args.get("limit", 50)), 500)

        params: list = []
        date_filter = ""
        if year:
            date_filter += " AND d.date_read LIKE ?"
            params.append(f"{year}%")
        if start_date:
            date_filter += " AND d.date_read >= ?"
            params.append(start_date)
        if end_date:
            date_filter += " AND d.date_read <= ?"
            params.append(end_date)

        with _connect() as conn:
            if aggregate_by == "year":
                sql = f"""
                    SELECT
                        SUBSTR(d.date_read, 1, 4)  AS period,
                        COUNT(DISTINCT b.book_id)  AS books_read,
                        ROUND(AVG(b.rating), 2)    AS avg_user_rating
                    FROM book_dates_read d
                    JOIN books b ON b.book_id = d.book_id
                    WHERE d.date_read IS NOT NULL{date_filter}
                    GROUP BY period
                    ORDER BY period DESC
                    LIMIT ?
                """
                params.append(limit)
                rows = _rows_to_list(conn.execute(sql, params).fetchall())
                return _ok({"aggregate_by": "year", "periods": rows})

            elif aggregate_by == "month":
                sql = f"""
                    SELECT
                        SUBSTR(d.date_read, 1, 7)  AS period,
                        COUNT(DISTINCT b.book_id)  AS books_read,
                        ROUND(AVG(b.rating), 2)    AS avg_user_rating
                    FROM book_dates_read d
                    JOIN books b ON b.book_id = d.book_id
                    WHERE d.date_read IS NOT NULL{date_filter}
                    GROUP BY period
                    ORDER BY period DESC
                    LIMIT ?
                """
                params.append(limit)
                rows = _rows_to_list(conn.execute(sql, params).fetchall())
                return _ok({"aggregate_by": "month", "periods": rows})

            else:
                sql = f"""
                    SELECT
                        b.book_id, b.book_title, a.author_name,
                        b.rating AS user_rating,
                        d.date_read, b.num_pages
                    FROM book_dates_read d
                    JOIN books b ON b.book_id = d.book_id
                    LEFT JOIN authors a ON a.author_id = b.author_id
                    WHERE d.date_read IS NOT NULL{date_filter}
                    ORDER BY d.date_read DESC
                    LIMIT ?
                """
                params.append(limit)
                rows = _rows_to_list(conn.execute(sql, params).fetchall())
                return _ok({"aggregate_by": "none", "books": rows, "count": len(rows)})
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 9. search_books
# ---------------------------------------------------------------------------

def search_books(args: dict, **kwargs) -> str:
    """Search by title, author, or description keyword."""
    try:
        query = args.get("query", "").strip()
        if not query:
            return _err("'query' parameter is required.")
        shelf = args.get("shelf")
        limit = min(int(args.get("limit", 15)), 100)

        pattern = f"%{query}%"
        params: list = [pattern, pattern, pattern]
        extra = ""
        if shelf:
            extra = " AND b.exclusive_shelf = ?"
            params.append(shelf)

        sql = f"""
            SELECT
                b.book_id, b.book_title, a.author_name,
                b.rating AS user_rating, b.average_rating AS global_avg,
                b.year_first_published, b.exclusive_shelf, b.num_pages
            FROM books b
            LEFT JOIN authors a ON a.author_id = b.author_id
            WHERE (
                b.book_title LIKE ?
                OR a.author_name LIKE ?
                OR b.book_description LIKE ?
            ){extra}
            ORDER BY
                CASE WHEN b.book_title LIKE ? THEN 0 ELSE 1 END,
                b.rating DESC NULLS LAST,
                b.book_title
            LIMIT ?
        """
        params += [pattern, limit]

        with _connect() as conn:
            rows = _rows_to_list(conn.execute(sql, params).fetchall())

        return _ok({"query": query, "books": rows, "count": len(rows)})
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 10. get_book_details
# ---------------------------------------------------------------------------

def get_book_details(args: dict, **kwargs) -> str:
    """Full details for a single book."""
    try:
        book_id = args.get("book_id", "").strip()
        title = args.get("title", "").strip()

        if not book_id and not title:
            return _err("Provide either 'book_id' or 'title'.")

        with _connect() as conn:
            if book_id:
                row = conn.execute(
                    "SELECT * FROM books WHERE book_id = ?", [book_id]
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM books WHERE book_title LIKE ? ORDER BY LENGTH(book_title) LIMIT 1",
                    [f"%{title}%"],
                ).fetchone()

            if not row:
                return _err("No book found matching the given criteria.")

            book = dict(row)
            bid = book["book_id"]

            author = dict(conn.execute(
                "SELECT * FROM authors WHERE author_id = ?", [book.get("author_id")]
            ).fetchone() or {})

            genres = [r["genre"] for r in conn.execute(
                "SELECT genre FROM book_genres WHERE book_id = ? ORDER BY genre", [bid]
            ).fetchall()]

            shelves = [r["shelf_name"] for r in conn.execute(
                "SELECT shelf_name FROM book_shelves WHERE book_id = ? ORDER BY shelf_name", [bid]
            ).fetchall()]

            dates_read = [r["date_read"] for r in conn.execute(
                "SELECT date_read FROM book_dates_read WHERE book_id = ? ORDER BY date_read DESC", [bid]
            ).fetchall()]

        # Strip large/noisy fields from author for brevity
        author.pop("author_description", None)
        author.pop("author_image", None)

        return _ok({
            "book": book,
            "author": author,
            "genres": genres,
            "custom_shelves": shelves,
            "dates_read": dates_read,
        })
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 11. get_rating_distribution
# ---------------------------------------------------------------------------

def get_rating_distribution(args: dict, **kwargs) -> str:
    """How many books the user gave each star rating."""
    try:
        shelf = args.get("shelf", "read")

        with _connect() as conn:
            rows = _rows_to_list(conn.execute(
                """
                SELECT
                    rating,
                    COUNT(*) AS book_count
                FROM books
                WHERE exclusive_shelf = ?
                GROUP BY rating
                ORDER BY rating DESC NULLS LAST
                """,
                [shelf],
            ).fetchall())

            total = conn.execute(
                "SELECT COUNT(*) FROM books WHERE exclusive_shelf = ?", [shelf]
            ).fetchone()[0]

        # Add percentages and fill in any missing star values
        dist = {str(i): {"rating": i, "book_count": 0, "pct": 0.0} for i in range(5, 0, -1)}
        dist["None"] = {"rating": None, "book_count": 0, "pct": 0.0}

        for row in rows:
            key = str(row["rating"]) if row["rating"] is not None else "None"
            dist[key]["book_count"] = row["book_count"]
            dist[key]["pct"] = round(row["book_count"] / total * 100, 1) if total else 0.0

        return _ok({
            "shelf": shelf,
            "total_books": total,
            "distribution": list(dist.values()),
        })
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 12. get_unrated_read_books
# ---------------------------------------------------------------------------

def get_unrated_read_books(args: dict, **kwargs) -> str:
    """Books marked as read but not rated."""
    try:
        limit = min(int(args.get("limit", 20)), 200)

        with _connect() as conn:
            rows = _rows_to_list(conn.execute(
                """
                SELECT
                    b.book_id, b.book_title, a.author_name,
                    b.num_pages, b.year_first_published,
                    MAX(d.date_read) AS last_date_read
                FROM books b
                LEFT JOIN authors a ON a.author_id = b.author_id
                LEFT JOIN book_dates_read d ON d.book_id = b.book_id
                WHERE b.exclusive_shelf = 'read'
                  AND (b.rating IS NULL OR b.rating = 0)
                GROUP BY b.book_id
                ORDER BY last_date_read DESC NULLS LAST, b.book_title
                LIMIT ?
                """,
                [limit],
            ).fetchall())

        return _ok({"unrated_read_books": rows, "count": len(rows)})
    except Exception as exc:
        return _err(str(exc))


# ---------------------------------------------------------------------------
# 13. lookup_book
# ---------------------------------------------------------------------------

def lookup_book(args: dict, **kwargs) -> str:
    """Exact title+author existence check (case-insensitive)."""
    try:
        title = args.get("title", "").strip()
        author = args.get("author", "").strip()
        if not title or not author:
            return _err("Both 'title' and 'author' parameters are required.")
        shelf = args.get("shelf")

        params: list = [title.lower(), author.lower()]
        extra = ""
        if shelf:
            extra = " AND b.exclusive_shelf = ?"
            params.append(shelf)

        sql = f"""\
            SELECT
                b.book_id, b.book_title, a.author_name,
                b.rating AS user_rating, b.average_rating AS global_avg,
                b.year_first_published, b.num_pages, b.exclusive_shelf
            FROM books b
            LEFT JOIN authors a ON a.author_id = b.author_id
            WHERE LOWER(b.book_title) = ?
              AND LOWER(a.author_name) = ?{extra}
            LIMIT 1
        """

        with _connect() as conn:
            row = conn.execute(sql, params).fetchone()

        if row:
            return _ok({
                "found": True,
                "book": dict(row),
            })
        return _ok({
            "found": False,
            "message": f"No book titled '{title}' by '{author}' found in the library.",
        })
    except Exception as exc:
        return _err(str(exc))
