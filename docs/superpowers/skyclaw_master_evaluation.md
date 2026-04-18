# Evaluación Estratégica y Arquitectónica de Sky-Claw (Visión 2026)

## 1. Estado Actual de la Arquitectura y Capacidades

Sky-Claw opera actualmente como un orquestador híbrido autónomo-interactivo, diseñado para automatizar y gestionar el ciclo de vida de los mods en *The Elder Scrolls V: Skyrim SE/AE* a través de Mod Organizer 2 (MO2). 

### 1.1 ¿Qué hace exactamente?
En su estado presente, la herramienta es capaz de procesar lenguaje natural por CLI, GUI (sv-ttk) o Telegram para ejecutar comandos de instalación. Automatiza descargas asíncronas desde NexusMods, maneja instalaciones complejas parseando instaladores FOMOD, y ejecuta reordenamientos básicos y parches mediante wrappers "headless" sobre LOOT y xEdit (SSEEdit). Utiliza un sistema robusto de HITL (Human-in-the-Loop) mediante Telegram para asegurar que las descargas externas y operaciones destructivas reciban aprobación manual.

### 1.2 Arquitectura Subyacente
El sistema exhibe un diseño modular de capas (Layered Architecture):
- **Capa de Interfaces de Entrada:** Capta intenciones mediante CLI Terminal, GUI local o Webhooks de Telegram.
- **Router y Capa de Providers LLM:** Un enrutador central de intenciones analiza el input usando adaptadores agnósticos (Soporte simultáneo de Anthropic, OpenAI, DeepSeek y locales vía Ollama). 
- **Tool Registry Asíncrono:** Una colección de herramientas aisladas (ej. `download_mod`, `run_loot_sort`, `check_load_order`) invocadas de manera determinista por el LLM.
- **Capa de Dominio de Modding (VFS/MO2):** Módulos que interactúan en tiempo real y gestionan el Virtual File System, estructuran la carpeta virtual de MO2 y manipulan el `modlist.txt` e `.ini` de Skyrim.
- **Seguridad Zero-Trust:** Un Gateway estricto restringe e inspecciona las direcciones IP y URLs permitidas en las descargas. 

### 1.3 Procesamiento de la Información
Sky-Claw procesa el contexto del usuario extrayendo intenciones mediante *FastEmbed* (embeddings vectoriales subyacentes), comparándolo con metadatos previamente almacenados en bases SQLite distribuidas (`async_registry.py`). Aplica un razonamiento heurístico rudimentario estilo "Tree of Thoughts" (ToT) para discernir si un mod depende de otro antes de la instalación y resolver las dependencias faltantes invocando la tool de búsqueda nuevamente.

---

## 2. Auditoría Crítica de Carencias (Hacia la Visión 2026)

Para que Sky-Claw trascienda la automatización básica y se posicione como el agente definitivo de modding de Skyrim en 2026, el análisis estructural revela brechas funcionales urgentes:

### 2.1 Carencia de Herramientas de Integración Final (The Capstone Tools)
1. **Motores de Comportamiento (Behavior Engines):** El agente ignora la ejecución de *Nemesis Unlimited Behavior Engine* o el moderno *Pandora Behaviour Engine*. Esto es crítico: instalar mods modernos de combate y animaciones hoy resulta inútil sin actualizar la pipeline de animación de FNIS/Nemesis de forma automática al final del load order.
2. **Generadores Dinámicos de LOD (DynDOLOD 3 y TexGen):** La capacidad del entorno remoto para automatizar el renderizado visual de largo alcance está bloqueada. La ejecución síncrona/timeout actual de DynDOLOD es ineficiente y no está adaptada a parámetros de configuración según el hardware del usuario.
3. **Patching Estructural Complejo:** Aunque tiene acceso básico a xEdit, no integra frameworks como *Synthesis* ni gestores de "Leveled Lists" robustos como *Wrye Bash* (para la creación de un Bashed Patch final automatizado de forma desprotegida/autónoma).

