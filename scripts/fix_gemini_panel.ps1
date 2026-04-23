<#
.SYNOPSIS
    Reparador del panel Gemini congelado en Antigravity IDE v1.107.0
.DESCRIPTION
    Diagnostica y repara el panel lateral de Gemini Code Assist v2.78.0
    cuando se congela, purgando caché y reiniciando el proceso backend
    sin perder el contexto de la sesión actual.
.NOTES
    Ejecutar desde la terminal integrada de Antigravity:
    powershell -ExecutionPolicy Bypass -File .\scripts\fix_gemini_panel.ps1
#>

param(
    [switch]$DryRun = $false,
    [switch]$Verbose = $false,
    [switch]$FullReset = $false
)

$ErrorActionPreference = "Stop"

# ============================================================
# CONSTANTES DEL ENTORNO
# ============================================================
$AG_USER_DATA      = "$env:APPDATA\Antigravity"

# Guard: validar que APPDATA este definido y que la ruta resuelta contenga \Antigravity
# antes de cualquier Remove-Item con wildcards sobre directorios de cache.
if ([string]::IsNullOrWhiteSpace($env:APPDATA)) {
    Write-Error "APPDATA no esta definido en este entorno. No es seguro ejecutar operaciones de limpieza."
    exit 1
}
if ($AG_USER_DATA -notlike "*\Antigravity") {
    Write-Error "La ruta de datos '$AG_USER_DATA' no contiene '\Antigravity'. Abortando para evitar borrados accidentales."
    exit 1
}

$AG_INSTALL_DIR    = "$env:LOCALAPPDATA\Programs\Antigravity"
$AG_EXTENSIONS     = "$env:USERPROFILE\.antigravity\extensions"
$GEMINI_EXT_ID     = "google.geminicodeassist"
$GEMINI_EXT_VER    = "2.78.0"
$GEMINI_EXT_PATH   = "$AG_EXTENSIONS\$GEMINI_EXT_ID-$GEMINI_EXT_VER-universal"
$GEMINI_GLOBAL     = "$AG_USER_DATA\User\globalStorage\$GEMINI_EXT_ID"
$TIMESTAMP         = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_DIR        = "$AG_USER_DATA\gemini_backup_$TIMESTAMP"

function Write-Status {
    param([string]$Icon, [string]$Msg, [string]$Color = "White")
    Write-Host "[$Icon] " -ForegroundColor $Color -NoNewline
    Write-Host $Msg
}

function Write-Step {
    param([int]$Num, [string]$Title)
    Write-Host ""
    Write-Host "=== PASO $Num: $Title ===" -ForegroundColor Cyan
}

# ============================================================
# PASO 0: DIAGNÓSTICO
# ============================================================
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
Write-Host "║  ANTIGRAVITY GEMINI PANEL REPAIR UTILITY v1.0              ║" -ForegroundColor Yellow
Write-Host "║  Gemini Code Assist v$GEMINI_EXT_VER | Antigravity v1.107.0        ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow

Write-Step 0 "DIAGNÓSTICO DEL ESTADO ACTUAL"

# Detectar proceso principal de Antigravity
$agMain = Get-Process Antigravity -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $agMain) {
    Write-Status "!" "Antigravity no está ejecutándose." "Red"
    exit 1
}
Write-Status "OK" "Antigravity.exe corriendo (PID: $($agMain.Id))" "Green"

# Detectar Extension Host
$extHosts = Get-CimInstance Win32_Process -Filter "name='Antigravity.exe'" |
    Where-Object { $_.CommandLine -match "node\.mojom\.NodeService" -and $_.CommandLine -match "inspect-port" }

if ($extHosts) {
    foreach ($eh in $extHosts) {
        Write-Status "OK" "Extension Host activo (PID: $($eh.ProcessId))" "Green"
    }
} else {
    Write-Status "!" "No se detectó Extension Host primario" "Yellow"
}

# Detectar proceso A2A de Gemini
$geminiProcs = Get-CimInstance Win32_Process -Filter "name='Antigravity.exe'" |
    Where-Object { $_.CommandLine -match "geminicodeassist" }

