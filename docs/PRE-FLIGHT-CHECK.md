# 🛡️ Guía de Auditoría de Seguridad (Pre-Flight Check) - Abril 2026

Sky-Claw v5.5 introduce el **Motor de Auditoría Purple Team**, diseñado para proteger tu entorno local antes de realizar operaciones de alto riesgo como `git clone`, `pip install` o la instalación de mods externos desconocidos.

## 🧠 El Marco Metacognitivo (5 Pasos)

Cada vez que solicitas un análisis, el agente ejecuta un ciclo de razonamiento estructurado:

1. **DESCOMPONER**: Mapeo de archivos y fronteras de confianza (Trust Boundaries).
2. **RESOLVER**: Escaneo AST avanzado (detecta ofuscación sin palabras clave liteales) e inspección de texto (detecta Indirect Prompt Injection en MD/TXT).
3. **VERIFICAR**: Cruce con la base de firmas offline y la lista blanca local (`.purple_whitelist.json`).
4. **SINTETIZAR**: Agregación de riesgos y cálculo de **Confianza Ponderada**.
5. **REFLEXIONAR**: Decisión final. Si la confianza es `< 0.8`, el agente bloqueará la ejecución y solicitará tu intervención.

## 🚀 Cómo Realizar una Auditoría

### 1. Auditoría de un Repositorio Externo
Antes de clonar un repositorio, puedes pedirle a Sky-Claw que pre-audite el contenido (si ya está descargado o en una carpeta temporal):

```bash
python -m sky_claw security scan ./carpeta_descargada
```

El agente responderá con un reporte detallado:
- **Confianza ≥ 0.9**: ✅ Seguro de usar.
- **0.7 ≤ Confianza < 0.9**: 🟠 Sospechoso. Revisa los hallazgos críticos.
- **Confianza < 0.7**: 🔴 BLOQUEADO. El código contiene patrones de ataque polimórficos de 2026.

### 2. Gestión de Falsos Positivos (HITL)
Si el agente bloquea un archivo que sabes que es seguro (ej. un cargador de mods sofisticado):

1. Inspecciona el reporte de hallazgos.
2. Si estás seguro, puedes aprobarlo manualmente:
   ```bash
   python -m sky_claw security approve ./ruta/archivo.py
   ```
   Esto añadirá el hash del archivo a la whitelist local y el agente no volverá a alertar sobre él a menos que el archivo cambie.

## ⚠️ Amenazas de Abril 2026: Lo que debes saber

- **The Little LLM Virus**: Instrucciones maliciosas ocultas en archivos `README.md` que el LLM intenta ejecutar al "leer" el repositorio. El **TextInspector** de Sky-Claw ahora escanea estos patrones automáticamente.
- **Ofuscación por Atributos**: Ataques que usan `getattr(__builtins__, "exec")` para evitar que escáneres simples detecten la palabra "exec". El **PurpleScanner** rastrea el flujo de estas constantes para detectar la intención real.
- **Inyección por Homoglifos**: El uso de caracteres Unicode que se ven idénticos pero envían comandos diferentes. Sky-Claw alerta sobre cualquier anomalía Unicode sospechosa.

---

*Configuración generada por Antigravity AI - v5.5 "THE ORACLE'S MEMORY"*
