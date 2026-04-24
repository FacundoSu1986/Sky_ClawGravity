---
name: executing-plans
description: Usar cuando se tiene un plan de implementación escrito para ejecutar en una sesión separada con puntos de revisión
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
---

# Ejecutando Planes

## Visión General

Cargar plan, revisar críticamente, ejecutar todas las tareas, reportar al completar.

**Anunciar al inicio:** "Estoy usando la skill executing-plans para implementar este plan."

**Nota:** Dile a tu socio humano que Superpowers funciona mucho mejor con acceso a subagentes. La calidad de su trabajo será significativamente mayor si se ejecuta en una plataforma con soporte de subagentes (como Claude Code o Codex). Si los subagentes están disponibles, usa superpowers:subagent-driven-development en lugar de esta skill.

## El Proceso

### Paso 1: Cargar y Revisar el Plan
1. Leer archivo del plan
2. Revisar críticamente — identificar cualquier pregunta o preocupación sobre el plan
3. Si hay preocupaciones: Plantearlas con tu socio humano antes de comenzar
4. Si no hay preocupaciones: Crear TodoWrite y proceder

### Paso 2: Ejecutar Tareas

Para cada tarea:
1. Marcar como in_progress
2. Seguir cada paso exactamente (el plan tiene pasos bite-sized)
3. Ejecutar verificaciones según lo especificado
4. Marcar como completed

### Paso 3: Completar Desarrollo

Después de que todas las tareas estén completas y verificadas:
- Anunciar: "Estoy usando la skill finishing-a-development-branch para completar este trabajo."
- **SUB-SKILL REQUERIDA:** Usar superpowers:finishing-a-development-branch
- Seguir esa skill para verificar tests, presentar opciones, ejecutar elección

## Cuándo Detenerse y Pedir Ayuda

**DETENER la ejecución inmediatamente cuando:**
- Encuentres un bloqueo (dependencia faltante, test falla, instrucción poco clara)
- El plan tenga gaps críticos que impidan comenzar
- No entiendas una instrucción
- La verificación falle repetidamente

**Pide clarificación en lugar de adivinar.**

## Cuándo Revisitar Pasos Anteriores

**Volver a Revisar (Paso 1) cuando:**
- El socio actualice el plan basado en tu feedback
- El enfoque fundamental necesite repensarse

**No fuerces a través de bloqueos** — detente y pregunta.

## Recordar
- Revisar el plan críticamente primero
- Seguir los pasos del plan exactamente
- No saltar verificaciones
- Referenciar skills cuando el plan lo indique
- Detenerse cuando estás bloqueado, no adivinar
- Nunca comenzar implementación en rama main/master sin consentimiento explícito del usuario

## Integración

**Skills de workflow requeridas:**
- **superpowers:using-git-worktrees** - REQUERIDO: Configurar workspace aislado antes de comenzar
- **superpowers:writing-plans** - Crea el plan que esta skill ejecuta
- **superpowers:finishing-a-development-branch** - Completa el desarrollo después de todas las tareas