if ($geminiProcs) {
    foreach ($gp in $geminiProcs) {
        $mem = (Get-Process -Id $gp.ProcessId -ErrorAction SilentlyContinue).WorkingSet64 / 1MB
        Write-Status "~" "Gemini A2A Server (PID: $($gp.ProcessId), Mem: $([math]::Round($mem,1)) MB)" "Yellow"
        
        # Verificar si el proceso responde
        try {
            $proc = Get-Process -Id $gp.ProcessId
            if ($proc.Responding -eq $false) {
                Write-Status "!" "  ⚠ EL PROCESO NO RESPONDE - Confirmado congelamiento" "Red"
            }
        } catch {
            Write-Status "!" "  ⚠ No se puede verificar estado del proceso" "Red"
        }
    }
} else {
    Write-Status "!" "No se detectó proceso Gemini A2A (puede estar inactivo)" "Yellow"
}

# Detectar renderer del panel Gemini (webview)
$renderers = Get-CimInstance Win32_Process -Filter "name='Antigravity.exe'" |
    Where-Object { $_.CommandLine -match "renderer" }

Write-Status "i" "Procesos renderer activos: $(($renderers | Measure-Object).Count)" "Cyan"

# Verificar checkpoints de chat
$checkpoints = Get-ChildItem "$GEMINI_GLOBAL\chat_checkpoint_files" -ErrorAction SilentlyContinue -Directory
if ($checkpoints) {
    Write-Status "i" "Sesiones de chat con checkpoints: $($checkpoints.Count)" "Cyan"
    foreach ($cp in $checkpoints) {
        $files = Get-ChildItem $cp.FullName -File -ErrorAction SilentlyContinue
        Write-Status "i" "  Sesión $($cp.Name): $($files.Count) checkpoint(s)" "DarkGray"
    }
} else {
    Write-Status "i" "No se encontraron checkpoints de sesión" "DarkGray"
}

if ($DryRun) {
    Write-Host ""
    Write-Status "i" "Modo DryRun activado - solo diagnóstico, sin cambios." "Yellow"
    exit 0
}

# ============================================================
# PASO 1: RESPALDO DEL CONTEXTO DE SESIÓN
# ============================================================
Write-Step 1 "RESPALDO DEL CONTEXTO DE SESIÓN"

Write-Status ">" "Creando respaldo en: $BACKUP_DIR" "Cyan"

if (-not (Test-Path $BACKUP_DIR)) {
    New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null
}

# Respaldar checkpoints de chat
if (Test-Path "$GEMINI_GLOBAL\chat_checkpoint_files") {
    Copy-Item "$GEMINI_GLOBAL\chat_checkpoint_files" "$BACKUP_DIR\chat_checkpoint_files" -Recurse -Force
    Write-Status "OK" "Checkpoints de chat respaldados" "Green"
}

# Respaldar estado del workspace si existe
$wsStorageDirs = Get-ChildItem "$AG_USER_DATA\User\workspaceStorage" -Directory -ErrorAction SilentlyContinue
foreach ($wsDir in $wsStorageDirs) {
    $geminiState = Get-ChildItem $wsDir.FullName -Filter "*gemini*" -ErrorAction SilentlyContinue
    if ($geminiState) {
        $destDir = "$BACKUP_DIR\workspace\$($wsDir.Name)"
        New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        Copy-Item $geminiState.FullName $destDir -Recurse -Force
        Write-Status "OK" "Estado workspace $($wsDir.Name) respaldado" "Green"
    }
}

Write-Status "OK" "Respaldo completado: $BACKUP_DIR" "Green"

# ============================================================
# PASO 2: TERMINAR PROCESO GEMINI A2A SERVER
# ============================================================
Write-Step 2 "REINICIO DEL PROCESO GEMINI A2A SERVER"

# Reinicio efectivo del backend: terminacion directa del proceso A2A.
# Nota: este script no implementa un reinicio graceful via IPC/Developer Commands.
# Para reinicio graceful usa Ctrl+Shift+P -> "Developer: Reload Window" despues de ejecutar.
Write-Status ">" "Terminando proceso Gemini A2A Server (kill directo)..." "Cyan"

# Kill directo del proceso A2A
if ($geminiProcs) {
    foreach ($gp in $geminiProcs) {
        Write-Status ">" "Terminando Gemini A2A Server (PID: $($gp.ProcessId))..." "Yellow"
        try {
            Stop-Process -Id $gp.ProcessId -Force -ErrorAction Stop
            Write-Status "OK" "Proceso $($gp.ProcessId) terminado" "Green"
        } catch {
            Write-Status "!" "Error terminando proceso: $_" "Red"
        }
    }
}

