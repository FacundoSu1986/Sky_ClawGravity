---
description: Ejecuta el protocolo de endurecimiento de seguridad completo (AST Guardian, validación de rutas, PII redaction, credential vault).
---

# Protocolo de Hardening de Seguridad

Ejecuta el ciclo completo de endurecimiento de seguridad sobre el proyecto Sky-Claw.

## Pasos

1. **Ejecutar análisis estático AST Guardian** sobre todos los archivos `.py` del proyecto:
   ```bash
   cd e:\Pruba antigravity\Sky_Claw-main
   python -m pytest tests/ -k "ast_guardian or security" -v --tb=short
   ```

2. **Verificar que no existan llamadas prohibidas** (`eval`, `exec`, `__import__`, `compile`, `subprocess.call` con `shell=True`):
   ```bash
   cd e:\Pruba antigravity\Sky_Claw-main
   Get-ChildItem -Path sky_claw -Recurse -Filter "*.py" | Select-String -Pattern "eval\(|exec\(|__import__|compile\(|shell=True" -CaseSensitive
   ```

3. **Verificar sanitización de PII** en logs y outputs:
   ```bash
   cd e:\Pruba antigravity\Sky_Claw-main
   Get-ChildItem -Path sky_claw -Recurse -Filter "*.py" | Select-String -Pattern "password|secret|api_key|token" -CaseSensitive
   ```

4. **Validar integridad del CredentialVault** — revisar que no haya credenciales hardcodeadas:
   ```bash
   cd e:\Pruba antigravity\Sky_Claw-main
   Get-ChildItem -Path . -Recurse -Include "*.py","*.yaml","*.yml","*.json","*.toml" | Select-String -Pattern "sk-|ghp_|AKIA|password\s*=" -CaseSensitive
   ```

5. **Generar reporte de hallazgos** y presentar un resumen con tabla de severidades (CRITICAL / HIGH / MEDIUM / LOW).

## Criterios de Éxito

- Cero hallazgos CRITICAL o HIGH sin mitigación documentada.
- Todos los tests de seguridad pasan.
- No hay credenciales expuestas en el código fuente.
