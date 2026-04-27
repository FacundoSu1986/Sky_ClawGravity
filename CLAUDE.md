# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Project Overview

**Sky-Claw** is an autonomous agent for managing Skyrim SE/AE mods through Mod Organizer 2 (MO2). It features:
- Multi-LLM support (Claude, OpenAI, DeepSeek, Ollama)
- Async architecture with Tkinter GUI
- Zero-Trust security with sandboxing and HITL approval (Telegram)
- SQLite database with async operations
- Integration with LOOT, xEdit, and Nexus Mods

**Tech Stack:** Python 3.11+, Tkinter + sv-ttk, SQLite (WAL mode), Pydantic, aiohttp, Playwright

---

## Quick Start Commands

### Setup
```bash
# Install dependencies
pip install -e ".[dev]"

# Auto-detect MO2 installation and configure
python scripts/first_run.py
```

### Run
```bash
# GUI mode (Tkinter)
python -m sky_claw --mode gui

# Telegram HITL interactive mode
python -m sky_claw --mode telegram

# Terminal/CLI mode
python -m sky_claw --mode cli
```

### Code Quality
```bash
# Lint with Ruff
ruff check sky_claw/ tests/

# Format code
ruff format sky_claw/ tests/

# Type check with Mypy (non-blocking, progressive typing)
mypy sky_claw/ --ignore-missing-imports

# Run tests with coverage (target: ≥49%)
pytest --cov=sky_claw --cov-fail-under=49 tests/

# Run single test
pytest tests/test_<module>.py::test_<function> -v
```

### Security & Validation
```bash
# SAST (Source code analysis)
bandit -r sky_claw/ -ll

# SCA (Software composition analysis)
pip-audit --skip-editable

# Check for secrets in diffs
git diff | /skill:security-review
```

### Build
```bash
# Build Windows executable (requires PyInstaller)
pip install pyinstaller
pyinstaller sky_claw.spec --clean
```

---

## Architecture Overview

### Module Layout

```
sky_claw/
├── agent/              → LLM router, providers (Claude/OpenAI/DeepSeek/Ollama), Pydantic schemas
├── core/               → Business logic, async tool registry, compatibility analyzer
├── db/                 → Async SQLite manager (WAL, foreign_keys=ON, threading.local())
├── gui/                → Tkinter + sv-ttk frontend (MVC pattern)
├── security/           → PathValidator (sandboxing), NetworkGateway (whitelist), HITLGuard
├── orchestrator/       → Global agent orchestration, DLQ (dead-letter queue)
├── mo2/                → Mod Organizer 2 integration (modlist.txt parsing)
├── loot/               → LOOT masterlist YAML parser + caching
├── xedit/              → xEdit headless runner (script generation)
├── scraper/            → Playwright-based web scraping (Nexus, Patreon, GitHub, Mega)
├── comms/              → Telegram webhook integration for HITL approvals
├── tools/              → Async tool definitions (search_mod, detect_conflicts, run_loot_sort, etc.)
├── validators/         → Pydantic input validation models
├── discovery/          → Plugin metadata discovery
├── fomod/              → FOMOD installer XML parser
├── web/                → Optional NiceGUI web interface (experimental)
├── app_context.py      → AppContext singleton with asyncio.Lock for initialization
├── config.py           → SystemPaths, FUZZY_MATCH_THRESHOLD, global config
└── logging_config.py   → Structured logging setup
```

### Data Flow
```
User Input (GUI/CLI/Telegram)
    ↓
LLMRouter (message dispatch)
    ↓
LLMProvider Interface (Claude/OpenAI/DeepSeek/Ollama)
    ↓
AsyncToolRegistry (async tool execution)
    │
    ├→ search_mod() → AsyncModRegistry (SQLite fuzzy search)
    ├→ check_load_order() → MO2Controller (modlist.txt validation)
    ├→ detect_conflicts() → SQL JOINs on dependencies
    ├→ run_loot_sort() → LOOTRunner (headless LOOT)
    ├→ run_xedit_script() → XEditRunner (xEdit commands)
    └→ download_mod() → NexusDownloader + HITLGuard (Telegram approval)
    ↓
Output → GUI/Telegram/CLI response
```

