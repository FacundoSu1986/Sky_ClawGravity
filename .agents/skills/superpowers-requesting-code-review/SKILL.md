---
name: requesting-code-review
description: Usar al completar tareas, implementar features mayores, o antes de mergear para verificar que el trabajo cumple los requisitos
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
---

# Solicitando Code Review

Despacha el subagente superpowers:code-reviewer para atrapar issues antes de que se propaguen. El reviewer recibe contexto precisamente diseñado para evaluación — nunca tu historial de sesión. Esto mantiene al reviewer enfocado en el producto de trabajo, no en tu proceso de pensamiento, y preserva tu propio contexto para trabajo continuo.

**Principio core:** Review temprano, review frecuente.

## Cuándo Solicitar Review

**Obligatorio:**
- Después de cada tarea en desarrollo driven by subagent
- Después de completar feature mayor
- Antes de merge a main

**Opcional pero valioso:**
- Cuando estás atascado (perspectiva fresca)
- Antes de refactoring (baseline check)
- Después de arreglar bug complejo

## Cómo Solicitar

**1. Obtener git SHAs:**
```bash
BASE_SHA=$(git rev-parse HEAD~1)  # o origin/main
HEAD_SHA=$(git rev-parse HEAD)
```

**2. Despachar subagente code-reviewer:**

Usar herramienta Task con tipo superpowers:code-reviewer, llenar template en `code-reviewer.md`

**Placeholders:**
- `{WHAT_WAS_IMPLEMENTED}` - Qué acabas de construir
- `{PLAN_OR_REQUIREMENTS}` - Qué debería hacer
- `{BASE_SHA}` - Commit inicial
- `{HEAD_SHA}` - Commit final
- `{DESCRIPTION}` - Resumen breve

**3. Actuar sobre el feedback:**
- Arreglar issues Críticos inmediatamente
- Arreglar issues Importantes antes de proceder
- Notar issues Menores para después
- Rechazar si el reviewer está equivocado (con razonamiento)

## Ejemplo

```
[Acabo de completar Task 2: Add verification function]

Tú: Déjame solicitar code review antes de proceder.

BASE_SHA=$(git log --oneline | grep "Task 1" | head -1 | awk '{print $1}')
HEAD_SHA=$(git rev-parse HEAD)

[Despachar subagente superpowers:code-reviewer]
  WHAT_WAS_IMPLEMENTED: Verification and repair functions for conversation index
  PLAN_OR_REQUIREMENTS: Task 2 from docs/superpowers/plans/deployment-plan.md
  BASE_SHA: a7981ec
  HEAD_SHA: 3df7661
  DESCRIPTION: Added verifyIndex() and repairIndex() with 4 issue types

[Subagent retorna]:
  Strengths: Clean architecture, real tests
  Issues:
    Important: Missing progress indicators
    Minor: Magic number (100) for reporting interval
  Assessment: Ready to proceed

Tú: [Arreglar progress indicators]
[Continuar a Task 3]
```

## Integración con Workflows

**Desarrollo Driven by Subagent:**
- Review después de CADA tarea
- Atrapar issues antes de que se compongan
- Arreglar antes de moverse a la siguiente tarea

**Ejecutando Planes:**
- Review después de cada batch (3 tareas)
- Obtener feedback, aplicar, continuar

**Desarrollo Ad-Hoc:**
- Review antes de merge
- Review cuando estás atascado

## Red Flags

**Nunca:**
- Saltar review porque "es simple"
- Ignorar issues Críticos
- Proceder con issues Importantes sin arreglar
- Discutir feedback técnico válido

**Si el reviewer está equivocado:**
- Rechazar con razonamiento técnico
- Mostrar código/tests que prueban que funciona
- Solicitar clarificación

Ver template en: requesting-code-review/code-reviewer.md
