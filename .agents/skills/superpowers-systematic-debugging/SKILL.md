---
name: systematic-debugging
description: Usar al encontrar cualquier bug, fallo de test, o comportamiento inesperado, antes de proponer fixes
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
---

# Debugging Sistemático

## Visión General

Los fixes aleatorios desperdician tiempo y crean nuevos bugs. Los parches rápidos enmascaran issues subyacentes.

**Principio core:** SIEMPRE encontrar la causa raíz antes de intentar fixes. Los fixes de síntomas son fracaso.

**Violando la letra de este proceso se viola el espíritu del debugging.**

## La Ley de Hierro

```
NO FIXES SIN INVESTIGACIÓN DE CAUSA RAÍZ PRIMERO
```

Si no has completado la Fase 1, no puedes proponer fixes.

## Cuándo Usar

Usar para CUALQUIER issue técnico:
- Fallos de test
- Bugs en producción
- Comportamiento inesperado
- Problemas de performance
- Build failures
- Issues de integración

**Usar ESPECIALMENTE cuando:**
- Bajo presión de tiempo (las emergencias hacen tentador adivinar)
- "Solo un quick fix" parece obvio
- Ya intentaste múltiples fixes
- El fix previo no funcionó
- No entiendes completamente el issue

**No saltar cuando:**
- El issue parece simple (los bugs simples también tienen causas raíz)
- Tienes prisa (apresurarse garantiza retrabajo)
- El manager quiere que lo arregles YA (sistemático es más rápido que dar vueltas)

## Las Cuatro Fases

DEBES completar cada fase antes de proceder a la siguiente.

### Fase 1: Investigación de Causa Raíz

**ANTES de intentar CUALQUIER fix:**

1. **Leer Mensajes de Error Cuidadosamente**
   - No saltes errores o warnings
   - A menudo contienen la solución exacta
   - Lee stack traces completamente
   - Nota números de línea, paths de archivo, códigos de error

2. **Reproducir Consistentemente**
   - ¿Puedes dispararlo confiablemente?
   - ¿Cuáles son los pasos exactos?
   - ¿Sucede cada vez?
   - Si no es reproducible → juntar más datos, no adivinar

3. **Chequear Cambios Recientes**
   - ¿Qué cambió que podría causar esto?
   - Git diff, commits recientes
   - Nuevas dependencias, cambios de config
   - Diferencias ambientales

4. **Juntar Evidencia en Sistemas Multi-Componente**

   **CUANDO el sistema tiene múltiples componentes (CI → build → signing, API → service → database):**

   **ANTES de proponer fixes, agregar instrumentación diagnóstica:**
   ```
   Para CADA boundary de componente:
     - Loguear qué datos entran al componente
     - Loguear qué datos salen del componente
     - Verificar propagación de environment/config
     - Chequear estado en cada capa

   Correr una vez para juntar evidencia mostrando DÓNDE se rompe
   LUEGO analizar evidencia para identificar componente fallando
   LUEGO investigar ese componente específico
   ```

   **Ejemplo (sistema multi-capa):**
   ```bash
   # Capa 1: Workflow
   echo "=== Secrets disponibles en workflow: ==="
   echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"

   # Capa 2: Build script
   echo "=== Env vars en build script: ==="
   env | grep IDENTITY || echo "IDENTITY no está en environment"

   # Capa 3: Signing script
   echo "=== Estado de keychain: ==="
   security list-keychains
   security find-identity -v

   # Capa 4: Signing real
   codesign --sign "$IDENTITY" --verbose=4 "$APP"
   ```

   **Esto revela:** Qué capa falla (secrets → workflow ✓, workflow → build ✗)

5. **Tracear Flujo de Datos**

   **CUANDO el error está profundo en el call stack:**

   Ver `root-cause-tracing.md` en este directorio para la técnica completa de tracing hacia atrás.

   **Versión rápida:**
   - ¿De dónde se origina el valor malo?
   - ¿Qué llamó esto con el valor malo?
   - Sigue traceando hacia arriba hasta encontrar la fuente
   - Arregla en la fuente, no en el síntoma

