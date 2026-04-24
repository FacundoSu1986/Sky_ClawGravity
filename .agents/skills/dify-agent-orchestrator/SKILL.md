---
name: dify-agent-orchestrator
description: Orquestación de flujos RAG y workflows de conocimiento usando una instancia Dify self-hosted local. Usar cuando se necesite ejecutar pipelines de conocimiento complejos, RAG avanzado o UI de agentes low-code sobre infraestructura propia. No usar para tareas de codificación directa ni si no hay una instancia Dify desplegada.
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
  compatibility:
    - Docker Compose
    - Python 3.11+
    - Sky-Claw Ecosystem
---

# Dify Agent Orchestrator (Sky-Claw Integration)

Skill para interactuar con una instancia **Dify self-hosted** local dentro del ecosistema Sky-Claw. Requiere despliegue previo; no es un servicio cloud ni un CLI portable.

## 🎯 Propósito

- Ejecutar flujos de trabajo (workflows) definidos visualmente en Dify.
- Consultar bases de conocimiento indexadas localmente.
- Gestionar pipelines de RAG con control total de los datos.

## 📋 Cuándo Usar

| Escenario | Prioridad |
|-----------|-----------|
| Ejecutar workflow de RAG sobre documentación interna | 🔴 Alta |
| Consultar Knowledge Base indexada localmente | 🔴 Alta |
| Actualizar documentos en Dify desde el IDE | 🟠 Media |

## ❌ Cuándo NO Usar

- Si no existe una instancia Dify desplegada localmente.
- Para tareas de codificación directa → usar `local-dev-aider-pairing`.
- Para datos en tiempo real de Nexus Mods → usar `sky-claw-automation`.

## 🔧 Prerrequisitos

1. **Despliegue local de Dify** (Docker Compose):
   ```bash
   cd <dify-repo>/docker/
   docker compose up -d
   ```
2. **API Key configurada** en variables de entorno o `.env`:
   ```bash
   DIFY_API_KEY=your-api-key
   DIFY_BASE_URL=http://localhost/v1
   ```

## 🚀 Instrucciones de Uso

### Ejecutar Workflow
```bash
curl -X POST "${DIFY_BASE_URL}/workflows/${WORKFLOW_ID}/run" \
  -H "Authorization: Bearer ${DIFY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"inputs": {"query": "<tu_consulta>"}}'
```

### Desde Python
```python
import requests

response = requests.post(
    f"{dify_base_url}/workflows/{workflow_id}/run",
    headers={"Authorization": f"Bearer {dify_api_key}"},
    json={"inputs": {"query": "conflictos de mods"}}
)
result = response.json()
```

## ⚠️ Restricciones

- **Self-hosted obligatorio:** No usar endpoints cloud si la soberanía de datos es requerida.
- **API Key segura:** Nunca commitear la API Key. Usar variables de entorno o gestor de secretos.
- **Scope de enriquecimiento:** Su propósito es enriquecimiento de contexto, no modificación de código.

## 🎯 Score de la Skill

| Dimensión | Score | Estado |
|-----------|-------|--------|
| Realismo | 9/10 | ✅ Requiere infraestructura real |
| Seguridad | 8.5/10 | ✅ Local-only + API Key |
| Integración | 7/10 | ⚠️ Requiere setup previo del usuario |
