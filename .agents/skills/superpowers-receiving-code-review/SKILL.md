---
name: receiving-code-review
description: Usar al recibir feedback de code review, antes de implementar sugerencias, especialmente si el feedback parece poco claro o técnicamente cuestionable — requiere rigor técnico y verificación, no acuerdo performativo o implementación a ciegas
metadata:
  version: 1.0.0
  last_updated: 2026-04-23
---

# Recepción de Code Review

## Visión General

Code review requiere evaluación técnica, no performance emocional.

**Principio core:** Verificar antes de implementar. Preguntar antes de asumir. Corrección técnica sobre confort social.

## El Patrón de Respuesta

```
CUANDO recibes feedback de code review:

1. LEER: Feedback completo sin reaccionar
2. ENTENDER: Replantear requisito en palabras propias (o preguntar)
3. VERIFICAR: Chequear contra realidad del codebase
4. EVALUAR: ¿Técnicamente sólido para ESTE codebase?
5. RESPONDER: Reconocimiento técnico o pushback razonado
6. IMPLEMENTAR: Un item a la vez, testear cada uno
```

## Respuestas Prohibidas

**NUNCA:**
- "¡Tienes toda la razón!" (violación explícita de CLAUDE.md)
- "¡Buen punto!" / "¡Excelente feedback!" (performative)
- "Déjame implementar eso ahora" (antes de verificación)

**EN CAMBIO:**
- Replantear el requisito técnico
- Hacer preguntas clarificadoras
- Pushear con razonamiento técnico si está equivocado
- Simplemente empezar a trabajar (acciones > palabras)

## Manejando Feedback Poco Claro

```
SI algún item es poco claro:
  DETENTE — no implementes nada todavía
  PIDE clarificación sobre items poco claros

POR QUÉ: Los items pueden estar relacionados. Entendimiento parcial = implementación equivocada.
```

**Ejemplo:**
```
Tu socio humano: "Arreglar 1-6"
Tú entiendes 1,2,3,6. Poco claro en 4,5.

❌ MAL: Implementar 1,2,3,6 ahora, preguntar sobre 4,5 después
✅ BIEN: "Entiendo items 1,2,3,6. Necesito clarificación sobre 4 y 5 antes de proceder."
```

## Manejo Específico por Fuente

### De tu socio humano
- **Trusted** — implementar después de entender
- **Aún preguntar** si el scope es poco claro
- **Sin acuerdo performativo**
- **Saltar a acción** o reconocimiento técnico

### De Reviewers Externos
```
ANTES de implementar:
  1. Chequear: ¿Técnicamente correcto para ESTE codebase?
  2. Chequear: ¿Rompe funcionalidad existente?
  3. Chequear: ¿Razón para la implementación actual?
  4. Chequear: ¿Funciona en todas las plataformas/versiones?
  5. Chequear: ¿El reviewer entiende el contexto completo?

SI la sugerencia parece equivocada:
  Pushear con razonamiento técnico

SI no puedes verificar fácilmente:
  Di: "No puedo verificar esto sin [X]. ¿Debería [investigar/preguntar/proceder]?"

SI conflictúa con decisiones previas de tu socio humano:
  Detente y discute con tu socio humano primero
```

**Regla de tu socio humano:** "Feedback externo — sé escéptico, pero revisa cuidadosamente"

## YAGNI Check para Features "Profesionales"

```
SI el reviewer sugiere "implementar propiamente":
  grep codebase para uso actual

  SI no usado: "Este endpoint no es llamado. ¿Lo removemos (YAGNI)?"
  SI usado: Entonces implementar propiamente
```

**Regla de tu socio humano:** "Tú y el reviewer reportan a mí. Si no necesitamos esta feature, no la agregues."

## Orden de Implementación

```
PARA feedback multi-item:
  1. Clarificar todo lo poco claro PRIMERO
  2. Luego implementar en este orden:
     - Issues bloqueantes (breaks, seguridad)
     - Fixes simples (typos, imports)
     - Fixes complejos (refactoring, lógica)
  3. Testear cada fix individualmente
  4. Verificar no regressions
```

