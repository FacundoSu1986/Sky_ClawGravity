# Plan Anti-Alucinación Gemini — Sky-Claw
<!-- Fecha: 2026-04-28 | Confianza: 0.85 | Estado: Investigación Completa -->

## Resumen Ejecutivo

Plan para implementar 3 barreras anti-alucinación cuando Gemini escribe código en el proyecto Sky-Claw:
1. **pre-commit** con `ruff` + `mypy`
2. **Script `gemini-write`** que pipea código generado → validación automática
3. **LSP activo** durante la escritura de Gemini

---

## 0. Estado Actual del Entorno (Inventario)

| Recurso | Estado | Detalle |
|---------|--------|---------|
| `.git/` | ✅ Existe | Pre-commit puede funcionar |
| `ruff` | ✅ v0.15.10 (venv), global (Python 3.14) | Configurado en `pyproject.toml` |
| `mypy` | ✅ v1.20.0 (venv), global (Python 3.14) | Configurado en `pyproject.toml` con strict parcial |
| `pytest` | ✅ v8.4.2 (venv) | `asyncio_mode = "auto"` |
| `pre-commit` | ❌ No instalado | Requiere `pip install pre-commit` |
| `.pre-commit-config.yaml` | ❌ No existe | Crear nuevo |
| `uv` | ✅ Disponible | `uv sync` funcional |
| `bash` (WSL) | ✅ Disponible | `C:\Windows\System32\bash.exe` |
| `npm`/`npx` | ✅ Disponible | Node.js via nvm4w |
| Gemini CLI | ❌ No instalado | No existe `gemini`, `gemini-cli` ni `google-genai` |
| Antigravity IDE | ✅ Activo | Panel Gemini integrado |
| Python venv | ✅ Python 3.13.12 | `.venv\Scripts\python.exe` |

---

## 1. pre-commit con ruff + mypy

### 1.1 Viabilidad: ✅ POSIBLE

**Confianza: P = 0.92**

El proyecto ya tiene `.git/`, `ruff`, y `mypy` configurados. Solo falta instalar `pre-commit` y crear el config.

### 1.2 Pasos de Implementación (~30 min)

#### Paso 1: Instalar pre-commit
```powershell
# Dentro del venv
.venv\Scripts\activate
uv add --dev pre-commit
```

O alternativamente:
```powershell
pip install pre-commit
```

#### Paso 2: Crear `.pre-commit-config.yaml`
```yaml
# .pre-commit-config.yaml
repos:
  # Ruff: lint + format en un solo paso
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.10  # Usar la versión instalada en el venv
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
        name: "ruff lint"
      - id: ruff-format
        name: "ruff format"

  # Mypy: type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.20.0  # Usar la versión instalada en el venv
    hooks:
      - id: mypy
        name: "mypy type-check"
        additional_dependencies:
          - pydantic>=2.0
          - types-aiofiles
        args: [--config-file=pyproject.toml]

  # Guardián: no print() en producción
  - repo: local
    hooks:
      - id: no-print
        name: "check: no print() in production"
        entry: 'print\('
        language: pygrep
        types: [python]
        exclude: ^tests/
```

#### Paso 3: Instalar hooks
```powershell
pre-commit install
pre-commit install --hook-type pre-push  # Doble barrera
```

#### Paso 4: Test inicial
```powershell
pre-commit run --all-files
```

### 1.3 Notas Críticas

- **Conflicto con git-guard**: La regla `git-guard.md` dice "NEVER `git init`". Como `.git` ya existe, `pre-commit install` solo escribe en `.git/hooks/` — no ejecuta `git init`. **No viola la regla.**
- **mypy strict parcial**: La config actual tiene `strict = false` global con overrides para módulos específicos. El pre-commit respetará esta config.
- **Performance**: `ruff` es ~100x más rápido que flake8. `mypy` incremental con cache en `.mypy_cache/`.

---

## 2. Script gemini-write (Pipe Gemini → pytest)

### 2.1 Viabilidad: ⚠️ PARCIALMENTE POSIBLE — Requiere Adaptación

