# DB-001: Diagnóstico de Esquemas `mods` — Fase 1

> **Fecha:** 2026-04-28 | **Alcance:** Análisis de 3 definiciones de tabla `mods`  
> **Estado:** Diagnóstico completo — pendiente Fase 2 (migración)

---

## 1. Fuentes Identificadas

| # | Archivo | Clase/Módulo | Rol | DB física |
|---|---------|-------------|-----|-----------|
| S1 | `sky_claw/core/database.py:52` | `DatabaseAgent` | GUI / Frontend | `skyclaw_gui.db` |
| S2 | `sky_claw/db/registry.py:24` | `ModRegistry` (sync) | Backend sync | `mod_registry.db` |
| S3 | `sky_claw/db/async_registry.py:38` | `AsyncModRegistry` | Backend async | `mod_registry.db` |

**Hallazgo clave:** S2 y S3 son **idénticos** en estructura. S1 es un esquema completamente diferente orientado a GUI.

---

## 2. Esquema S1 — `database.py` (GUI)

```sql
CREATE TABLE IF NOT EXISTS mods (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    version     TEXT,
    size_mb     REAL DEFAULT 0,
    status      TEXT DEFAULT 'inactive',
    source      TEXT,
    installed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP
);
```

**Columnas (8):** `id`, `name`, `version`, `size_mb`, `status`, `source`, `installed_at`, `updated_at`

---

## 3. Esquema S2/S3 — `registry.py` / `async_registry.py` (Backend)

```sql
CREATE TABLE IF NOT EXISTS mods (
    mod_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nexus_id        INTEGER UNIQUE NOT NULL,
    name            TEXT    NOT NULL,
    version         TEXT    NOT NULL DEFAULT '',
    author          TEXT    NOT NULL DEFAULT '',
    category        TEXT    NOT NULL DEFAULT '',
    download_url    TEXT    NOT NULL DEFAULT '',
    installed       INTEGER NOT NULL DEFAULT 0,
    enabled_in_vfs  INTEGER NOT NULL DEFAULT 0,
    install_path    TEXT    NOT NULL DEFAULT '',
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);
```

**Columnas (12):** `mod_id`, `nexus_id`, `name`, `version`, `author`, `category`, `download_url`, `installed`, `enabled_in_vfs`, `install_path`, `created_at`, `updated_at`

---

## 4. Mapeo Columna-a-Columna

| Columna Canonical | S1 (`database.py`) | S2/S3 (`registry`) | Notas |
|-------------------|--------------------|--------------------|-------|
| `mod_id` (PK) | `id` | `mod_id` | Diferente nombre de PK |
| `nexus_id` (UNIQUE) | ❌ Ausente | `nexus_id` | S1 no tiene relación con Nexus |
| `name` | `name` (UNIQUE) | `name` | S1 tiene UNIQUE, S2/S3 no |
| `version` | `version` | `version` | Compatible |
| `author` | ❌ Ausente | `author` | Solo en backend |
| `category` | ❌ Ausente | `category` | Solo en backend |
| `download_url` | ❌ Ausente | `download_url` | Solo en backend |
| `installed` | ❌ Ausente | `installed` | S1 usa `status` en su lugar |
| `enabled_in_vfs` | ❌ Ausente | `enabled_in_vfs` | Solo en backend |
| `install_path` | ❌ Ausente | `install_path` | Solo en backend |
| `size_mb` | `size_mb` | ❌ Ausente | Solo en GUI |
| `status` | `status` | ❌ Ausente | Solo en GUI (derivable de `installed`+`enabled_in_vfs`) |
| `source` | `source` | ❌ Ausente | Solo en GUI |
| `installed_at` | `installed_at` | ❌ Ausente | S1 tiene TIMESTAMP, S2/S3 usa `created_at` |
| `created_at` | ❌ Ausente | `created_at` | S2/S3 usa TEXT, S1 no tiene |
| `updated_at` | `updated_at` (TIMESTAMP) | `updated_at` (TEXT) | Tipos incompatibles |

---

## 5. Análisis de Incompatibilidades

### 5.1 Divergencia Semántica
- **S1** es un esquema de **presentación GUI**: `status`, `size_mb`, `source` son datos derivados/de visualización.
- **S2/S3** es un esquema de **dominio backend**: `nexus_id`, `installed`, `enabled_in_vfs` son datos operacionales.

### 5.2 Problemas Críticos
1. **PK naming:** `id` vs `mod_id` — JOINs entre tablas requerirán alias.
2. **Sin nexus_id en S1:** No se puede correlacionar un mod del GUI con su registro backend sin `name` (frágil).
3. **Tipos de timestamp:** S1 usa `TIMESTAMP`, S2/S3 usan `TEXT` con `datetime('now')`.
4. **UNIQUE constraint divergente:** S1 tiene `name UNIQUE`, S2/S3 no (pueden existir mods con mismo nombre de diferentes autores).

### 5.3 Observación
S2 y S3 son idénticos porque `async_registry.py` fue creado como versión async de `registry.py`. Ambos operan sobre el mismo archivo `mod_registry.db`, pero son clases independientes.

---

## 6. Esquema Canonical Propuesto

```sql
CREATE TABLE IF NOT EXISTS mods (
    mod_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nexus_id        INTEGER UNIQUE NOT NULL,
    name            TEXT    NOT NULL,
    version         TEXT    NOT NULL DEFAULT '',
    author          TEXT    NOT NULL DEFAULT '',
    category        TEXT    NOT NULL DEFAULT '',
    download_url    TEXT    NOT NULL DEFAULT '',
    installed       INTEGER NOT NULL DEFAULT 0,       -- 0/1 boolean
    enabled_in_vfs  INTEGER NOT NULL DEFAULT 0,       -- 0/1 boolean
    install_path    TEXT    NOT NULL DEFAULT '',
    size_mb         REAL    NOT NULL DEFAULT 0.0,     -- desde S1
    source          TEXT    NOT NULL DEFAULT '',       -- desde S1
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Tabla de control de migración
CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER PRIMARY KEY,
    applied_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    description TEXT
);

INSERT INTO schema_version (version, description) VALUES (1, 'Canonical mods schema — DB-001');
```

### Columnas derivadas eliminadas
- `status` → Derivable como `CASE WHEN enabled_in_vfs THEN 'active' WHEN installed THEN 'installed' ELSE 'inactive' END`
- `installed_at` → Reemplazado por `created_at` existente

### Estrategia de migración (Fase 2)
1. `database.py` (S1) debe dejar de crear su propia tabla `mods` y usar el esquema canonical.
2. `registry.py` (S2) se marca como deprecated — toda operación pasa por `AsyncModRegistry` (S3).
3. La GUI consulta vía `AsyncModRegistry` en lugar de `DatabaseAgent` para datos de mods.
4. `schema_version` controla migraciones automáticas al abrir la DB.

---

## 7. Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|-------------|------------|
| GUI rompe al perder `status`/`size_mb` | Media | Vista SQL o propiedades calculadas en el frontend |
| `registry.py` sync aún usado en producción | Alta | Verificar callers antes de deprecar |
| Timestamps `TEXT` vs `TIMESTAMP` causan bugs de comparación | Baja | Usar `TEXT` consistently con `datetime('now')` |
| Datos existentes en `skyclaw_gui.db` se pierden | Media | Script de migración con INSERT INTO ... SELECT |

---

*Documento generado como parte de PLAN_REFACTORIZACION_CONSOLIDADO — Tarea 5.5 (DB-001 Fase 1).*
