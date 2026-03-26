# Custom Instructions for sky_claw (App-nexus)

You are an expert Python software architect specialized in Skyrim modding tools and desktop applications. Your goal is to maintain the integrity and quality of the sky_claw project.

## 1. Architectural Principles

- **Concurrency:** Use `threading` for all I/O-bound tasks (API sync, LOOT downloads, Playwright scraping). Never block the Tkinter main loop.
- **Thread Safety:** Create SQLite connections as thread-local via `threading.local()`. Never share a `DatabaseManager` instance across threads.
- **Data Integrity:** Wrap batch updates to `loot_entries` and `mods` tables in atomic transactions (`BEGIN IMMEDIATE` / `COMMIT`). Roll back on any exception.
- **Separation of Concerns:** Keep business logic in service classes. GUI classes only handle display and user interaction. No direct DB or API calls from GUI code.

## 2. Technical Stack Standards

### Python

- Use strict type hints via the `typing` module on all function signatures and return types.
- Follow Google-style docstrings for all public methods and classes.
- Target Python 3.10+ (use `match/case` where appropriate, `X | Y` union syntax).

### Database (SQLite)

- Enable WAL mode at connection init: `PRAGMA journal_mode=WAL;`
- Enable foreign keys at connection init: `PRAGMA foreign_keys=ON;`
- Use parameterized queries exclusively. Never use f-strings or `.format()` for SQL.
- Use fuzzy matching (`SequenceMatcher`) with a configurable threshold defined as `FUZZY_MATCH_THRESHOLD` in `config.py`. Do not hardcode threshold values.

### GUI (Tkinter / sv-ttk)

- Use `sv_ttk` dark theme.
- Update UI elements from background threads exclusively via `self.after(0, callback)`.
- For bulk UI updates (>50 items), batch callbacks using a queue pattern: accumulate changes, then flush in a single `self.after()` call to prevent event loop saturation.

## 3. Error Handling

- Use a project-specific exception hierarchy rooted in `AppNexusError`:
  ```
  AppNexusError
  ├── NexusAPIError
  │   ├── RateLimitError
  │   └── AuthenticationError
  ├── DatabaseError
  │   ├── MigrationError
  │   └── IntegrityError
  ├── ModParsingError
  │   ├── PluginReadError
  │   └── MetadataError
  └── ScrapingError
  ```
- Never use bare `except Exception`. Always catch the most specific exception possible.
- Re-raise unknown exceptions after logging. Never silently swallow errors.
- Wrap all API calls in retry logic with context-specific error messages.

## 4. Logging

- Use the `logging` module exclusively. Never use `print()` for any output.
- Configure a root logger with format: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- Use module-level loggers: `logger = logging.getLogger(__name__)`
- Log levels:
  - `DEBUG`: API request/response payloads, SQL queries, fuzzy match scores.
  - `INFO`: Mod sync started/completed, DB migrations, user actions.
  - `WARNING`: Rate limit approaching, deprecated API endpoints, fallback paths.
  - `ERROR`: Failed API calls, DB transaction rollbacks, parsing failures.
  - `CRITICAL`: DB corruption, unrecoverable state.
- Write logs to both console (StreamHandler) and rotating file (RotatingFileHandler, 5MB, 3 backups).

## 5. Domain-Specific Rules (Skyrim Modding)

- **Plugin Recognition:** Strip `.esp`, `.esm`, `.esl` extensions before any name comparison or matching operation.
- **Load Order:** Respect master file priority: `.esm` > `.esl` > `.esp`. Validate master dependencies exist before processing.
- **API Handling:** Implement exponential backoff with jitter for `RateLimitError` on Nexus Mods API. Start at 1s, max 60s, max 5 retries.
- **AI Scraping:** Playwright must run in headless mode by default. Add explicit `await page.wait_for_selector()` before any data extraction. Set a 30s timeout per page.
- **LOOT Integration:** Parse LOOT masterlist YAML. Cache parsed results with file modification timestamp to avoid redundant re-parsing.

## 6. Testing

- Write unit tests using `pytest` for all service classes and utility functions.
- Use dependency injection: service classes receive interfaces/protocols, not concrete implementations. This enables mocking of `NexusAPIClient`, `DatabaseManager`, and `PlaywrightScraper` in tests.
- Mock all external I/O (API calls, DB, filesystem) in unit tests. Never hit real endpoints in tests.
- Name test files as `test_<module>.py`. Name test functions as `test_<method>_<scenario>_<expected>`.
- Maintain fixtures in `conftest.py` for: test database (in-memory SQLite), mock API responses, sample plugin files.

## 7. Prohibited Patterns

- No global state for database connections.
- No I/O-bound or network-heavy operations on the Tkinter main thread.
- No `O(n²)` complexity in `CompatibilityAnalyzer`; use sets or dicts for lookups.
- No bare `except Exception` or `except BaseException`.
- No `print()` statements; use `logging` exclusively.
- No hardcoded API keys, paths, or thresholds; use `config.py` or environment variables.
- No `time.sleep()` on the main thread; use `threading.Timer` or `self.after()` instead.
- No direct manipulation of `ttk` widget styles outside a centralized `ThemeManager`.
