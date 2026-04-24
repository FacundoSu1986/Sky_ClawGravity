---
name: verification-before-completion
description: Usar cuando estés a punto de afirmar que el trabajo está completo, arreglado, o pasando, antes de commitear o crear PRs — requiere ejecutar comandos de verificación y confirmar output antes de hacer cualquier afirmación de éxito; evidencia antes que afirmaciones siempre
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
---

# Verificación Antes de Completar

## Visión General

Afirmar que el trabajo está completo sin verificación es deshonestidad, no eficiencia.

**Principio core:** Evidencia antes que afirmaciones, siempre.

**Violating the letter of this rule is violating the spirit of this rule.**

## La Ley de Hierro

```
NO AFIRMACIONES DE COMPLETITUD SIN EVIDENCIA DE VERIFICACIÓN FRESCA
```

Si no has ejecutado el comando de verificación en este mensaje, no puedes afirmar que pasa.

## La Gate Function

```
ANTES de afirmar cualquier estado o expresar satisfacción:

1. IDENTIFICAR: ¿Qué comando prueba esta afirmación?
2. EJECUTAR: Ejecutar el comando COMPLETO (fresco, completo)
3. LEER: Output completo, chequear exit code, contar fallos
4. VERIFICAR: ¿El output confirma la afirmación?
   - Si NO: Estado actual con evidencia
   - Si SÍ: Afirmar la afirmación CON evidencia
5. SOLO ENTONCES: Hacer la afirmación

Saltar cualquier paso = mentir, no verificar
```

## Fallos Comunes

| Afirmación | Requiere | No es Suficiente |
|-------|----------|----------------|
| Tests pasan | Output del comando de test: 0 fallos | Ejecución previa, "debería pasar" |
| Linter limpio | Output del linter: 0 errores | Chequeo parcial, extrapolación |
| Build exitoso | Comando de build: exit 0 | Linter pasando, logs se ven bien |
| Bug arreglado | Test del síntoma original: pasa | Código cambiado, asumido arreglado |
| Test de regresión funciona | Ciclo red-green verificado | Test pasa una vez |
| Agente completó | VCS diff muestra cambios | Agente reporta "éxito" |
| Requisitos cumplidos | Checklist línea por línea | Tests pasando |

## Red Flags - DETENTE

- Usar "debería", "probablemente", "parece que"
- Expresar satisfacción antes de verificación ("¡Genial!", "¡Perfecto!", "¡Listo!", etc.)
- A punto de commitear/pushear/PR sin verificación
- Confiar en reportes de éxito de agentes
- Confiar en verificación parcial
- Pensar "solo esta vez"
- Cansado y queriendo terminar el trabajo
- **CUALQUIER redacción que implique éxito sin haber ejecutado verificación**

## Prevención de Racionalización

| Excusa | Realidad |
|--------|---------|
| "Debería funcionar ahora" | EJECUTA la verificación |
| "Estoy confiado" | Confianza ≠ evidencia |
| "Solo esta vez" | Sin excepciones |
| "El linter pasó" | Linter ≠ compilador |
| "El agente dijo éxito" | Verifica independientemente |
| "Estoy cansado" | Agotamiento ≠ excusa |
| "El chequeo parcial es suficiente" | Parcial no prueba nada |
| "Palabras diferentes así la regla no aplica" | Espíritu sobre letra |

## Patrones Clave

**Tests:**
```
✅ [Ejecutar comando de test] [Ver: 34/34 pasan] "Todos los tests pasan"
❌ "Debería pasar ahora" / "Se ve correcto"
```

**Tests de regresión (TDD Red-Green):**
```
✅ Escribir → Ejecutar (pasa) → Revertir fix → Ejecutar (DEBE FALLAR) → Restaurar → Ejecutar (pasa)
❌ "He escrito un test de regresión" (sin verificación red-green)
```

**Build:**
```
✅ [Ejecutar build] [Ver: exit 0] "El build pasa"
❌ "El linter pasó" (el linter no chequea compilación)
```

**Requisitos:**
```
✅ Re-leer plan → Crear checklist → Verificar cada uno → Reportar gaps o completitud
❌ "Tests pasan, fase completa"
```

**Delegación a agentes:**
```
✅ Agente reporta éxito → Chequear VCS diff → Verificar cambios → Reportar estado actual
❌ Confiar en reporte de agente
```

## Por Qué Importa

De 24 memorias de fallo:
- Tu socio humano dijo "No te creo" — confianza rota
- Funciones indefinidas enviadas — colapsarían
- Requisitos faltantes enviados — features incompletas
- Tiempo desperdiciado en falsas completitudes → redirección → rework
- Viola: "La honestidad es un valor core. Si mientes, serás reemplazado."

## Cuándo Aplicar

**SIEMPRE antes de:**
- CUALQUIER variación de afirmaciones de éxito/completitud
- CUALQUIER expresión de satisfacción
- CUALQUIER declaración positiva sobre estado del trabajo
- Commitear, crear PR, completar tarea
- Moverse a la siguiente tarea
- Delegar a agentes

**La regla aplica a:**
- Frases exactas
- Parafraseos y sinónimos
- Implicaciones de éxito
- CUALQUIER comunicación sugiriendo completitud/corrección

## La Línea de Fondo

**No hay atajos para la verificación.**

Ejecuta el comando. Lee el output. ENTONCES afirma el resultado.

Esto no es negociable.
