# Sky-Claw — Agent & AI Guidelines

> This file is read by all AI agents, assistants, and IDE extensions working on the Sky-Claw ecosystem. Rules here take precedence over generic conventions.

---

## PREVENCIÓN

Como regla inquebrantable de arquitectura para el ecosistema Sky-Claw: cualquier herramienta nueva que integres en el futuro (compiladores, generadores de assets, bases de datos locales vectoriales) que produzca archivos dinámicos, debe ser declarada en el `.gitignore` antes de ejecutarse por primera vez. Esto protegerá el event loop de Antigravity y mantendrá la orquestación estable.

---

## Project Structure
- `sky_claw/`: Main package code.
- `tests/`: Test suite.
- `logs/`: Application logs (Ignored by Git).
- `.antigravity/`: IDE-specific metadata and session state.

## Tech Stack
- **Core:** Python 3.14+
- **Database:** Async SQLite
- **GUI:** Tkinter + sv-ttk
- **Orchestration:** Antigravity AI Agentic System