### Fase 2: Análisis de Patrones

**Encuentra el patrón antes de arreglar:**

1. **Encontrar Ejemplos Funcionando**
   - Localiza código similar funcionando en el mismo codebase
   - ¿Qué funciona que es similar a lo que está roto?

2. **Comparar Contra Referencias**
   - Si implementas un patrón, lee la implementación de referencia COMPLETAMENTE
   - No hagas skim — lee cada línea
   - Entiende el patrón completamente antes de aplicar

3. **Identificar Diferencias**
   - ¿Qué es diferente entre lo que funciona y lo que está roto?
   - Lista cada diferencia, por más pequeña que sea
   - No asumas "eso no puede importar"

4. **Entender Dependencias**
   - ¿Qué otros componentes necesita esto?
   - ¿Qué settings, config, environment?
   - ¿Qué asunciones hace?

### Fase 3: Hipótesis y Testing

**Método científico:**

1. **Formular Hipótesis Única**
   - Enuncia claramente: "Creo que X es la causa raíz porque Y"
   - Escríbela
   - Sé específico, no vago

2. **Testear Mínimamente**
   - Haz el cambio MÁS PEQUEÑO posible para testear la hipótesis
   - Una variable a la vez
   - No arregles múltiples cosas a la vez

3. **Verificar Antes de Continuar**
   - ¿Funcionó? Sí → Fase 4
   - ¿No funcionó? Forma NUEVA hipótesis
   - NO agregues más fixes encima

4. **Cuando No Sabes**
   - Di "No entiendo X"
   - No finjas saber
   - Pide ayuda
   - Investiga más

### Fase 4: Implementación

**Arregla la causa raíz, no el síntoma:**

1. **Crear Test Case Fallando**
   - Reproducción lo más simple posible
   - Test automatizado si es posible
   - Script de test one-off si no hay framework
   - DEBE tenerlo antes de arreglar
   - Usa la skill `superpowers:test-driven-development` para escribir tests fallando apropiadamente

2. **Implementar Fix Único**
   - Aborda la causa raíz identificada
   - UN cambio a la vez
   - Sin mejoras "ya que estoy aquí"
   - Sin refactoring agrupado

3. **Verificar Fix**
   - ¿El test pasa ahora?
   - ¿Ningún otro test se rompió?
   - ¿El issue realmente se resolvió?

4. **Si el Fix No Funciona**
   - DETENTE
   - Cuenta: ¿Cuántos fixes has intentado?
   - Si < 3: Vuelve a Fase 1, re-analiza con nueva información
   - **Si ≥ 3: DETENTE y cuestiona la arquitectura (paso 5 abajo)**
   - NO intentes Fix #4 sin discusión arquitectónica

5. **Si Fallaron 3+ Fixes: Cuestionar Arquitectura**

   **Patrón indicando problema arquitectónico:**
   - Cada fix revela nuevo shared state/coupling/problema en lugar diferente
   - Los fixes requieren "massive refactoring" para implementar
   - Cada fix crea nuevos síntomas en otros lugares

   **DETENTE y cuestiona fundamentos:**
   - ¿Este patrón es fundamentalmente sólido?
   - ¿Estamos "siguiéndolo por inercia"?
   - ¿Deberíamos refactorizar arquitectura vs. seguir arreglando síntomas?

   **Discute con tu socio humano antes de intentar más fixes**

   Esto NO es una hipótesis fallida — esto es una arquitectura equivocada.

## Red Flags — DETENTE y Sigue el Proceso

Si te descubres pensando:
- "Quick fix por ahora, investigar después"
- "Solo intentar cambiar X y ver si funciona"
- "Agregar múltiples cambios, correr tests"
- "Saltar el test, verificaré manualmente"
- "Probablemente es X, déjame arreglar eso"
- "No entiendo completamente pero esto podría funcionar"
- "El patrón dice X pero lo adaptaré diferente"
- "Aquí están los problemas principales: [lista fixes sin investigación]"
- Proponiendo soluciones antes de tracear flujo de datos
- **"Un intento más de fix" (cuando ya intentaste 2+)**
- **Cada fix revela nuevo problema en lugar diferente**