---

## Critical Architectural Constraints

### P0: Zero-Trust Security (Non-negotiable)

- **PathValidator**: All file operations confined to `SystemPaths.modding_root()`. Validate with `PathValidator.validate()`.
- **NetworkGateway**: Outbound connections whitelisted (*.nexusmods.com, api.telegram.org, openai.com, etc.). Reject unlisted domains.
- **HITLGuard**: Before downloading from external hosts (GitHub, Patreon, Mega), pause and request Telegram approval.
- **SQL Injection**: Only parameterized queries. **Forbidden:** f-strings or `.format()` in SQL.
- **LLM Output**: Validate all LLM responses with Pydantic (`model_validate_json`). **Forbidden:** regex parsing of free text.

**Violation = CVSS ≥ 7.0. Use `/skill:security-review` before merge.**

### P1: Concurrency & UI (Invariants)

- **Tkinter**: Main thread only. I/O (APIs, DB, Playwright) must run off-thread via `threading.Timer`, `asyncio.TaskGroup`, or `self.after()`.
- **Database**: `threading.local()` per thread. Never share `DatabaseManager` instances.
- **Async**: `BEGIN IMMEDIATE` for batch transactions. Auto-rollback on exception.
- **UI Updates**: Always `self.after(0, callback)`. For >50 items, batch via queue to avoid event loop saturation.
- **Prohibited**: `time.sleep()` in main thread, blocking I/O on UI thread, shared DB connections.

### P2: SRE & Error Handling

- **Exceptions**: Use typed `AppNexusError` hierarchy. **Forbidden:** bare `except Exception`.
- **Logging**: Use `logging` module only. **Forbidden:** `print()`. Include context (user ID, mod name, error code).
- **Retry Strategy**: Exponential backoff (1s → 60s, max 5 attempts) for Nexus API rate limits.
- **Skyrim Domain**: Clean `.esp`/`.esm`/`.esl` extensions before comparison. Order: `.esm` > `.esl` > `.esp`.

### P3: Testing & Mocks

- **Pytest**: In `tests/conftest.py`, inject mocks:
  - SQLite → in-memory `:memory:` database
  - LLMs → `AsyncMock` returning fixed Pydantic models
  - Network → `aioresponses` for aiohttp mocks
- **Coverage**: Minimum 49% (`pytest --cov-fail-under=49`).
- **Naming**: `test_<module>_<scenario>_<expected>.py`
- **Dependency Injection**: Services take `Protocol`s, not concrete implementations.

---

## Development Patterns

### Adding a New Async Tool

1. Define schema in `sky_claw/agent/schemas.py` (Pydantic).
2. Implement in `sky_claw/tools/<tool_name>.py` with type hints and docstrings.
3. Register in `sky_claw/core/tool_registry.py` (AsyncToolRegistry).
4. Add test in `tests/test_<tool_name>.py` with SQLite in-memory + LLM mock.
5. Update documentation in `TECHNICAL_SPEC_*.md`.

### Adding a New LLM Provider

1. Extend `sky_claw/agent/llm_provider.py` (LLMProvider base class).
2. Implement `acomplete()`, `astream()`, `validate_key()`.
3. Register in `sky_claw/agent/llm_router.py`.
4. Add tests with `AsyncMock`.
5. Document in config.py and first_run.py.

### Security Review Checklist