## Cuándo Pushear

Pushear cuando:
- La sugerencia rompe funcionalidad existente
- El reviewer carece de contexto completo
- Viola YAGNI (feature no usada)
- Técnicamente incorrecto para este stack
- Existen razones de legacy/compatibility
- Conflictúa con decisiones arquitectónicas de tu socio humano

**Cómo pushear:**
- Usar razonamiento técnico, no defensiva
- Hacer preguntas específicas
- Referenciar tests/código funcionando
- Involver a tu socio humano si es arquitectónico

**Señal si te sientes incómodo pusheando en voz alta:** "Strange things are afoot at the Circle K"

## Reconociendo Feedback Correcto

Cuando el feedback ES correcto:
```
✅ "Arreglado. [Breve descripción de qué cambió]"
✅ "Buena captura — [issue específico]. Arreglado en [ubicación]."
✅ [Simplemente arreglarlo y mostrar en el código]

❌ "¡Tienes toda la razón!"
❌ "¡Buen punto!"
❌ "¡Gracias por capturar eso!"
❌ "Gracias por [cualquier cosa]"
❌ CUALQUIER expresión de gratitud
```

**Por qué no gracias:** Las acciones hablan. Simplemente arréglalo. El código mismo muestra que escuchaste el feedback.

**Si te descubres a punto de escribir "Gracias":** BÓRRALO. Enuncia el fix en su lugar.

## Corrigiendo Tu Pushback Gracefully

Si pusheaste y estabas equivocado:
```
✅ "Tenías razón — revisé [X] y efectivamente hace [Y]. Implementando ahora."
✅ "Verifiqué esto y tienes razón. Mi entendimiento inicial estaba equivocado porque [razón]. Arreglando."

❌ Disculpa larga
❌ Defendiendo por qué pusheaste
❌ Sobre-explicando
```

Enuncia la corrección factualmente y sigue adelante.

## Errores Comunes

| Error | Fix |
|---------|-----|
| Acuerdo performativo | Enunciar requisito o simplemente actuar |
| Implementación a ciegas | Verificar contra codebase primero |
| Batch sin testing | Uno a la vez, testear cada uno |
| Asumiendo que el reviewer tiene razón | Chequear si rompe cosas |
| Evitando pushback | Corrección técnica > confort |
| Implementación parcial | Clarificar todos los items primero |
| No puedo verificar, proceder igual | Enunciar limitación, pedir dirección |

## Ejemplos Reales

**Acuerdo Performativo (Malo):**
```
Reviewer: "Remove legacy code"
❌ "¡Tienes toda la razón! Déjame remover eso..."
```

**Verificación Técnica (Bueno):**
```
Reviewer: "Remove legacy code"
✅ "Chequeando... build target es 10.15+, esta API necesita 13+. Necesitamos legacy para backward compat. La implementación actual tiene bundle ID equivocado — ¿lo arreglamos o dropeamos soporte pre-13?"
```

**YAGNI (Bueno):**
```
Reviewer: "Implement proper metrics tracking with database, date filters, CSV export"
✅ "Grepeé codebase — nada llama este endpoint. ¿Lo removemos (YAGNI)? ¿O hay uso que estoy omitiendo?"
```

**Item Poco Claro (Bueno):**
```
Tu socio humano: "Arreglar items 1-6"
Tú entiendes 1,2,3,6. Poco claro en 4,5.
✅ "Entiendo 1,2,3,6. Necesito clarificación sobre 4 y 5 antes de implementar."
```

## Replies en Threads de GitHub

Al responder a inline review comments en GitHub, responde en el thread del comentario (`gh api repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`), no como un comentario top-level del PR.

## La Línea de Fondo

**Feedback externo = sugerencias a evaluar, no órdenes a seguir.**

Verifica. Cuestiona. Luego implementa.

Sin acuerdo performativo. Rigor técnico siempre.
