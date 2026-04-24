---
name: metagpt-software-engineer
description: Generación de módulos completos y microservicios usando MetaGPT. Usar para "boilear" nuevos módulos o microservicios que sigan patrones conocidos, generando PRDs, diseño de arquitectura y código de sistema. No usar para correcciones de una sola línea ni si MetaGPT no está instalado y configurado.
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
  compatibility:
    - Python 3.11+
    - MetaGPT 0.7+
    - API keys (OpenAI / Anthropic) configuradas
---

# MetaGPT Software Engineer (Sky-Claw Integration)

Skill para utilizar el framework **MetaGPT** y simular un equipo de desarrollo (Product Manager, Architect, Engineer) generando una solución de software de extremo a extremo.

## 🎯 Propósito

- Generar PRDs y diseños de arquitectura desde requisitos de alto nivel.
- Producir múltiples archivos interconectados que formen una unidad funcional.
- "Boilear" nuevos módulos o microservicios.

## 📋 Cuándo Usar

| Escenario | Prioridad |
|-----------|-----------|
| Generar PRD y arquitectura para nuevo módulo | 🔴 Alta |
| Crear estructura de microservicio desde cero | 🟠 Media |
| Simulación de diseño end-to-end antes de implementar | 🟠 Media |

## ❌ Cuándo NO Usar

- Correcciones de una sola línea → usar `local-dev-aider-pairing`.
- Cuando el tiempo es crítico (MetaGPT es lento).
- Si no se dispone de API keys configuradas.

## 🔧 Prerrequisitos

```bash
pip install metagpt
# Configurar API keys en ~/.metagpt/config.yaml o variables de entorno
export OPENAI_API_KEY="sk-..."
```

## 🚀 Instrucciones de Uso

### Inicializar Proyecto MetaGPT
```bash
metagpt --init-config  # Genera config.yaml
```

### Ejecutar Simulación
```bash
metagpt "<descripción_detallada_del_sistema>"
```

**Ejemplo:**
```bash
metagpt "Diseña un servicio de notificaciones para Sky-Claw que soporte Telegram y email, con cola de mensajes SQLite y retry automático"
```

### Salida
MetaGPT generará una estructura de carpetas similar a:
```
output/
├── 2026-04-23_10-00-00/
│   ├── prd.md
│   ├── design.md
│   ├── system_architecture/
│   └── sky_claw_notifications/
│       ├── __init__.py
│       ├── main.py
│       └── ...
```

## ⚠️ Restricciones

- **Auditoría obligatoria:** Los archivos generados deben pasar por `skyclaw-purple-auditor` o `security-auditor-sast` antes de integrarse.
- **Revisión manual:** Los PRDs y diseños requieren validación humana antes de convertirse en código de producción.
- **Coste:** Cada ejecución consume tokens de LLM significativamente (múltiples rondas PM→Architect→Engineer).
- **Simulación pesada:** No usar para tareas triviales.

## 🎯 Score de la Skill

| Dimensión | Score | Estado |
|-----------|-------|--------|
| Realismo | 8.5/10 | ✅ Requiere setup real |
| Seguridad | 7/10 | ⚠️ Requiere auditoría post-generación |
| Coste | 6/10 | ⚠️ Alto consumo de tokens |
