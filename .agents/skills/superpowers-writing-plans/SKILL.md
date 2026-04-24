---
name: writing-plans
description: Usar cuando tienes una spec o requisitos para una tarea multi-paso, antes de tocar código
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
---

# Escribiendo Planes

## Visión General

Escribe planes de implementación comprehensivos asumiendo que el ingeniero tiene cero contexto de nuestro codebase y gusto cuestionable. Documenta todo lo que necesitan saber: qué archivos tocar para cada tarea, código, testing, docs que podrían necesitar chequear, cómo testearlo. Dales el plan completo como tareas bite-sized. DRY. YAGNI. TDD. Commits frecuentes.

Asume que son desarrolladores habilidosos, pero saben casi nada sobre nuestro toolset o dominio de problema. Asume que no saben diseñar tests muy bien.

**Anunciar al inicio:** "Estoy usando la skill writing-plans para crear el plan de implementación."

**Contexto:** Esto debería ejecutarse en un worktree dedicado (creado por la skill de brainstorming).

**Guardar planes en:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- (Las preferencias de ubicación de planes del usuario anulan este default)

## Scope Check

Si la spec cubre múltiples subsistemas independientes, debería haberse dividido en specs de sub-proyecto durante brainstorming. Si no fue así, sugerir dividir esto en planes separados — uno por subsistema. Cada plan debería producir software funcional y testeable por sí solo.

## Estructura de Archivos

Antes de definir tareas, mapea qué archivos serán creados o modificados y qué responsabilidad tiene cada uno. Aquí es donde las decisiones de descomposición se definen.

- Diseña unidades con límites claros e interfaces bien definidas. Cada archivo debería tener una responsabilidad clara.
- Razonas mejor sobre código que puedes mantener en contexto a la vez, y tus ediciones son más confiables cuando los archivos están enfocados. Prefiere archivos más pequeños y enfocados sobre archivos grandes que hacen demasiado.
- Archivos que cambian juntos deberían vivir juntos. Divide por responsabilidad, no por capa técnica.
- En codebases existentes, sigue patrones establecidos. Si el codebase usa archivos grandes, no reestructure unilateralmente — pero si un archivo que estás modificando ha crecido demasiado, incluir una división en el plan es razonable.

Esta estructura informa la descomposición de tareas. Cada tarea debería producir cambios autocontenidos que tengan sentido independientemente.

## Granularidad de Tareas Bite-Sized

**Cada paso es una acción (2-5 minutos):**
- "Escribir el test fallando" - paso
- "Ejecutarlo para asegurar que falla" - paso
- "Implementar el código mínimo para hacer pasar el test" - paso
- "Ejecutar los tests y asegurar que pasan" - paso
- "Commit" - paso

## Header del Documento de Plan

**Cada plan DEBE comenzar con este header:**

```markdown
# [Nombre de Feature] Implementation Plan

> **Para workers agenticos:** SUB-SKILL REQUERIDA: Usar superpowers:subagent-driven-development (recomendado) o superpowers:executing-plans para implementar este plan tarea por tarea. Los pasos usan checkbox (`- [ ]`) syntax para tracking.

**Goal:** [Una oración describiendo qué construye]

**Architecture:** [2-3 oraciones sobre el approach]

**Tech Stack:** [Tecnologías/librerías clave]

---
```

## Estructura de Tareas

````markdown
### Task N: [Nombre de Componente]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Escribir el test fallando**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Ejecutar test para verificar que falla**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Escribir implementación mínima**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Ejecutar test para verificar que pasa**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## No Placeholders

Cada paso debe contener el contenido actual que un ingeniero necesita. Estos son **fallos de plan** — nunca los escribas:
- "TBD", "TODO", "implementar después", "llenar detalles"
- "Agregar manejo de errores apropiado" / "agregar validación" / "manejar edge cases"
- "Escribir tests para lo de arriba" (sin código de test actual)
- "Similar a Task N" (repite el código — el ingeniero puede estar leyendo tareas fuera de orden)
- Pasos que describen qué hacer sin mostrar cómo (bloques de código requeridos para pasos de código)
- Referencias a tipos, funciones o métodos no definidos en ninguna tarea

## Recordar
- File paths exactos siempre
- Código completo en cada paso — si un paso cambia código, muestra el código
- Comandos exactos con output esperado
- DRY, YAGNI, TDD, commits frecuentes

## Self-Review

Después de escribir el plan completo, mira la spec con ojos frescos y chequea el plan contra ella. Este es un checklist que ejecutas tú mismo — no un despacho de subagente.

**1. Spec coverage:** Skim cada sección/requisito en la spec. ¿Puedes apuntar a una tarea que lo implementa? Lista cualquier gap.

**2. Placeholder scan:** Busca en tu plan red flags — cualquiera de los patrones de la sección "No Placeholders" de arriba. Arréglalos.

**3. Type consistency:** ¿Los tipos, firmas de métodos y nombres de propiedades que usaste en tareas posteriores matchean lo que definiste en tareas anteriores? Una función llamada `clearLayers()` en Task 3 pero `clearFullLayers()` en Task 7 es un bug.

Si encuentras issues, arréglalos inline. No necesitas re-revisar — solo arregla y sigue. Si encuentras un requisito de spec sin tarea, agrégala.

## Execution Handoff

Después de guardar el plan, ofrecer opción de ejecución:

**"Plan completo y guardado en `docs/superpowers/plans/<filename>.md`. Dos opciones de ejecución:**

**1. Subagent-Driven (recomendado)** - Despacho un subagente fresco por tarea, reviso entre tareas, iteración rápida

**2. Inline Execution** - Ejecuto tareas en esta sesión usando executing-plans, ejecución batch con checkpoints

**¿Qué approach?"**

**Si se elige Subagent-Driven:**
- **SUB-SKILL REQUERIDA:** Usar superpowers:subagent-driven-development
- Subagent fresco por tarea + two-stage review

**Si se elige Inline Execution:**
- **SUB-SKILL REQUERIDA:** Usar superpowers:executing-plans
- Ejecución batch con checkpoints para review
