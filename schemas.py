"""
Goodreads plugin — tool schemas.

Each schema's description is what the LLM reads to decide when and how to
call the tool.  Descriptions are written from the agent's perspective:
the database contains the *user's* Goodreads library, so the agent queries
it on the user's behalf and reports back what it finds.
"""

GET_READING_STATS = {
    "name": "get_reading_stats",
    "description": (
        "Return high-level reading statistics from the user's Goodreads library: "
        "total books on each shelf (read, currently-reading, to-read, custom), "
        "total ratings the user has given, the user's overall average rating, "
        "number of reviews written, and average book length (pages) for books "
        "the user has read.  Use this first when someone asks for a general "
        "overview of the user's reading habits or 'how many books have they read'."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GET_TOP_RATED_BOOKS = {
    "name": "get_top_rated_books",
    "description": (
        "Return the books the user rated most highly (5 stars first, then 4, etc.). "
        "Optionally filter to a specific exclusive shelf (e.g. 'read', 'currently-reading') "
        "and limit the number of results.  Use this to answer questions like "
        "'what are the user's favourite books', 'what did they love', or "
        "'which books did the user rate 5 stars'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "shelf": {
                "type": "string",
                "description": (
                    "Exclusive shelf to filter by, e.g. 'read' or 'currently-reading'. "
                    "Omit to search across all shelves."
                ),
            },
            "min_rating": {
                "type": "integer",
                "description": "Only return books the user rated >= this value (1–5). Default 4.",
                "minimum": 1,
                "maximum": 5,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of books to return. Default 10.",
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": [],
    },
}

GET_BOOKS_BY_GENRE = {
    "name": "get_books_by_genre",
    "description": (
        "Return books from the user's library that belong to a specific genre "
        "(e.g. 'fantasy', 'science-fiction', 'mystery', 'romance', 'history', "
        "'biography', 'self-help').  Genre matching is case-insensitive and partial "
        "(so 'sci' matches 'science-fiction').  Optionally filter to a shelf and/or "
        "a minimum user rating.  Use this when someone asks what the user has read "
        "in a particular genre."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "genre": {
                "type": "string",
                "description": "Genre keyword to search for (partial match, case-insensitive).",
            },
            "shelf": {
                "type": "string",
                "description": "Exclusive shelf filter, e.g. 'read'. Omit to search all shelves.",
            },
            "min_rating": {
                "type": "integer",
                "description": "Only include books the user rated at or above this value. Omit to include all.",
                "minimum": 1,
                "maximum": 5,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results to return. Default 20.",
                "minimum": 1,
                "maximum": 200,
            },
        },
        "required": ["genre"],
    },
}

GET_GENRE_PREFERENCES = {
    "name": "get_genre_preferences",
    "description": (
        "Aggregate reading statistics from the user's library broken down by genre: "
        "number of books read per genre, the user's average rating per genre, and the "
        "top-rated book in each genre.  This is the best tool to answer questions about "
        "the user's genre preferences, 'which genres do they enjoy most', or 'do they "
        "prefer fiction or non-fiction'.  Optionally restrict to books on a specific "
        "shelf (default: 'read')."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "shelf": {
                "type": "string",
                "description": "Shelf to restrict to. Default is 'read'.",
            },
            "min_books": {
                "type": "integer",
                "description": "Only show genres with at least this many books. Default 1.",
                "minimum": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of genres to return, ordered by avg rating desc. Default 20.",
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": [],
    },
}

GET_AUTHOR_STATS = {
    "name": "get_author_stats",
    "description": (
        "Return per-author reading statistics from the user's library: number of books "
        "read by each author, the user's average rating for that author's books, and the "
        "titles read.  Useful for 'which authors has the user read the most', "
        "'does the user like [author]', or finding the user's favourite authors based "
        "on their ratings.  Optionally filter by shelf or sort by book count vs. "
        "average rating."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "shelf": {
                "type": "string",
                "description": "Restrict to books on this shelf (e.g. 'read'). Omit for all shelves.",
            },
            "sort_by": {
                "type": "string",
                "enum": ["avg_rating", "book_count"],
                "description": "Sort by the user's average rating or number of books read. Default 'avg_rating'.",
            },
            "min_books": {
                "type": "integer",
                "description": "Only include authors with at least this many books in the library. Default 1.",
                "minimum": 1,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of authors to return. Default 20.",
                "minimum": 1,
                "maximum": 200,
            },
            "author_name": {
                "type": "string",
                "description": "Filter to a specific author name (partial, case-insensitive). Omit to return all authors.",
            },
        },
        "required": [],
    },
}

GET_BOOKS_BY_SHELF = {
    "name": "get_books_by_shelf",
    "description": (
        "List all books on a given shelf in the user's library, ordered by the user's "
        "rating (highest first) then by title.  Works for both exclusive shelves "
        "('read', 'currently-reading', 'to-read') and custom tag-style shelves "
        "(e.g. 'favorites', 'owned', 'kindle').  Use this when someone asks what is "
        "on a particular shelf, or wants to see the user's 'to-read' list or "
        "'currently reading' list."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "shelf": {
                "type": "string",
                "description": "Shelf name (exact or partial match, case-insensitive).",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of books to return. Default 25.",
                "minimum": 1,
                "maximum": 500,
            },
        },
        "required": ["shelf"],
    },
}

