# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

This project requires [uv](https://github.com/astral-sh/uv) for dependency management. Run `. ./activate.sh` to set up the development environment.

## Core Architecture

The project provides async S3 utilities for efficient bucket object listing with these key components:

- **S3BucketObjects** (`src/async_s3/s3_bucket_objects.py`): Core class implementing async S3 object listing with semaphore-based concurrency control and folder traversal
- **group_by_prefix** (`src/async_s3/group_by_prefix.py`): Utility for grouping S3 prefixes to optimize folder requests
- **CLI interface** (`src/async_s3/main.py`): Rich-click based command-line tool with `ls` and `du` commands

The main async iterator pattern is in `S3BucketObjects.iter()` which yields object pages as they're collected asynchronously, with deduplication to handle objects listed multiple times when grouping by prefixes.

## Commands

### Development Tasks (using invoke)
- `invoke --list` - List all available tasks
- `invoke reqs` - Upgrade requirements and pre-commit hooks
- `invoke pre` - Run pre-commit checks (ruff linting/formatting, mypy)
- `invoke compile-requirements` - Update requirements.txt files from .in files

### Testing
- `pytest` - Run tests (includes doctests via pytest.ini configuration)

### Version Management
- `invoke version` - Show current version
- `invoke ver-release` - Bump release version
- `invoke ver-feature` - Bump feature version
- `invoke ver-bug` - Bump bug fix version

### Documentation
- `invoke docs-en` - Preview English documentation
- `invoke docs-ru` - Preview Russian documentation

## Code Quality Tools

- **Ruff**: Linting and formatting with extensive rule set (99-100 char line length)
- **Mypy**: Type checking for source code (excludes tests)
- **Pre-commit**: Automated quality checks on commit

Ruff configuration uses comprehensive rules including Pylint, security, complexity, and code style checks. Tests have relaxed formatting rules (99 chars vs 100 for source).