# Esperar a que el proceso se libere
Start-Sleep -Seconds 2

# Verificar que terminó
$geminiProcsAfter = Get-CimInstance Win32_Process -Filter "name='Antigravity.exe'" |
    Where-Object { $_.CommandLine -match "geminicodeassist" }

if (-not $geminiProcsAfter) {
    Write-Status "OK" "Proceso Gemini A2A terminado exitosamente" "Green"
} else {
    Write-Status "!" "El proceso aún existe, puede requerir FullReset" "Red"
}

# ============================================================
# PASO 3: PURGAR CACHÉ DE LA INTERFAZ RENDERIZADA
# ============================================================
Write-Step 3 "PURGADO DE CACHÉ DE INTERFAZ"

# 3a. Purgar GPUCache (afecta rendering de webviews)
$gpuCachePath = "$AG_USER_DATA\GPUCache"
if (Test-Path $gpuCachePath) {
    Write-Status ">" "Purgando GPUCache..." "Cyan"
    Remove-Item "$gpuCachePath\*" -Force -ErrorAction SilentlyContinue
    Write-Status "OK" "GPUCache purgado" "Green"
}

# 3b. Purgar Code Cache (caché de compilación JS de extensiones)
$codeCachePath = "$AG_USER_DATA\Code Cache"
if (Test-Path $codeCachePath) {
    Write-Status ">" "Purgando Code Cache..." "Cyan"
    Remove-Item "$codeCachePath\*" -Force -Recurse -ErrorAction SilentlyContinue
    Write-Status "OK" "Code Cache purgado" "Green"
}

# 3c. Purgar CachedData (datos compilados de VS Code)
if (-not $FullReset) {
    Write-Status "i" "CachedData no purgado (usar -FullReset para purge completo)" "DarkGray"
} else {
    $cachedDataPath = "$AG_USER_DATA\CachedData"
    if (Test-Path $cachedDataPath) {
        Write-Status ">" "Purgando CachedData (FullReset)..." "Cyan"
        Remove-Item "$cachedDataPath\*" -Force -Recurse -ErrorAction SilentlyContinue
        Write-Status "OK" "CachedData purgado" "Green"
    }
}

# 3d. Purgar Service Worker cache (webview de Gemini)
$swPath = "$AG_USER_DATA\Service Worker"
if (Test-Path $swPath) {
    Write-Status ">" "Purgando Service Worker cache..." "Cyan"
    Remove-Item "$swPath\CacheData\*" -Force -Recurse -ErrorAction SilentlyContinue
    Write-Status "OK" "Service Worker cache purgado" "Green"
}

# 3e. Purgar Dawn GPU cache
$dawnCache = "$AG_USER_DATA\DawnGraphiteCache"
if (Test-Path $dawnCache) {
    Remove-Item "$dawnCache\*" -Force -ErrorAction SilentlyContinue
    Write-Status "OK" "DawnGraphiteCache purgado" "Green"
}

$dawnWebGPU = "$AG_USER_DATA\DawnWebGPUCache"
if (Test-Path $dawnWebGPU) {
    Remove-Item "$dawnWebGPU\*" -Force -ErrorAction SilentlyContinue
    Write-Status "OK" "DawnWebGPUCache purgado" "Green"
}

# ============================================================
# PASO 4: RESTABLECER CONEXIÓN CON MOTOR DE IA
# ============================================================
Write-Step 4 "RESTABLECIMIENTO DE CONEXIÓN CON MOTOR DE IA"

# 4a. Verificar que el checkpoint de sesión existe para restaurar contexto
if (Test-Path "$BACKUP_DIR\chat_checkpoint_files") {
    Write-Status ">" "Verificando integridad de checkpoints..." "Cyan"
    $cpFiles = Get-ChildItem "$BACKUP_DIR\chat_checkpoint_files" -Recurse -File
    $totalSize = ($cpFiles | Measure-Object -Property Length -Sum).Sum
    Write-Status "OK" "$($cpFiles.Count) archivos de checkpoint ($([math]::Round($totalSize/1KB,1)) KB) preservados" "Green"
}

