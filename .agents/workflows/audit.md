---
description: Ejecuta una auditoría de seguridad completa sobre la base de código usando patrones del Purple Auditor (AST + Trust Boundaries + OWASP).
---

# Auditoría de Seguridad del Código

Realiza una auditoría de seguridad enterprise sobre el proyecto Sky-Claw.

## Pasos

1. **Mapear fronteras de confianza (Trust Boundaries)** — identificar todos los puntos de entrada/salida de datos:
   - Endpoints de API / WebSocket
   - Inputs de usuario vía Telegram Bot
   - Lectura/escritura de archivos y bases de datos
   - Llamadas a servicios externos

2. **Ejecutar análisis estático** sobre el código Python:
   ```bash
   cd e:\Pruba antigravity\sky-claw
   python -m pytest tests/ -v --tb=short 2>&1
   ```

3. **Buscar patrones de vulnerabilidad OWASP Top 10**:
   - SQL Injection (concatenación de strings en queries)
   - Prompt Injection (inputs no sanitizados al LLM)
   - RCE (eval/exec/subprocess sin sandbox)
   - Path Traversal (rutas de archivo no validadas)
   - Secret Exposure (credenciales hardcodeadas)

4. **Clasificar hallazgos** por severidad usando CVSS 4.0:
   | Severidad | Rango CVSS | Acción |
   |-----------|------------|--------|
   | 🔴 CRITICAL | 9.0 - 10.0 | Bloquear deployment, remediar inmediatamente |
   | 🟠 HIGH | 7.0 - 8.9 | Remediar antes del siguiente release |
   | 🟡 MEDIUM | 4.0 - 6.9 | Planificar remediación |
   | 🟢 LOW | 0.1 - 3.9 | Documentar y monitorear |

5. **Generar tabla de hallazgos** con formato:
   | ID | Severidad | Tipo | CWE | Ubicación | Parche Propuesto |

6. **Mapear a frameworks de compliance** (NIST CSF 2.0, ISO 27001) si aplica.

## Criterios de Éxito

- Cobertura de análisis ≥ 95% de archivos `.py`.
- Todos los hallazgos CRITICAL tienen parche propuesto.
- Reporte generado como artefacto markdown.
