---
name: finishing-a-development-branch
description: Usar cuando la implementación está completa, todos los tests pasan, y necesitas decidir cómo integrar el trabajo — guía la finalización de trabajo de desarrollo presentando opciones estructuradas para merge, PR, o cleanup
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
---

# Finalizando un Branch de Desarrollo

## Visión General

Guía la finalización de trabajo de desarrollo presentando opciones claras y manejando el workflow elegido.

**Principio core:** Verificar tests → Presentar opciones → Ejecutar elección → Limpiar.

**Anunciar al inicio:** "Estoy usando la skill finishing-a-development-branch para completar este trabajo."

## El Proceso

### Paso 1: Verificar Tests

**Antes de presentar opciones, verificar que los tests pasan:**

```bash
# Ejecutar test suite del proyecto
npm test / cargo test / pytest / go test ./...
```

**Si los tests fallan:**
```
Tests fallando (<N> failures). Deben arreglarse antes de completar:

[Mostrar failures]

No se puede proceder con merge/PR hasta que los tests pasen.
```

Detente. No procedas al Paso 2.

**Si los tests pasan:** Continuar al Paso 2.

### Paso 2: Determinar Base Branch

```bash
# Intentar branches base comunes
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

O preguntar: "Este branch se separó de main — ¿es eso correcto?"

### Paso 3: Presentar Opciones

Presentar exactamente estas 4 opciones:

```
Implementación completa. ¿Qué te gustaría hacer?

1. Mergear de vuelta a <base-branch> localmente
2. Pushear y crear un Pull Request
3. Mantener el branch as-is (lo manejaré después)
4. Descartar este trabajo

¿Qué opción?
```

**No agregar explicación** — mantener opciones concisas.

### Paso 4: Ejecutar Elección

#### Opción 1: Merge Local

```bash
# Cambiar a base branch
git checkout <base-branch>

# Pull latest
git pull

# Merge feature branch
git merge <feature-branch>

# Verificar tests en resultado mergeado
<test command>

# Si tests pasan
git branch -d <feature-branch>
```

Luego: Limpiar worktree (Paso 5)

#### Opción 2: Push y Crear PR

```bash
# Push branch
git push -u origin <feature-branch>

# Crear PR
gh pr create --title "<title>" --body "$(cat <<'EOF'
## Summary
<2-3 bullets de qué cambió>

## Test Plan
- [ ] <verification steps>
EOF
)"
```

Luego: Limpiar worktree (Paso 5)

#### Opción 3: Mantener As-Is

Reportar: "Manteniendo branch <name>. Worktree preservado en <path>."

**No limpiar worktree.**

#### Opción 4: Descartar

**Confirmar primero:**
```
Esto eliminará permanentemente:
- Branch <name>
- Todos los commits: <commit-list>
- Worktree en <path>

Escribe 'discard' para confirmar.
```

Esperar confirmación exacta.

Si confirmado:
```bash
git checkout <base-branch>
git branch -D <feature-branch>
```

Luego: Limpiar worktree (Paso 5)

### Paso 5: Limpiar Worktree

**Para Opciones 1, 2, 4:**

Chequear si estamos en worktree:
```bash
git worktree list | grep $(git branch --show-current)
```

Si sí:
```bash
git worktree remove <worktree-path>
```

**Para Opción 3:** Mantener worktree.

## Quick Reference

| Opción | Merge | Push | Mantener Worktree | Limpiar Branch |
|--------|-------|------|-------------------|----------------|
| 1. Merge local | ✓ | - | - | ✓ |
| 2. Crear PR | - | ✓ | ✓ | - |
| 3. Mantener as-is | - | - | ✓ | - |
| 4. Descartar | - | - | - | ✓ (force) |

## Errores Comunes

**Saltar verificación de tests**
- **Problema:** Mergear código roto, crear PR fallando
- **Fix:** Siempre verificar tests antes de ofrecer opciones

**Preguntas open-ended**
- **Problema:** "¿Qué debería hacer ahora?" → ambiguo
- **Fix:** Presentar exactamente 4 opciones estructuradas

**Limpieza automática de worktree**
- **Problema:** Remover worktree cuando podría necesitarse (Opción 2, 3)
- **Fix:** Solo limpiar para Opciones 1 y 4

**Sin confirmación para discard**
- **Problema:** Accidentalmente borrar trabajo
- **Fix:** Requerir confirmación tipiada "discard"

## Red Flags

**Nunca:**
- Proceder con tests fallando
- Mergear sin verificar tests en resultado
- Borrar trabajo sin confirmación
- Force-push sin request explícito

**Siempre:**
- Verificar tests antes de ofrecer opciones
- Presentar exactamente 4 opciones
- Obtener confirmación tipiada para Opción 4
- Limpiar worktree solo para Opciones 1 & 4

## Integración

**Llamado por:**
- **subagent-driven-development** (Paso 7) - Después de que todas las tareas completan
- **executing-plans** (Paso 5) - Después de que todos los batches completan

**Parea con:**
- **using-git-worktrees** - Limpia el worktree creado por esa skill