GET_SHELF_LIST = {
    "name": "get_shelf_list",
    "description": (
        "Return a list of every shelf in the user's library (both exclusive shelves like "
        "'read' and custom tag shelves), along with the count of books on each.  "
        "Use this when the available shelves are unknown, or when someone asks "
        "'what shelves does the user have' or 'how is their library organised'."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GET_READING_TIMELINE = {
    "name": "get_reading_timeline",
    "description": (
        "Return books from the user's library grouped by the year (and optionally month) "
        "they were marked as read, showing title, author, user rating, and date.  "
        "Use this to answer 'what did the user read in 2023', 'how many books did they "
        "read last year', or to spot reading-pace trends over time.  "
        "Optionally filter to a date range or return yearly/monthly aggregates."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "year": {
                "type": "integer",
                "description": "Filter to a specific year (e.g. 2023). Omit for all years.",
            },
            "start_date": {
                "type": "string",
                "description": "ISO date lower bound, inclusive (e.g. '2022-01-01').",
            },
            "end_date": {
                "type": "string",
                "description": "ISO date upper bound, inclusive (e.g. '2022-12-31').",
            },
            "aggregate_by": {
                "type": "string",
                "enum": ["year", "month", "none"],
                "description": (
                    "'year' returns one row per year with book count and avg user rating; "
                    "'month' groups by year-month; "
                    "'none' (default) returns individual books ordered by date desc."
                ),
            },
            "limit": {
                "type": "integer",
                "description": "Maximum rows to return. Default 50.",
                "minimum": 1,
                "maximum": 500,
            },
        },
        "required": [],
    },
}

SEARCH_BOOKS = {
    "name": "search_books",
    "description": (
        "Full-text search across book titles, author names, and book descriptions "
        "in the user's library.  Returns matching books with their shelf, user rating, "
        "and publication year.  Use this when someone asks about a specific book "
        "or author by name, or wants to find books whose titles contain a keyword."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search term (partial match against title, author name, or description).",
            },
            "shelf": {
                "type": "string",
                "description": "Restrict to a specific shelf. Omit to search the whole library.",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum results. Default 15.",
                "minimum": 1,
                "maximum": 100,
            },
        },
        "required": ["query"],
    },
}

GET_BOOK_DETAILS = {
    "name": "get_book_details",
    "description": (
        "Return full details for a single book in the user's library: title, author, "
        "description, genres, shelves, the user's rating, global average rating, "
        "page count, publication year, and dates the user marked it as read.  "
        "Use this when someone wants to know everything about a specific book, "
        "or after search_books finds a candidate and more detail is needed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "book_id": {
                "type": "string",
                "description": "The book_id from a previous search_books or other tool result.",
            },
            "title": {
                "type": "string",
                "description": (
                    "Alternatively, look up by title (partial, case-insensitive). "
                    "If multiple books match, the closest title match is returned."
                ),
            },
        },
        "required": [],
    },
}

GET_RATING_DISTRIBUTION = {
    "name": "get_rating_distribution",
    "description": (
        "Show how many books the user rated 1, 2, 3, 4, and 5 stars, "
        "as counts and percentages.  Also returns the number of read books "
        "with no rating.  Use this to understand the user's rating behaviour: "
        "'are they a generous rater', 'do they finish books they dislike', "
        "or to calibrate what a 4-star rating means for this particular user."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "shelf": {
                "type": "string",
                "description": "Restrict distribution to a shelf. Default 'read'.",
            },
        },
        "required": [],
    },
}

GET_UNRATED_READ_BOOKS = {
    "name": "get_unrated_read_books",
    "description": (
        "List books that are on the user's 'read' shelf but have no rating.  "
        "Useful for finding gaps in the rating data, or surfacing books the "
        "user finished but never rated.  "
        "Returns title, author, page count, and date read."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of books to return. Default 20.",
                "minimum": 1,
                "maximum": 200,
            },
        },
        "required": [],
    },
}

LOOKUP_BOOK = {
    "name": "lookup_book",
    "description": (
        "Check whether a specific book by a specific author exists in the user's "
        "library.  Performs case-insensitive exact matching on both title and author "
        "name.  Returns a definitive yes/no answer with matching book details when "
        "found.  Use this when someone asks 'does the user have [title] by [author]' "
        "or 'is [title] by [author] on their shelves' — i.e. precise existence checks "
        "where search_books would return too many fuzzy matches."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Exact book title to match (case-insensitive).",
            },
            "author": {
                "type": "string",
                "description": "Exact author name to match (case-insensitive).",
            },
            "shelf": {
                "type": "string",
                "description": (
                    "Restrict to a specific shelf (e.g. 'read', 'to-read'). "
                    "Omit to search the entire library."
                ),
            },
        },
        "required": ["title", "author"],
    },
}