**Confianza: P = 0.75**

#### Problema Identificado
No existe un **Gemini CLI standalone** instalado. El acceso a Gemini es a través del **panel del Antigravity IDE** (interfaz gráfica), no por CLI.

#### Solución: 3 Enfoques Alternativos

---

### Enfoque A: Script Python con Google GenAI SDK (RECOMENDADO)

**Confianza: P = 0.85**

Crear un script Python que use la API de Google GenAI para enviar prompts, recibir código, escribirlo a archivo, y ejecutar validación.

```python
# scripts/gemini_write.py
"""Gemini Write: Pipe Gemini code generation → ruff + mypy + pytest"""
import subprocess
import sys
from pathlib import Path

from google import genai


def call_gemini(prompt: str, model: str = "gemini-2.5-pro") -> str:
    """Send prompt to Gemini API and return generated code."""
    client = genai.Client()  # Uses GEMINI_API_KEY from env
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text


def extract_code(response: str) -> str:
    """Extract Python code from markdown response."""
    if "```python" in response:
        return response.split("```python")[1].split("```")[0]
    if "```" in response:
        return response.split("```")[1].split("```")[0]
    return response


def validate_with_ruff(filepath: Path) -> bool:
    """Run ruff check + format on the file."""
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--fix", str(filepath)],
        capture_output=True, text=True
    )
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", str(filepath)],
        capture_output=True, text=True
    )
    return result.returncode == 0


