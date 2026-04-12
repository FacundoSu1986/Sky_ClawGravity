---
description: Ejecuta la suite completa de pruebas con pytest, genera reporte de cobertura y muestra resultados resumidos.
---

# Ejecución de Tests

Ejecuta la suite de pruebas del proyecto Sky-Claw y genera reporte de cobertura.

## Pasos

// turbo
1. **Ejecutar suite completa de tests con cobertura**:
   ```bash
   cd e:\Pruba antigravity\sky-claw
   python -m pytest tests/ -v --tb=short --cov=sky_claw --cov-report=term-missing 2>&1
   ```

2. **Analizar resultados**:
   - Identificar tests que fallaron y la causa raíz.
   - Verificar que la cobertura está por encima del 70%.
   - Si hay fallos, proponer correcciones.

3. **Si se requiere un test específico**, ejecutar con filtro:
   ```bash
   cd e:\Pruba antigravity\sky-claw
   python -m pytest tests/ -k "<nombre_del_test>" -v --tb=long 2>&1
   ```

4. **Generar reporte resumido** con:
   - Total de tests ejecutados
   - Tests pasados / fallidos / saltados
   - Porcentaje de cobertura por módulo
   - Módulos con cobertura baja (< 50%)

## Criterios de Éxito

- Todos los tests pasan (0 failures).
- Cobertura general ≥ 70%.
- No hay tests saltados sin justificación documentada.
