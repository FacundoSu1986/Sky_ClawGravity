---
name: using-superpowers
description: Usar al iniciar cualquier conversación — establece cómo encontrar y usar skills, requiriendo invocación de Skill tool antes de CUALQUIER respuesta incluyendo preguntas clarificadoras
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
---

<SUBAGENT-STOP>
Si fuiste despachado como subagente para ejecutar una tarea específica, salta esta skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
Si crees que hay incluso un 1% de chance de que una skill pueda aplicar a lo que estás haciendo, ABSOLUTAMENTE DEBES invocar la skill.

SI UNA SKILL APLICA A TU TAREA, NO TIENES ELECCIÓN. DEBES USARLA.

Esto no es negociable. No es opcional. No puedes racionalizar tu salida de esto.
</EXTREMELY-IMPORTANT>

## Prioridad de Instrucciones

Las skills de Superpowers anulan el comportamiento default del system prompt, pero **las instrucciones del usuario siempre tienen precedencia**:

1. **Instrucciones explícitas del usuario** (CLAUDE.md, GEMINI.md, AGENTS.md, requests directos) — prioridad más alta
2. **Skills de Superpowers** — anulan comportamiento default del system donde conflictúan
3. **System prompt default** — prioridad más baja

Si CLAUDE.md, GEMINI.md, o AGENTS.md dice "no uses TDD" y una skill dice "siempre usa TDD," sigue las instrucciones del usuario. El usuario tiene el control.

## Cómo Acceder a Skills

**En Claude Code:** Usa la herramienta `Skill`. Cuando invocas una skill, su contenido se carga y se presenta — síguelo directamente. Nunca uses la herramienta Read en archivos de skill.

**En Copilot CLI:** Usa la herramienta `skill`. Las skills son auto-descubiertas desde plugins instalados. La herramienta `skill` funciona igual que la de Claude Code.

**En Gemini CLI:** Las skills se activan vía la herramienta `activate_skill`. Gemini carga metadata de skills al inicio de sesión y activa el contenido completo on demand.

**En otros entornos:** Consulta la documentación de tu plataforma para ver cómo se cargan las skills.

## Adaptación de Plataforma

Las skills usan nombres de herramientas de Claude Code. Plataformas no-CC: ver `references/copilot-tools.md` (Copilot CLI), `references/codex-tools.md` (Codex) para equivalentes de herramientas. Los usuarios de Gemini CLI obtienen el mapeo de herramientas cargado automáticamente vía GEMINI.md.

# Usando Skills

## La Regla

**Invoca skills relevantes o solicitadas ANTES de cualquier respuesta o acción.** Incluso un 1% de chance de que una skill pueda aplicar significa que deberías invocarla para verificar. Si una skill invocada resulta incorrecta para la situación, no necesitas usarla.

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke brainstorming skill" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

## Red Flags

Estos pensamientos significan DETENTE — estás racionalizando:

| Pensamiento | Realidad |
|---------|---------|
| "Esto es solo una pregunta simple" | Las preguntas son tareas. Busca skills. |
| "Necesito más contexto primero" | El check de skill viene ANTES de preguntas clarificadoras. |
| "Déjame explorar el codebase primero" | Las skills te dicen CÓMO explorar. Chequea primero. |
| "Puedo chequear git/archivos rápido" | Los archivos carecen de contexto de conversación. Busca skills. |
| "Déjame juntar información primero" | Las skills te dicen CÓMO juntar información. |
| "Esto no necesita una skill formal" | Si existe una skill, úsala. |
| "Recuerdo esta skill" | Las skills evolucionen. Lee la versión actual. |
| "Esto no cuenta como tarea" | Acción = tarea. Busca skills. |
| "La skill es overkill" | Las cosas simples se vuelven complejas. Úsala. |
| "Voy a hacer esto primero" | Chequea ANTES de hacer cualquier cosa. |
| "Esto se siente productivo" | La acción indisciplinada desperdicia tiempo. Las skills previenen esto. |
| "Sé lo que eso significa" | Saber el concepto ≠ usar la skill. Invócala. |

## Prioridad de Skills

Cuando múltiples skills podrían aplicar, usa este orden:

1. **Process skills primero** (brainstorming, debugging) — determinan CÓMO abordar la tarea
2. **Implementation skills segundo** (frontend-design, mcp-builder) — guían la ejecución

"Vamos a construir X" → brainstorming primero, luego implementation skills.
"Arregla este bug" → debugging primero, luego domain-specific skills.

## Tipos de Skills

**Rígidas** (TDD, debugging): Sigue exactamente. No adaptes lejos de la disciplina.

**Flexibles** (patterns): Adapta principios al contexto.

La skill misma te dice cuál es.

## Instrucciones del Usuario

Las instrucciones dicen QUÉ, no CÓMO. "Agrega X" o "Arregla Y" no significa saltar workflows.
