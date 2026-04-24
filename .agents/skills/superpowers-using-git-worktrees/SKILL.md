---
name: using-git-worktrees
description: Usar al comenzar trabajo de feature que necesita aislamiento del workspace actual o antes de ejecutar planes de implementación — crea git worktrees aislados con selección inteligente de directorio y verificación de seguridad
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
---

# Usando Git Worktrees

## Visión General

Los git worktrees crean workspaces aislados compartiendo el mismo repositorio, permitiendo trabajar en múltiples branches simultáneamente sin cambiar.

**Principio core:** Selección sistemática de directorio + verificación de seguridad = aislamiento confiable.

**Anunciar al inicio:** "Estoy usando la skill using-git-worktrees para configurar un workspace aislado."

## Proceso de Selección de Directorio

Seguir este orden de prioridad:

### 1. Chequear Directorios Existentes

```bash
# Chequear en orden de prioridad
ls -d .worktrees 2>/dev/null     # Preferido (hidden)
ls -d worktrees 2>/dev/null      # Alternativa
```

**Si se encuentra:** Usar ese directorio. Si ambos existen, `.worktrees` gana.

### 2. Chequear CLAUDE.md

```bash
grep -i "worktree.*director" CLAUDE.md 2>/dev/null
```

**Si se especifica preferencia:** Usarla sin preguntar.

### 3. Preguntar al Usuario

Si no existe directorio y no hay preferencia en CLAUDE.md:

```
No se encontró directorio de worktree. ¿Dónde debería crear los worktrees?

1. .worktrees/ (project-local, hidden)
2. ~/.config/superpowers/worktrees/<project-name>/ (ubicación global)

¿Qué prefieres?
```

## Verificación de Seguridad

### Para Directorios Project-Local (.worktrees o worktrees)

**DEBE verificar que el directorio esté ignorado antes de crear worktree:**

```bash
# Chequear si el directorio está ignorado (respeta local, global, y system gitignore)
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

**Si NO está ignorado:**

Por la regla de Jesse "Fix broken things immediately":
1. Agregar línea apropiada a .gitignore
2. Commitear el cambio
3. Proceder con creación de worktree

**Por qué es crítico:** Previene accidentalmente commitear contenidos de worktree al repositorio.

### Para Directorio Global (~/.config/superpowers/worktrees)

No se necesita verificación de .gitignore — fuera del proyecto enteramente.

## Pasos de Creación

### 1. Detectar Nombre de Proyecto

```bash
project=$(basename "$(git rev-parse --show-toplevel)")
```

### 2. Crear Worktree

```bash
# Determinar path completo
case $LOCATION in
  .worktrees|worktrees)
    path="$LOCATION/$BRANCH_NAME"
    ;;
  ~/.config/superpowers/worktrees/*)
    path="~/.config/superpowers/worktrees/$project/$BRANCH_NAME"
    ;;
esac

# Crear worktree con nuevo branch
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

### 3. Ejecutar Setup del Proyecto

Auto-detectar y ejecutar setup apropiado:

```bash
# Node.js
if [ -f package.json ]; then npm install; fi

# Rust
if [ -f Cargo.toml ]; then cargo build; fi

# Python
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then poetry install; fi

# Go
if [ -f go.mod ]; then go mod download; fi
```

### 4. Verificar Baseline Limpio

Ejecutar tests para asegurar que el worktree arranca limpio:

```bash
# Ejemplos — usar comando apropiado para el proyecto
npm test
cargo test
pytest
go test ./...
```

**Si tests fallan:** Reportar failures, preguntar si proceder o investigar.

**Si tests pasan:** Reportar listo.

### 5. Reportar Ubicación

```
Worktree listo en <full-path>
Tests pasando (<N> tests, 0 failures)
Listo para implementar <feature-name>
```

## Quick Reference

| Situación | Acción |
|-----------|--------|
| `.worktrees/` existe | Usarlo (verificar ignored) |
| `worktrees/` existe | Usarlo (verificar ignored) |
| Ambos existen | Usar `.worktrees/` |
| Ninguno existe | Chequear CLAUDE.md → Preguntar usuario |
| Directorio no ignorado | Agregar a .gitignore + commit |
| Tests fallan durante baseline | Reportar failures + preguntar |
| No hay package.json/Cargo.toml | Saltar instalación de dependencias |

## Errores Comunes

### Saltar verificación de ignore

- **Problema:** Contenidos de worktree se trackean, contaminan git status
- **Fix:** Siempre usar `git check-ignore` antes de crear worktree project-local

### Asumir ubicación de directorio

- **Problema:** Crea inconsistencia, viola convenciones de proyecto
- **Fix:** Seguir prioridad: existing > CLAUDE.md > ask

### Proceder con tests fallando

- **Problema:** No se pueden distinguir nuevos bugs de issues pre-existentes
- **Fix:** Reportar failures, obtener permiso explícito para proceder

### Hardcodear comandos de setup

- **Problema:** Rompe en proyectos usando herramientas diferentes
- **Fix:** Auto-detectar desde archivos de proyecto (package.json, etc.)

## Ejemplo de Workflow

```
Tú: Estoy usando la skill using-git-worktrees para configurar un workspace aislado.

[Chequear .worktrees/ - existe]
[Verificar ignored - git check-ignore confirma .worktrees/ está ignorado]
[Crear worktree: git worktree add .worktrees/auth -b feature/auth]
[Ejecutar npm install]
[Ejecutar npm test - 47 pasando]

Worktree listo en /Users/jesse/myproject/.worktrees/auth
Tests pasando (47 tests, 0 failures)
Listo para implementar auth feature
```

## Red Flags

**Nunca:**
- Crear worktree sin verificar que esté ignorado (project-local)
- Saltar verificación de baseline test
- Proceder con tests fallando sin preguntar
- Asumir ubicación de directorio cuando es ambigua
- Saltar chequeo de CLAUDE.md

**Siempre:**
- Seguir prioridad de directorio: existing > CLAUDE.md > ask
- Verificar que el directorio esté ignorado para project-local
- Auto-detectar y ejecutar setup de proyecto
- Verificar baseline test limpio

## Integración

**Llamado por:**
- **brainstorming** (Fase 4) - REQUERIDO cuando el diseño es aprobado y la implementación sigue
- **subagent-driven-development** - REQUERIDO antes de ejecutar cualquier tarea
- **executing-plans** - REQUERIDO antes de ejecutar cualquier tarea
- Cualquier skill que necesite workspace aislado

**Parea con:**
- **finishing-a-development-branch** - REQUERIDO para cleanup después de que el trabajo completa