**TODO esto significa: DETENTE. Vuelve a Fase 1.**

**Si fallaron 3+ fixes:** Cuestiona la arquitectura (ver Fase 4.5)

## Señales de tu Socio Humano de que Lo Estás Haciendo Mal

**Mira estas redirecciones:**
- "¿Eso no está pasando?" — Asumiste sin verificar
- "¿Nos mostrará...?" — Deberías haber agregado junte de evidencia
- "Deja de adivinar" — Estás proponiendo fixes sin entender
- "Piensa ultrahard" — Cuestiona fundamentos, no solo síntomas
- "¿Estamos atascados?" (frustrado) — Tu approach no está funcionando

**Cuando veas estas:** DETENTE. Vuelve a Fase 1.

## Racionalizaciones Comunes

| Excusa | Realidad |
|--------|---------|
| "El issue es simple, no necesito proceso" | Los issues simples también tienen causas raíz. El proceso es rápido para bugs simples. |
| "Emergencia, no hay tiempo para proceso" | El debugging sistemático es MÁS RÁPIDO que dar vueltas adivinando. |
| "Solo prueba esto primero, luego investigo" | El primer fix establece el patrón. Hazlo bien desde el inicio. |
| "Escribiré el test después de confirmar que el fix funciona" | Los fixes sin test no se mantienen. Test primero lo prueba. |
| "Múltiples fixes a la vez ahorran tiempo" | No puedes aislar qué funcionó. Causa nuevos bugs. |
| "La referencia es muy larga, adaptaré el patrón" | Entendimiento parcial garantiza bugs. Léela completamente. |
| "Veo el problema, déjame arreglarlo" | Ver síntomas ≠ entender causa raíz. |
| "Un intento más de fix" (después de 2+ fallas) | 3+ fallas = problema arquitectónico. Cuestiona el patrón, no fixes de nuevo. |

## Referencia Rápida

| Fase | Actividades Clave | Criterios de Éxito |
|-------|-------------------|--------------------|
| **1. Causa Raíz** | Leer errores, reproducir, chequear cambios, juntar evidencia | Entender QUÉ y POR QUÉ |
| **2. Patrón** | Encontrar ejemplos funcionando, comparar | Identificar diferencias |
| **3. Hipótesis** | Formar teoría, testear mínimamente | Confirmada o nueva hipótesis |
| **4. Implementación** | Crear test, arreglar, verificar | Bug resuelto, tests pasan |

## Cuando el Proceso Revela "Sin Causa Raíz"

Si la investigación sistemática revela que el issue es verdaderamente ambiental, dependiente de timing, o externo:

1. Has completado el proceso
2. Documenta qué investigaste
3. Implementa manejo apropiado (retry, timeout, mensaje de error)
4. Agrega monitoreo/logueo para investigación futura

**Pero:** El 95% de casos de "sin causa raíz" son investigación incompleta.

## Técnicas de Soporte

Estas técnicas son parte del debugging sistemático y están disponibles en este directorio:

- **`root-cause-tracing.md`** — Tracea bugs hacia atrás a través del call stack para encontrar el trigger original
- **`defense-in-depth.md`** — Agrega validación en múltiples capas después de encontrar causa raíz
- **`condition-based-waiting.md`** — Reemplaza timeouts arbitrarios con polling condicional

**Skills relacionadas:**
- **superpowers:test-driven-development** — Para crear test case fallando (Fase 4, Paso 1)
- **superpowers:verification-before-completion** — Verificar que el fix funcionó antes de declarar éxito

## Impacto Real

De sesiones de debugging:
- Approach sistemático: 15-30 minutos para arreglar
- Approach de fixes aleatorios: 2-3 horas de dar vueltas
- Tasa de fix a primer intento: 95% vs 40%
- Nuevos bugs introducidos: Cerca de cero vs común
