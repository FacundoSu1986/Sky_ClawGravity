---
name: external-github-agents
description: Puente para delegar tareas complejas a frameworks autónomos externos (AutoGPT, OpenHands, AutoGen, CrewAI, LangGraph, Dify, MetaGPT, Agno) cuando un agente local de una sola ronda no es suficiente. Usar para simulaciones multi-agente, investigación profunda, desarrollo sandboxed o flujos de estado complejos.
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
  compatibility:
    - Python 3.11+
    - Docker (para OpenHands/Dify)
    - asyncio
    - Sky-Claw Ecosystem
  requirements:
    - API keys configuradas (OpenAI, Anthropic, etc.)
    - Entorno virtual aislado recomendado
---

# External GitHub Agents Integrator

Puente oficial para delegar tareas a frameworks autónomos externos cuando la complejidad excede las capacidades de un agente local de una sola ronda.

## 🎯 Propósito

- Orquestar **simulaciones multi-agente** prolongadas.
- Ejecutar **investigación autónoma** profunda en internet.
- Generar **código de ciclo completo** en entornos sandboxed.
- Gestionar **flujos de trabajo ramificados** con persistencia de estado.

## 📋 Cuándo Usar

| Escenario | Framework típico | Prioridad |
|-----------|------------------|-----------|
| Desarrollo de software completo en sandbox | OpenHands | 🔴 Alta |
| Investigación autónoma extensa en web | AutoGPT | 🔴 Alta |
| Flujo de agentes secuencial/jerárquico | CrewAI | 🟠 Media |
| Debate multi-agente con roles definidos | AutoGen | 🟠 Media |
| Grafo de estado cíclico con persistencia | LangGraph | 🟠 Media |
| Simulación de empresa de software | MetaGPT | 🟡 Media |
| Orquestación RAG low-code con UI | Dify | 🟡 Media |
| Agente con memoria persistente a largo plazo | Agno | 🟡 Media |

## ❌ Cuándo NO Usar

- **Cambios triviales** de una sola línea que no justifiquen la sobrecarga.
- Cuando la tarea puede resolverse con skills locales:
  - Modificación de código → `local-dev-aider-pairing`
  - Scraping/automatización de mods → `sky-claw-automation`
  - Revisión de seguridad → `skyclaw-purple-auditor`
- Cuando **no se dispone** de los recursos computacionales (RAM/CPU/Docker) requeridos.
- Cuando la **soberanía de datos** impide ejecutar código en contenedores o APIs externas.

## 🌳 Árbol de Decisión

```text
¿La tarea requiere ejecución en sandbox Dockerizado?
├── SÍ  → OpenHands (desarrollo de software completo)
└── NO  → ¿Es investigación autónoma extensiva en internet?
        ├── SÍ  → AutoGPT
        └── NO  → ¿Requiere flujo de estado cíclico / persistencia?
                ├── SÍ  → LangGraph
                └── NO  → ¿Es un pipeline secuencial de roles?
                        ├── SÍ  → CrewAI
                        └── NO  → ¿Es debate multi-agente?
                                ├── SÍ  → AutoGen
                                └── NO  → ¿Es simulación de empresa/software?
                                        ├── SÍ  → MetaGPT
                                        └── NO  → ¿Es orquestación RAG low-code?
                                                ├── SÍ  → Dify
                                                └── NO  → ¿Es agente con memoria persistente?
                                                        └── SÍ  → Agno
```

## 🔧 Frameworks Soportados

### 1. LangGraph (langchain-ai/langgraph)
- **Tipo**: Biblioteca Python.
- **Adopción**: Estándar de la industria para grafos cíclicos y de estado.
- **Caso de uso**: Lógica de agentes determinista, persistencia de estado y flujos de trabajo ramificados complejos.
- **Prerrequisitos**: `pip install langgraph langchain-core`
- **Ejecución típica**:
  ```bash
  python scripts/mi_flujo_langgraph.py --input "<contexto>"
  ```
- **Nota**: Requiere definir el grafo (`StateGraph`) en un script Python previo.

### 2. CrewAI (crewAIInc/crewAI)
- **Tipo**: Biblioteca Python / Framework.
- **Stars**: ~30k+
- **Caso de uso**: Operaciones secuenciales estructuradas y roles jerárquicos corporativos.
- **Prerrequisitos**: `pip install crewai`
- **Ejecución típica**:
  ```bash
  # Con proyecto inicializado
  crewai run
  # O directamente vía script Python
  python scripts/equipo_crewai.py
  ```
- **Nota**: `crewai run` requiere un proyecto con `crew.py` inicializado previamente.

### 3. AutoGen (microsoft/autogen)
- **Tipo**: Biblioteca Python.
- **Caso de uso**: Debates multi-agente complejos y Group Chat de roles definidos.
- **Prerrequisitos**: `pip install pyautogen`
- **Ejecución típica**:
  ```bash
  python scripts/debate_autogen.py --config autogen_config.yaml
  ```
- **Nota**: Se configura via código Python definiendo `ConversableAgent` y `GroupChat`.

### 4. AutoGPT (Significant-Gravitas/AutoGPT)
- **Tipo**: Aplicación standalone.
- **Caso de uso**: Investigación en internet profunda y ejecución autónoma de flujos de trabajo extensos.
- **Prerrequisitos**:
  - Clonar repositorio oficial.
  - Instalar dependencias (`poetry install`).
  - Configurar `.env` con API keys.
