"""
Goodreads plugin — registration entry point.

Hermes calls register(ctx) exactly once at startup.
Every tool is paired with its schema (what the LLM sees) and
its handler (the code that runs).
"""

import logging

from . import schemas, tools

logger = logging.getLogger(__name__)

_TOOLSET = "goodreads"

_TOOL_MAP = [
    ("get_reading_stats",      schemas.GET_READING_STATS,      tools.get_reading_stats),
    ("get_top_rated_books",    schemas.GET_TOP_RATED_BOOKS,     tools.get_top_rated_books),
    ("get_books_by_genre",     schemas.GET_BOOKS_BY_GENRE,      tools.get_books_by_genre),
    ("get_genre_preferences",  schemas.GET_GENRE_PREFERENCES,   tools.get_genre_preferences),
    ("get_author_stats",       schemas.GET_AUTHOR_STATS,        tools.get_author_stats),
    ("get_books_by_shelf",     schemas.GET_BOOKS_BY_SHELF,      tools.get_books_by_shelf),
    ("get_shelf_list",         schemas.GET_SHELF_LIST,          tools.get_shelf_list),
    ("get_reading_timeline",   schemas.GET_READING_TIMELINE,    tools.get_reading_timeline),
    ("search_books",           schemas.SEARCH_BOOKS,            tools.search_books),
    ("get_book_details",       schemas.GET_BOOK_DETAILS,        tools.get_book_details),
    ("get_rating_distribution",schemas.GET_RATING_DISTRIBUTION, tools.get_rating_distribution),
    ("get_unrated_read_books", schemas.GET_UNRATED_READ_BOOKS,  tools.get_unrated_read_books),
    ("lookup_book",           schemas.LOOKUP_BOOK,              tools.lookup_book),
]


def register(ctx):
    """Register all Goodreads tools with Hermes."""
    for name, schema, handler in _TOOL_MAP:
        ctx.register_tool(
            name=name,
            toolset=_TOOLSET,
            schema=schema,
            handler=handler,
        )
    logger.info(
        "goodreads plugin: registered %d tools (toolset=%r)",
        len(_TOOL_MAP),
        _TOOLSET,
    )
