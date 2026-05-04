## Git & File Watcher Safety

**Regla Inquebrantable de Arquitectura:** Cualquier herramienta nueva que integres en el futuro (compiladores, generadores de assets, bases de datos locales vectoriales) que produzca archivos dinámicos, **DEBE ser declarada en el `.gitignore` antes de ejecutarse por primera vez.**

Esto protegerá el event loop de Antigravity y mantendrá la orquestación estable.