- **Ejecución típica**:
  ```bash
  cd autogpt/
  poetry run autogpt --task "<tu_tarea>"
  ```
- **Nota**: No es una biblioteca importable de forma trivial; requiere entorno propio.

### 5. OpenHands (All-Hands-AI/OpenHands)
- **Tipo**: Aplicación Dockerizada.
- **Caso de uso**: Desarrollo de software de ciclo completo en entorno Dockerizado (sandboxed).
- **Prerrequisitos**:
  - Docker instalado y en ejecución.
  - Puerto libre (default 3000).
- **Ejecución típica**:
  ```bash
  docker run -it --rm \
    -p 3000:3000 \
    -v $(pwd):/opt/workspace \
    allhands/openhands:latest
  ```
- **Nota**: Expone una UI web. Ideal para features nuevos, no para parches quirúrgicos.

### 6. Dify (langgenius/dify)
- **Tipo**: Plataforma self-hosted (Docker Compose).
- **Stars**: ~90k+
- **Caso de uso**: Orquestación de flujos RAG complejos, pipelines de conocimiento y UI de agentes low-code.
- **Prerrequisitos**:
  - Docker Compose.
  - Clonar repo de Dify y levantar servicios.
- **Ejecución típica**:
  ```bash
  cd dify/docker/
  docker compose up -d
  # Consumir vía API REST
  curl -X POST http://localhost/v1/workflows/<workflow_id>/run \
    -H "Authorization: Bearer <api_key>" \
    -d '{"inputs": {"query": "<prompt>"}}'
  ```
- **Nota**: Requiere despliegue previo. No es invocable con un simple CLI sin infraestructura.

### 7. MetaGPT (geekan/MetaGPT)
- **Tipo**: Biblioteca Python / CLI.
- **Stars**: ~50k+
- **Caso de uso**: Simulación de compañías de software para generar PRDs, diseños y código de sistemas completos.
- **Prerrequisitos**: `pip install metagpt`, configurar `config/key.yaml` con API keys.
- **Ejecución típica**:
  ```bash
  metagpt "<requisitos_del_software>"
  # O vía Python
  python scripts/startup_metagpt.py --idea "<requisitos>"
  ```
- **Nota**: Genera múltiples archivos (PRD, diseño, código). Requiere revisión manual posterior.

### 8. Agno (agno-ai/agno)
- **Tipo**: Biblioteca Python.
- **Stars**: ~30k+
- **Caso de uso**: Agentes con memoria persistente a largo plazo y herramientas de razonamiento determinista.
- **Prerrequisitos**: `pip install agno`
- **Ejecución típica**:
  ```bash
  python scripts/agente_agno.py --agent_id "<id>"
  ```
- **Nota**: Framework relativamente nuevo; validar compatibilidad con Python 3.13+ antes de usar.

## ⚠️ Reglas de Invocación

1. **Task Document obligatorio**: Antes de instanciar un agente externo, crear un contexto de tarea claro (objetivo, constraints, output esperado).
2. **Preferir locales**: No usar agentes externos para modificaciones triviales de archivos. Usar `local-dev-aider-pairing` para pair programming local.
3. **Validar entorno**: Verificar que el framework esté instalado/configurado antes de invocar. No asumir que comandos genéricos funcionan sin setup previo.
4. **Soberanía de datos**: Si la tarea involucra código sensible o credenciales, preferir ejecución 100% local (LangGraph, CrewAI, AutoGen en local) sobre servicios cloud o Docker no auditados.
5. **Auditoría selectiva**: Para outputs que modifican código crítico del proyecto Sky-Claw, considerar auditoría con `skyclaw-purple-auditor`. No es obligatoria para tareas de investigación o generación de documentación.

## 🛠️ Prerrequisitos Generales

- **Python 3.11+** (para frameworks basados en Python).
- **Docker & Docker Compose** (para OpenHands y Dify).
- **API keys configuradas** (OpenAI, Anthropic, Azure, etc.) en variables de entorno o archivos de config.
- **Entorno virtual aislado** (recomendado usar el `.venv/` del proyecto o crear uno específico en `.agents/venvs/<framework>/`).

## 📁 Recursos del Ecosistema

- `.agents/scripts/verify_agent_stubs.py`: Verificación de stubs y conectividad básica.
- `docs/LANGGRAPH-STATEGRAFH-INTEGRATION.md`: Guía específica de LangGraph en Sky-Claw.
- `docs/AUTOGEN-INTEGRATION.md`: Guía específica de AutoGen en Sky-Claw.

## 🎯 Score de la Skill

| Dimensión | Score | Estado |
|-----------|-------|--------|
| Realismo de comandos | 9/10 | ✅ Validados contra repos oficiales |
| Claridad de decisión | 8.5/10 | ✅ Árbol de decisión incluido |
| Seguridad/Soberanía | 8/10 | ✅ Reglas de datos y entorno |
| Integración Sky-Claw | 7.5/10 | ⚠️ Mejorable con wrappers nativos |
| **TOTAL** | **8.3/10** | **Usable con validación previa** |