def validate_with_mypy(filepath: Path) -> bool:
    """Run mypy type checking on the file."""
    result = subprocess.run(
        [sys.executable, "-m", "mypy", str(filepath),
         "--config-file=pyproject.toml"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def run_tests(test_path: str = "tests/") -> bool:
    """Run pytest with short traceback."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-x", "--tb=short", test_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("❌ TESTS FAILED:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
    return result.returncode == 0


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Gemini Write Pipeline")
    parser.add_argument("--prompt", required=True, help="Prompt for Gemini")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--model", default="gemini-2.5-pro")
    parser.add_argument("--skip-tests", action="store_true")
    args = parser.parse_args()

    output_path = Path(args.output)

    # Step 1: Generate code with Gemini
    print(f"🤖 Generating code with {args.model}...")
    raw_response = call_gemini(args.prompt, args.model)
    code = extract_code(raw_response)

    # Step 2: Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(code, encoding="utf-8")
    print(f"📝 Written to {output_path}")

    # Step 3: Validate with ruff
    print("🔍 Running ruff...")
    ruff_ok = validate_with_ruff(output_path)
    if not ruff_ok:
        print("⚠️  ruff found issues (auto-fixed where possible)")

    # Step 4: Validate with mypy
    print("🔍 Running mypy...")
    mypy_ok = validate_with_mypy(output_path)
    if not mypy_ok:
        print("❌ mypy type errors detected")
        sys.exit(1)

    # Step 5: Run tests
    if not args.skip_tests:
        print("🧪 Running pytest...")
        tests_ok = run_tests()
        if not tests_ok:
            sys.exit(1)

    print("✅ All validations passed!")


if __name__ == "__main__":
    main()
```

**Dependencia nueva**: `google-genai` (SDK oficial de Google)
```powershell
uv add google-genai
```

**Uso**:
```powershell
python scripts/gemini_write.py --prompt "Implement X function" --output sky_claw/new_module.py
```

---

### Enfoque B: Wrapper PowerShell para Antigravity IDE

**Confianza: P = 0.70**

Crear un script PowerShell que:
1. Copie el código generado por Gemini desde el panel del IDE
2. Lo pegue en un archivo temporal
3. Ejecute `ruff check`, `mypy`, y `pytest -x --tb=short`

```powershell
# scripts/gemini-validate.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$FilePath
)

$ErrorActionPreference = "Stop"

Write-Host "🔍 Validating: $FilePath" -ForegroundColor Cyan

# Step 1: ruff
Write-Host "  → ruff check..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m ruff check --fix $FilePath
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ ruff failed" -ForegroundColor Red
    exit 1
}

# Step 2: mypy
Write-Host "  → mypy..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m mypy $FilePath --config-file=pyproject.toml
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ mypy failed" -ForegroundColor Red
    exit 1
}

# Step 3: pytest
Write-Host "  → pytest..." -ForegroundColor Yellow
& .venv\Scripts\python.exe -m pytest -x --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ tests failed" -ForegroundColor Red
    exit 1
}

Write-Host "✅ All validations passed!" -ForegroundColor Green
```

**Uso** (después de que Gemini escribe código):
```powershell
.\scripts\gemini-validate.ps1 -FilePath sky_claw\new_module.py
```

---

### Enfoque C: Gemini CLI vía npx (FUTURO)

**Confianza: P = 0.50**

Google no tiene un CLI oficial para Gemini equivalente a `claude-code`. Si en el futuro lanzan uno, el pipe sería:

```bash
# Hipotético - NO funcional hoy
npx @google/gemini-cli "Implement X" > sky_claw/new_module.py && \
  ruff check sky_claw/new_module.py && \
  mypy sky_claw/new_module.py && \
  pytest -x --tb=short
```

**Estado**: ❌ No disponible. Revisar en https://ai.google.dev/gemini-api/docs para actualizaciones.

---

### 2.2 Script Bash (WSL) — Adaptación Windows

Dado que el usuario pidió `.sh` pero el entorno es Windows con cmd.exe, se adapta como `.ps1`:

```powershell
# scripts/gemini-write.ps1
# Equivalente a gemini-write.sh para Windows
# Pipeline: Gemini API → ruff → mypy → pytest

param(
    [string]$Prompt,
    [string]$OutputFile,
    [string]$Model = "gemini-2.5-pro",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$python = ".venv\Scripts\python.exe"

# Generar código con Gemini via API
$code = & $python -c @"
from google import genai
import json, sys
client = genai.Client()
resp = client.models.generate_content(model='$Model', contents='''$Prompt''')
print(resp.text)
"@

# Extraer bloque de código
$code = $code -replace '(?s).*```python\s*', '' -replace '(?s)\s*```.*', ''

# Escribir archivo
$code | Out-File -FilePath $OutputFile -Encoding utf8

# Validar con ruff
& $python -m ruff check --fix $OutputFile
& $python -m ruff format $OutputFile

# Validar con mypy
& $python -m mypy $OutputFile --config-file=pyproject.toml

# Ejecutar tests
if (-not $SkipTests) {
    & $python -m pytest -x --tb=short
}
```

---

## 3. LSP Activo Durante Escritura de Gemini

### 3.1 Viabilidad: ✅ POSIBLE

**Confianza: P = 0.90**

### 3.2 Configuración Requerida

El Antigravity IDE está basado en VS Code. El LSP de Python (Pylance) ya debería estar disponible.

#### Verificar en `settings.json` del workspace:
```json
{
    "python.languageServer": "Pylance",
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.autoImportCompletions": true,
    "python.analysis.diagnosticSeverityOverrides": {
        "reportUnusedImport": "warning",
        "reportUnusedVariable": "warning",
        "reportMissingTypeStubs": "none"
    },
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true,
    "python.linting.ruffEnabled": true,
    "editor.formatOnSave": true,
    "editor.formatOnPaste": false,
    "editor.codeActionsOnSave": {
        "source.organizeImports": "explicit"
    }
}
```

#### Cómo funciona con Gemini:
1. **Gemini escribe código** en el panel del IDE → se inserta en el editor
2. **Pylance (LSP)** analiza el código en tiempo real
3. **Errores de tipo** aparecen como squiggles rojos inmediatamente
4. **ruff** marca problemas de linting como diagnostics
5. **El usuario ve los errores ANTES de guardar** → puede corregir o rechazar

#### Activación:
```powershell
# Verificar que Pylance está instalado
code --list-extensions | findstr "ms-python"
```

Extensiones requeridas:
- `ms-python.python` — Python extension
- `ms-python.vscode-pylance` — LSP (Pylance)
- `charliermarsh.ruff` — ruff integration en el editor

---

## 4. Plan de Ejecución (Timeline: 1 Tarde ~4 horas)

### Fase 1: Pre-commit (30 min)
| # | Tarea | Comando | Estado |
|---|-------|---------|--------|
| 1.1 | Instalar pre-commit | `uv add --dev pre-commit` | ⬜ |
| 1.2 | Crear `.pre-commit-config.yaml` | (ver sección 1.2) | ⬜ |
| 1.3 | Instalar hooks | `pre-commit install` | ⬜ |
| 1.4 | Test run | `pre-commit run --all-files` | ⬜ |

### Fase 2: Script gemini-write (1.5 horas)
| # | Tarea | Comando | Estado |
|---|-------|---------|--------|
| 2.1 | Instalar google-genai | `uv add google-genai` | ⬜ |
| 2.2 | Configurar API key | `setx GEMINI_API_KEY "..."` o keyring | ⬜ |
| 2.3 | Crear `scripts/gemini_write.py` | (ver Enfoque A) | ⬜ |
| 2.4 | Crear `scripts/gemini-validate.ps1` | (ver Enfoque B) | ⬜ |
| 2.5 | Test con archivo de ejemplo | `python scripts/gemini_write.py --prompt "..." --output test_output.py` | ⬜ |

### Fase 3: LSP (30 min)
| # | Tarea | Comando | Estado |
|---|-------|---------|--------|
| 3.1 | Verificar Pylance instalado | `code --list-extensions` | ⬜ |
| 3.2 | Configurar settings.json del workspace | (ver sección 3.2) | ⬜ |
| 3.3 | Instalar extensión ruff si falta | `code --install-extension charliermarsh.ruff` | ⬜ |
| 3.4 | Test: escribir código inválido y verificar squiggles | Manual | ⬜ |

### Fase 4: Integración y Test End-to-End (1 hora)
| # | Tarea | Comando | Estado |
|---|-------|---------|--------|
| 4.1 | Generar código con Gemini → validar → commit | Workflow completo | ⬜ |
| 4.2 | Verificar que pre-commit atrapa errores | Insertar error intencional | ⬜ |
| 4.3 | Documentar en README o QUICKSTART | Actualizar docs | ⬜ |

---

## 5. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| `pre-commit` lento en cada commit | Media | Bajo | Usar `pre-push` hook en vez de `pre-commit` para mypy pesado |
| Gemini API rate limits | Media | Medio | Implementar retry con backoff exponencial |
| `mypy` falla en módulos con `ignore_errors = true` | Baja | Bajo | Los overrides ya excluyen módulos no tipados |
| API key expuesta | Baja | Crítico | Usar `keyring` o variable de entorno, NUNCA hardcodear |
| Conflicto con git-guard rule | Baja | Crítico | `pre-commit install` NO ejecuta `git init`, solo escribe en `.git/hooks/` |

---

## 6. Dependencias Nuevas Requeridas

```
# Agregar a [project.optional-dependencies] dev
pre-commit>=3.7,<5
google-genai>=1.0,<2
types-aiofiles  # Para mypy stubs
```

---

## 7. Veredicto Final

| Componente | Viabilidad | Esfuerzo | Prioridad |
|------------|-----------|----------|-----------|
| pre-commit + ruff + mypy | ✅ Posible | 30 min | 🔴 Alta |
| gemini-write script | ⚠️ Posible con SDK | 1.5 horas | 🟡 Media |
| LSP activo | ✅ Posible | 30 min | 🟢 Alta |

**Conclusión**: Las 3 barreras son implementables en una tarde. La barrera #1 (pre-commit) es la de mayor ROI — atrapa errores de Gemini en cada commit sin intervención manual. La barrera #2 (script) requiere instalar el SDK de Google GenAI pero automatiza el flujo completo. La barrera #3 (LSP) es la más simple — solo requiere configuración del editor.

**Recomendación**: Implementar en orden 1 → 3 → 2. Pre-commit y LSP dan protección inmediata con mínimo esfuerzo. El script es el "nice to have" para automatización completa.
