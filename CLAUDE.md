# Sky-Claw Project Guidelines

## ⚠️ Architectural Guardrails (CRITICAL)

### Git & File Watcher Safety
**Regla Inquebrantable de Arquitectura:** Cualquier herramienta nueva que integres en el futuro (compiladores, generadores de assets, bases de datos locales vectoriales) que produzca archivos dinámicos, **DEBE ser declarada en el `.gitignore` antes de ejecutarse por primera vez.**

**Razonamiento:** El File Watcher de Antigravity IDE (basado en el event loop de Node.js) puede entrar en un estado de deadlock o OOM (Out Of Memory) si se ve inundado por ráfagas masivas de cambios de archivos en directorios no ignorados (como caches de compilación o logs). Mantener el `.gitignore` actualizado es vital para la estabilidad de la orquestación.

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