Before every PR merge, verify:
- [ ] No hardcoded secrets, API keys, or paths (use `config.py` or env vars).
- [ ] SQL only uses parameterized queries (`:param` syntax).
- [ ] All file I/O uses `PathValidator.validate()`.
- [ ] Network calls checked against `NetworkGateway.is_allowed()`.
- [ ] LLM outputs parsed with Pydantic, not regex.
- [ ] No `time.sleep()` on main thread.
- [ ] Shared state protected by `asyncio.Lock` or `threading.Lock`.
- [ ] Logging has context (user ID, operation, error code).

Use `/skill:security-review` to automate this.

---

## CI/CD Pipeline (5 Gates)

| Gate | Tool | Command | Threshold |
|------|------|---------|-----------|
| 1. Lint | Ruff | `ruff check . && ruff format --check .` | Zero errors |
| 2. Type | Mypy | `mypy sky_claw/` | Non-blocking (progressive) |
| 3. Test | Pytest | `pytest --cov-fail-under=49` | 49% coverage |
| 4. Security | Bandit + pip-audit | `bandit -r sky_claw/ && pip-audit` | No high/critical CVE |
| 5. Build | PyInstaller | `pyinstaller sky_claw.spec` | Executable succeeds |

All gates must pass for builds to succeed.

---

## Configuration & Secrets

- **Config**: `~/.sky_claw/config.toml` (auto-generated by `first_run.py`)
- **Secrets**: API keys stored in OS keyring via `keyring` module. **Never hardcode.**
- **Environment**: Override via env vars:
  ```bash
  CLAUDE_API_KEY=sk-... OPENAI_API_KEY=sk-... python -m sky_claw
  ```
- **Telegram HITL**: Token in `~/.sky_claw/config.toml` under `[telegram]`

---

## Common Gotchas

1. **Fuzzy Matching**: Mod names use `SequenceMatcher` with `FUZZY_MATCH_THRESHOLD` (default 0.6). Tunable in `config.py`.
2. **LOOT Caching**: Parsed YAML cached by file mtime. Invalidate by touching LOOT masterlist.
3. **xEdit Scripts**: Must use xEdit-specific syntax. Validate with `XEditValidator` before execution.
4. **MO2 Paths**: Auto-detected on first run. Override in config.toml under `[paths]`.
5. **Load Order**: Always respect `.esm` > `.esl` > `.esp` priority. Use `LoadOrderValidator`.
6. **Playwright Timeouts**: 30s default per page. Increase for slow networks via config.

---

## Useful Resources

- [Copilot Instructions (Titan v7.0)](.github/copilot-instructions.md) — Staff-level constraints (Zero-Trust, concurrency, testing)
- `TECHNICAL_SPEC_DISPATCHER.md` — AsyncToolRegistry design
- `TECHNICAL_SPEC_DLQ.md` — Dead-letter queue pattern for failures
- `CODE_REVIEW_RESOLUTION.md` — Past issues and resolutions
- `SECURITY.md` — Security policy overview

---

## Using Claude Code Skills for Sky-Claw

### Enabled Skills
- **`/skill:security-review`** — Pre-merge security audit (P0: Zero-Trust, SQL, paths, secrets)
- **`/skill:review`** — Peer review for PRs
- **`/skill:simplify`** — Detect duplication and quality issues
- **`/skill:init`** — Update CLAUDE.md (this file)

### Recommended Agents
- **`Explore`** — Map 20+ modules, find dependencies (use for `grep` + `find` parallelization)
- **`Plan`** — Design architectural changes (multi-module refactors, new features)
- **`general-purpose`** — Fallback for debugging and one-off tasks

### GitHub MCP Tools (Pre-authorized)
- Read-only: `get_file_contents`, `list_commits`, `pull_request_read`
- Automated: `subscribe_pr_activity` (listen to CI failures, review comments)
- Security: `run_secret_scanning` (check diffs for leaked secrets)

---

## Questions?

For Sky-Claw-specific domain questions, refer to [.github/copilot-instructions.md](.github/copilot-instructions.md) or open an issue. For Claude Code usage, run `/help` or visit https://github.com/anthropics/claude-code/issues.
