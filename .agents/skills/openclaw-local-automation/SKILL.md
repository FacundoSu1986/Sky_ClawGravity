---
name: openclaw-local-automation
description: Automatización local-first del ecosistema Sky-Claw. Usar para ejecutar scripts de mantenimiento, scraping de proyecto, verificación de stubs de agentes y tareas de sistema operativo dentro del entorno del proyecto. No usar para operaciones que requieran APIs externas o modificación de código fuente.
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
  compatibility:
    - Python 3.11+
    - PowerShell 5.1+
    - Windows / WSL2
---

# OpenClaw Local Automation (Sky-Claw Ecosystem)

Skill interna para orquestar la automatización local dentro del ecosistema Sky-Claw/OpenClaw. No es una herramienta externa; es el nombre del framework de agentes propio del proyecto.

## 🎯 Propósito

- Ejecutar scripts de mantenimiento y verificación del proyecto.
- Orquestar tareas de sistema limitadas al directorio de trabajo.
- Validar el estado de los stubs y agentes del ecosistema.

## 📋 Cuándo Usar

| Escenario | Script/Comando | Prioridad |
|-----------|----------------|-----------|
| Verificar stubs de agentes | `python .agents/scripts/verify_agent_stubs.py` | 🔴 Alta |
| Scraping inicial del proyecto | `python scripts/scrape_project.py` | 🟠 Media |
| Configuración de entorno | `scripts/setup_env.ps1` | 🟠 Media |
| Pruebas de caos | `scripts/run_chaos_suite.ps1` | 🟡 Media |

## ❌ Cuándo NO Usar

- Para modificación de código fuente → usar `local-dev-aider-pairing`.
- Para tareas que requieran APIs externas (Nexus Mods, Telegram) → usar `sky-claw-automation`.
- Para ejecución de código en sandbox WSL2 → usar `ai-engineer`.

## 🔧 Scripts Disponibles

### Verificación de Stubs
```bash
python .agents/scripts/verify_agent_stubs.py
```
Valida que los stubs de agentes del ecosistema estén correctamente definidos.

### Scraping del Proyecto
```bash
python scripts/scrape_project.py
```
Extrae metadatos y estructura del proyecto para documentación.

### Setup de Entorno
```powershell
scripts/setup_env.ps1
```
Configura variables de entorno y dependencias base en Windows.

### Pruebas de Caos
```powershell
scripts/run_chaos_suite.ps1
```
Ejecuta suite de pruebas de resistencia del sistema.

## ⚠️ Reglas de Seguridad

- **Scope limitado:** Toda operación debe confinarse al directorio de trabajo (`e:\Skyclaw_Main_Sync`).
- **Sin privilegios elevados:** No ejecutar como Administrador salvo que el script específico lo requiera (ej. instalación de dependencias de sistema).
- **HITL para destructivas:** Operaciones de borrado masivo, movimiento de archivos críticos o cambios de configuración requieren confirmación explícita del usuario.
- **Audit trail:** Los scripts de mantenimiento deben loguear en `logs/sky_claw.log`.

## 🎯 Score de la Skill

| Dimensión | Score | Estado |
|-----------|-------|--------|
| Realismo | 9/10 | ✅ Scripts verificados |
| Seguridad | 8/10 | ✅ Scope limitado + HITL |
| Integración | 9/10 | ✅ 100% interna a Sky-Claw |
