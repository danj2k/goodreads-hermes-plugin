# Project: Goodreads Plugin

## Purpose

A Hermes Agent plugin that queries a user's local Goodreads SQLite database export to surface reading preferences, history, genre affinities, author statistics, and shelf contents — without requiring the user to write SQL.

This exists because LLM agents need structured access to personal reading data to answer natural-language questions about books, and the Goodreads export is a widely-available but under-documented SQLite schema.

## Goals

- Provide a natural-language interface to a user's Goodreads library data
- Return meaningful, pre-computed aggregations (not raw rows)
- Be safe by default: read-only database access, no side effects
- Fit cleanly into Hermes Agent's tool/plugin architecture

## Non-goals

- Writing to the Goodreads database
- Importing/exporting data from external sources
- Maintaining a separate database or sync process
- Providing a web UI or REST API

## Constraints

- Requires `GOODREADS_DB_PATH` environment variable pointing to a valid SQLite database
- Database must follow the schema exported by the companion scraper (`goodreads-user-scraper`)
- Plugin runs inside Hermes Agent, so all tools return JSON strings and never raise exceptions
- SQLite WAL mode is assumed (read-only connections are safe)
