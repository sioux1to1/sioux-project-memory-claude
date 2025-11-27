# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Claude Code skill that provides persistent project memory using PostgreSQL. It automatically identifies projects via git repo + branch and stores decisions, TODOs, context, patterns, and notes.

## Architecture

- `scripts/memory_api.py` - Main Python CLI that handles all database operations
- `scripts/setup_db.sql` - PostgreSQL schema with full-text search (Portuguese)
- `config.json` - Database connection configuration
- `SKILL.md` - Instructions that Claude follows for automatic behavior

The API uses git remote URL + branch to identify projects, enabling per-project and per-branch memory isolation.

## Commands

All commands auto-detect git repo/branch from current directory:

```bash
# Get project summary (run at session start)
python scripts/memory_api.py summary

# Add entries
python scripts/memory_api.py add --type decision --title "Title" --content "Details" --tags "tag1,tag2" --priority high

# List by type
python scripts/memory_api.py decisions
python scripts/memory_api.py todos
python scripts/memory_api.py context
python scripts/memory_api.py list --type pattern

# Search (uses PostgreSQL full-text search)
python scripts/memory_api.py search "query"
python scripts/memory_api.py search "query" --all-branches

# Update status
python scripts/memory_api.py update --id <uuid> --status completed
```

## Database Setup

```bash
pip install psycopg2-binary
createdb sioux_project_memory
psql sioux_project_memory < scripts/setup_db.sql
```

## Entry Types

- `decision` - Technical decisions (libraries, architecture)
- `todo` - Future improvements, pending tasks
- `context` - Project requirements, business rules
- `pattern` - Code conventions
- `note` - General important notes

## Priorities

`low`, `medium` (default), `high`, `critical`

## Status

`active` (default), `completed`, `archived`, `deprecated`