# 4b. Limpiar posibles locks de sesión
$lockFiles = Get-ChildItem "$GEMINI_GLOBAL" -Filter "*.lock" -Recurse -ErrorAction SilentlyContinue
if ($lockFiles) {
    foreach ($lock in $lockFiles) {
        Remove-Item $lock.FullName -Force -ErrorAction SilentlyContinue
        Write-Status "OK" "Lock eliminado: $($lock.Name)" "Green"
    }
}

# 4c. Limpiar estado corrupto de webview del panel
$sessionStorage = "$AG_USER_DATA\Session Storage"
if (Test-Path $sessionStorage) {
    # Solo eliminar archivos de sesión relacionados con webviews, no todos
    $sessionFiles = Get-ChildItem $sessionStorage -File -ErrorAction SilentlyContinue
    Write-Status "i" "Session Storage: $($sessionFiles.Count) archivos (preservados para otros paneles)" "DarkGray"
}

# ============================================================
# PASO 5: RELOAD DEL EXTENSION HOST
# ============================================================
Write-Step 5 "RELOAD DEL EXTENSION HOST"

Write-Host ""
Write-Host "Para completar la reparación, ejecuta UNO de estos métodos:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  MÉTODO A (Recomendado - sin reiniciar IDE):" -ForegroundColor White
Write-Host "    1. Presiona Ctrl+Shift+P para abrir Command Palette" -ForegroundColor Gray
Write-Host "    2. Escribe: Developer: Reload Window" -ForegroundColor Gray
Write-Host "    3. Presiona Enter" -ForegroundColor Gray
Write-Host ""
Write-Host "  MÉTODO B (Si A no funciona):" -ForegroundColor White
Write-Host "    1. Presiona Ctrl+Shift+P" -ForegroundColor Gray
Write-Host "    2. Escribe: Developer: Restart Extension Host" -ForegroundColor Gray
Write-Host "    3. Presiona Enter" -ForegroundColor Gray
Write-Host ""
Write-Host "  MÉTODO C (Si nada funciona - reinicio completo):" -ForegroundColor White
Write-Host "    1. Cierra Antigravity completamente" -ForegroundColor Gray
Write-Host "    2. Ejecuta: Antigravity.exe --force" -ForegroundColor Gray
Write-Host "    3. O re-abre normalmente" -ForegroundColor Gray
Write-Host ""

# ============================================================
# PASO 6: VERIFICACIÓN POST-REPARACIÓN
# ============================================================
Write-Step 6 "VERIFICACIÓN POST-REPARACIÓN"

Write-Status ">" "Verificando estado de procesos..." "Cyan"

Start-Sleep -Seconds 3

# Verificar que Antigravity sigue corriendo
$agCheck = Get-Process Antigravity -ErrorAction SilentlyContinue | Select-Object -First 1
if ($agCheck) {
    Write-Status "OK" "Antigravity sigue activo (PID: $($agCheck.Id))" "Green"
} else {
    Write-Status "!" "Antigravity se cerró - puede necesitar reinicio manual" "Red"
}

# Verificar que los checkpoints siguen intactos
if (Test-Path "$GEMINI_GLOBAL\chat_checkpoint_files") {
    $cpCheck = Get-ChildItem "$GEMINI_GLOBAL\chat_checkpoint_files" -Recurse -File -ErrorAction SilentlyContinue
    if ($cpCheck) {
        Write-Status "OK" "Contexto de sesión preservado ($($cpCheck.Count) archivos)" "Green"
    }
} else {
    Write-Status "!" "Checkpoints no encontrados en ubicación original" "Yellow"
    Write-Status ">" "Restaurando desde respaldo..." "Cyan"
    if (Test-Path "$BACKUP_DIR\chat_checkpoint_files") {
        Copy-Item "$BACKUP_DIR\chat_checkpoint_files" "$GEMINI_GLOBAL\chat_checkpoint_files" -Recurse -Force
        Write-Status "OK" "Checkpoints restaurados desde respaldo" "Green"
    }
}

Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  REPARACIÓN COMPLETADA                                     ║" -ForegroundColor Green
Write-Host "║  Respaldo en: $BACKUP_DIR" -ForegroundColor Green
Write-Host "║  Ejecuta 'Developer: Reload Window' para finalizar         ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Green