### 2.2 Brechas en la Arquitectura de Conocimiento (RAG y Constraints)
El asistente actualmente confía demasiado en el conocimiento *zero-shot* de sus propios LLMs base sobre el "lore" y arquitectura de Skyrim.
- Debería integrarse una Base de Datos Vectorial (como Chroma o Qdrant) pre-poblada con la documentación técnica de Modding 2026: guías de *S.T.E.P. Modifications*, dependencias y conflictos frecuentes de los 1000 mods más en Nexus.

### 2.3 Problemas en Capacidades de Agente Autónomo
- **Grafo de Conflictos Estacionario:** La validación de conflictos mediante bases de datos SQLite es plana. El agente carece de un modelo gráfico acíclico dirigido (DAG) robusto que advierta la ruptura de mallas (Navmeshes vs Modelos vs Scripts) a lo largo de interacciones complejas en largas Load Orders (+1500 mods). 
- **Backpressure y Timeouts Asíncronos:** Diversas tareas complejas (descompresión masiva de zip, invocaciones sub-process de xEdit) saturan el Queue asíncrono y bloquean la memoria de Windows vía VFS, limitando su capacidad para desplegar "Wabbajack-like" modlists masivas de manera autónoma.

---

## 3. Prompt Maestro Formatívo e Instructivo

Para inyectar en el `system_prompt` de la nueva instancia u otras agencias cognitivas encargadas de asimilar y escalar Sky-Claw:

> ***
> Eres Sky-Claw, la Inteligencia Artificial Arquitecta y Ejecutora Definitiva para The Elder Scrolls V: Skyrim (SE/AE) en su ecosistema tecnológico de 2026. Tu esencia es dotar a Mod Organizer 2 (MO2) de autonomía cognitiva pura, permitiendo que cualquier usuario ensamble listas de mods impecables de forma declarativa. 
> 
> Tu arquitectura base consta de adaptadores modulares, inyección robusta de dependencias SQLite y un protocolo de seguridad Zero-Trust con confirmaciones "Human-in-the-Loop". **Escúchame con claridad**: tu principal directriz no es solo descargar archivos; debes mantener la estabilidad homeostática de todo el Virtual File System de Skyrim, eludiendo bucles infinitos, corrupciones de archivos master y colisiones en Leveled Lists.
> 
> **Tu Misión Actual e Integración de Carencias:**
> 1. **Domina el Grafo de Load Order:** No te conformarás con LOOT. Debes estructurar, depurar y generar simulaciones temporales (Tree-of-Thoughts) sobre conflictos topológicos entre plugins `.esp`/`.esm`/`.esl` y sus empaquetados `.bsa`, antes de ordenar un despliegue real en VFS.
> 2. **Orquesta la Cadena de Herramientas Final (The Capstone Pipeline):** Debes diseñar e incorporar wrappers asíncronos limpios e infalibles para herramientas terminales críticas: compila animaciones invocando *Pandora Behaviour Engine* sin fricción, automatiza *Synthesis* introduciendo los mutators adecuados según la carga, y programa un sondeo de hilos desvinculados para ejecutar *TexGen* y *DynDOLOD 3* garantizando que el usuario tenga un horizonte visual HD sin requerir intervención manual.
> 3. **Gestión Autónoma Resiliente:** Si una instancia de xEdit, LODGen o una descarga masiva de FOMOD bloquea sus operaciones I/O en disco, detectarás el estancamiento e interrumpirás la subtarea (Circuit Breaker local) ejecutando limpiezas atómicas por "Rollback". Tu código siempre se asegurará de cerrar recursos.
> 4. **Conocimiento RAG de Modding Moderno:** Considerarás que gran parte de los parches clásicos están obsoletos en 2026. Utilizarás bases de conocimiento vectorizadas subyacentes para inferir cómo interaccionan las físicas modernas (SMP/HDT), animaciones OAR de nueva generación y sistemas parallax modernos; evitando sugerir parches antiguos y obsoletos y previniendo inestabilidades catastróficas.
> 
> Te conduces con extrema profesionalidad de ingeniero, no asumes sin validar el VFS, reescribes el código priorizando asincronismo escalable (aiofiles, aiohttp) e impones una disciplina de código estricta, modular y completamente tipada (PEP 484/526). Empieza a ejecutar.
> ***
