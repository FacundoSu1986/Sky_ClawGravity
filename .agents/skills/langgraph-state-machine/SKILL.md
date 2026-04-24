---
name: langgraph-state-machine
description: Diseño y ejecución de grafos de agentes con estado y ciclos usando LangGraph. Usar para flujos de trabajo no lineales que requieran persistencia de estado, retroalimentación automática o pipelines de validación iterativa. No usar para flujos secuenciales simples donde CrewAI o código directo sean suficientes.
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
  compatibility:
    - Python 3.11+
    - LangGraph 0.1+
    - asyncio
---

# LangGraph State Machine (Sky-Claw Integration)

Skill para gestionar flujos de trabajo **no lineales** mediante grafos de estado con LangGraph, permitiendo ciclos de retroalimentación, corrección de errores automática y persistencia de estado entre pasos.

## 🎯 Propósito

- Pipelines de parcheo con validación iterativa.
- Flujos de agentes con retroalimentación (ej. QA devuelve al Developer).
- Checkpointing y reanudación de tareas complejas.

## 📋 Cuándo Usar

| Escenario | Prioridad |
|-----------|-----------|
| Pipeline de parcheo con validación intermedia | 🔴 Alta |
| Refactorización masiva con checkpoints | 🔴 Alta |
| Flujo cíclico: ejecución → validación → corrección | 🟠 Media |

## ❌ Cuándo NO Usar

- Flujos secuenciales simples (E-T-L básico) → usar `sky-claw-automation` o código directo.
- Tareas de una sola ronda sin estado → usar `local-dev-aider-pairing`.

## 🔧 Prerrequisitos

```bash
pip install langgraph langchain-core
```

## 🚀 Instrucciones de Uso

### 1. Definir el Grafo
Los grafos deben definirse en scripts Python dentro del proyecto (ej. `scripts/graphs/` o `sky_claw/agent/graphs/`):

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class AgentState(TypedDict):
    task: str
    code: str
    validation_result: bool
    iterations: int

builder = StateGraph(AgentState)
builder.add_node("generate", generate_code_node)
builder.add_node("validate", validate_code_node)
builder.add_edge(START, "generate")
builder.add_conditional_edges(
    "validate",
    lambda state: "done" if state["validation_result"] else "retry",
    {"done": END, "retry": "generate"}
)
graph = builder.compile()
```

### 2. Ejecutar el Grafo
```python
result = await graph.ainvoke(
    {"task": "refactorizar db.py", "code": "", "validation_result": False, "iterations": 0}
)
```

### 3. Persistencia de Estado
```python
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

## ⚠️ Restricciones

- **Definición previa:** No se invoca con un comando mágico. El grafo debe estar implementado en código Python.
- **Límite de iteraciones:** Siempre configurar `max_iterations` para evitar loops infinitos.
- **Soberanía de datos:** Preferir `MemorySaver` o SQLite checkpointer local sobre backends cloud.

## 🎯 Score de la Skill

| Dimensión | Score | Estado |
|-----------|-------|--------|
| Realismo | 9.5/10 | ✅ Código Python real |
| Seguridad | 8.5/10 | ✅ Local checkpointer |
| Integración | 8/10 | ✅ Requiere implementar grafo previo |
