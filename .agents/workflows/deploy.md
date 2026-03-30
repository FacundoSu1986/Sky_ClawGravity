---
description: Inicia la aplicación Sky-Claw completa (daemon WSL2 + gateway Node.js + frontend). Usa para arrancar el sistema.
---

# Despliegue de Sky-Claw

Inicia todos los componentes de la aplicación Sky-Claw.

## Pasos

1. **Verificar prerequisitos** — comprobar que Python, Node.js, y las dependencias estén instaladas:
   ```bash
   python --version
   node --version
   ```

2. **Verificar que los servicios no estén ya corriendo** (evitar duplicados):
   ```bash
   Get-Process -Name python -ErrorAction SilentlyContinue
   Get-Process -Name node -ErrorAction SilentlyContinue
   ```

3. **Iniciar la aplicación** usando el script de arranque:
   ```bash
   cd e:\Pruba antigravity\Sky_Claw-main
   .\SkyClawApp.bat
   ```

4. **Verificar que los servicios estén activos**:
   - Daemon Python (WebSocket server)
   - Gateway Node.js (Telegram bridge)
   - Frontend (si aplica)

5. **Reportar estado** — mostrar URLs y puertos activos.

## Notas

- Si algún servicio falla al arrancar, verificar los logs en `logs/`.
- El daemon WSL2 requiere que WSL esté activo.
- El gateway necesita el token de Telegram configurado en variables de entorno.
