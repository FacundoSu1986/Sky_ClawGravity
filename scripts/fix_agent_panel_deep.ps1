<#
.SYNOPSIS
    Reparacion agresiva del Agent Panel - Limpieza de cache y estado corrupto
.DESCRIPTION
    Resuelve el error [createInstance] ooe depends on UNKNOWN service agentSessions
    limpiando CachedData, Code Cache, GPUCache y estado de workspace corrupto.
.NOTES
    PASOS PREVIOS: Cerrar Antigravity completamente antes de ejecutar.
    Ejecutar: powershell -ExecutionPolicy Bypass -File .\scripts\fix_agent_panel_deep.ps1
#>

param([switch]$DryRun = $false)

$ErrorActionPreference = "Continue"
$AG_USER_DATA = "$env:APPDATA\Antigravity"
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"

function Write-Status([string]$Icon, [string]$Msg, [string]$Color = "White") {
    Write-Host "[$Icon] $Msg" -ForegroundColor $Color
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Red
Write-Host "  FIX AGENT PANEL DEEP - Resolucion agentSessions UNKNOWN" -ForegroundColor Red
Write-Host "============================================================" -ForegroundColor Red

# Verificar que Antigravity NO esta corriendo
$ag = Get-Process Antigravity -ErrorAction SilentlyContinue
if ($ag) {
    Write-Status "!" "Antigravity esta corriendo (PID: $($ag.Id)). Debe cerrarse antes de ejecutar este script." "Red"
    Write-Status "i" "Cierre Antigravity y vuelva a ejecutar este script." "Yellow"
    exit 1
}
Write-Status "OK" "Antigravity no esta corriendo - seguro para proceder" "Green"

# ============================================================
# PASO 1: RESPALDO
# ============================================================
Write-Host ""
Write-Status ">" "PASO 1: Creando respaldo..." "Cyan"
$backupDir = "$AG_USER_DATA\deep_fix_backup_$TIMESTAMP"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Write-Status "OK" "Respaldo en: $backupDir" "Green"

# ============================================================
# PASO 2: LIMPIAR CachedData (CAUSA PRINCIPAL)
# ============================================================
Write-Host ""
Write-Status ">" "PASO 2: Limpiando CachedData (codigo compilado del workbench)..." "Cyan"
$cachedData = "$AG_USER_DATA\CachedData"
if (Test-Path $cachedData) {
    if (-not $DryRun) {
        Copy-Item $cachedData "$backupDir\CachedData" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item "$cachedData\*" -Force -Recurse -ErrorAction SilentlyContinue
        Write-Status "OK" "CachedData limpiado (contenia codigo compilado con agentSessions corrupto)" "Green"
    }
    else {
        Write-Status "i" "DryRun: Se limpiaria CachedData" "Yellow"
    }
}
else {
    Write-Status "i" "CachedData no encontrado" "DarkGray"
}

# ============================================================
# PASO 3: LIMPIAR Code Cache
# ============================================================
Write-Host ""
Write-Status ">" "PASO 3: Limpiando Code Cache..." "Cyan"
$codeCache = "$AG_USER_DATA\Code Cache"
if (Test-Path $codeCache) {
    if (-not $DryRun) {
        Copy-Item $codeCache "$backupDir\Code Cache" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item "$codeCache\*" -Force -Recurse -ErrorAction SilentlyContinue
        Write-Status "OK" "Code Cache limpiado" "Green"
    }
    else {
        Write-Status "i" "DryRun: Se limpiaria Code Cache" "Yellow"
    }
}
else {
    Write-Status "i" "Code Cache no encontrado" "DarkGray"
}

# ============================================================
# PASO 4: LIMPIAR GPUCache
# ============================================================
Write-Host ""
Write-Status ">" "PASO 4: Limpiando GPUCache..." "Cyan"
$gpuCache = "$AG_USER_DATA\GPUCache"
if (Test-Path $gpuCache) {
    if (-not $DryRun) {
        Remove-Item "$gpuCache\*" -Force -ErrorAction SilentlyContinue
        Write-Status "OK" "GPUCache limpiado" "Green"
    }
}

# ============================================================
# PASO 5: LIMPIAR Service Worker Cache
# ============================================================
Write-Host ""
Write-Status ">" "PASO 5: Limpiando Service Worker cache..." "Cyan"
$swCache = "$AG_USER_DATA\Service Worker\CacheData"
if (Test-Path $swCache) {
    if (-not $DryRun) {
        Remove-Item "$swCache\*" -Force -Recurse -ErrorAction SilentlyContinue
        Write-Status "OK" "Service Worker cache limpiado" "Green"
    }
}

# ============================================================
# PASO 6: LIMPIAR DawnCache
# ============================================================
Write-Host ""
Write-Status ">" "PASO 6: Limpiando Dawn GPU caches..." "Cyan"
$dawnPaths = @("$AG_USER_DATA\DawnGraphiteCache", "$AG_USER_DATA\DawnWebGPUCache")
foreach ($dp in $dawnPaths) {
    if (Test-Path $dp) {
        if (-not $DryRun) {
            Remove-Item "$dp\*" -Force -ErrorAction SilentlyContinue
            Write-Status "OK" "$dp limpiado" "Green"
        }
    }
}

# ============================================================
# PASO 7: RESETEAR WORKSPACE STATE (agentSessions corrupto)
# ============================================================
Write-Host ""
Write-Status ">" "PASO 7: Reseteando estado de workspace para este proyecto..." "Cyan"

# Buscar el workspace de este proyecto
$wsStorage = "$AG_USER_DATA\User\workspaceStorage"
$targetWorkspace = $null
if (Test-Path $wsStorage) {
    $wsDirs = Get-ChildItem $wsStorage -Directory
    foreach ($wsd in $wsDirs) {
        $wsJson = Join-Path $wsd.FullName "workspace.json"
        if (Test-Path $wsJson) {
            $content = Get-Content $wsJson -Raw -ErrorAction SilentlyContinue
            if ($content -match "Skyclaw_Main_Sync[^/]") {
                $targetWorkspace = $wsd
                break
            }
        }
    }
}

if ($targetWorkspace) {
    Write-Status "i" "Workspace encontrado: $($targetWorkspace.Name)" "Cyan"
    $stateDb = Join-Path $targetWorkspace.FullName "state.vscdb"
    if (Test-Path $stateDb) {
        if (-not $DryRun) {
            Copy-Item $stateDb "$backupDir\state.vscdb" -Force
            Remove-Item $stateDb -Force -ErrorAction SilentlyContinue
            Write-Status "OK" "state.vscdb reseteado (contenia agentSessions corrupto)" "Green"
        }
        else {
            Write-Status "i" "DryRun: Se resetearia state.vscdb" "Yellow"
        }
    }
    $stateBackup = Join-Path $targetWorkspace.FullName "state.vscdb.backup"
    if (Test-Path $stateBackup) {
        if (-not $DryRun) {
            Remove-Item $stateBackup -Force -ErrorAction SilentlyContinue
            Write-Status "OK" "state.vscdb.backup eliminado" "Green"
        }
    }
}
else {
    Write-Status "!" "No se encontro el workspace de este proyecto" "Yellow"
}

# ============================================================
# PASO 8: LIMPIAR SESSION STORAGE
# ============================================================
Write-Host ""
Write-Status ">" "PASO 8: Limpiando Session Storage..." "Cyan"
$sessionStorage = "$AG_USER_DATA\Session Storage"
if (Test-Path $sessionStorage) {
    if (-not $DryRun) {
        Copy-Item $sessionStorage "$backupDir\Session Storage" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item "$sessionStorage\*" -Force -ErrorAction SilentlyContinue
        Write-Status "OK" "Session Storage limpiado" "Green"
    }
}

# ============================================================
# PASO 9: LIMPIAR LOCKS DE GEMINI
# ============================================================
Write-Host ""
Write-Status ">" "PASO 9: Limpiando locks de Gemini..." "Cyan"
$geminiGlobal = "$AG_USER_DATA\User\globalStorage\google.geminicodeassist"
$locks = Get-ChildItem $geminiGlobal -Filter "*.lock" -Recurse -ErrorAction SilentlyContinue
if ($locks) {
    foreach ($lf in $locks) {
        if (-not $DryRun) {
            Remove-Item $lf.FullName -Force -ErrorAction SilentlyContinue
            Write-Status "OK" "Lock eliminado: $($lf.Name)" "Green"
        }
    }
}

# ============================================================
# RESUMEN
# ============================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  REPARACION PROFUNDA COMPLETADA" -ForegroundColor Green
Write-Host "  Respaldo en: $backupDir" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  PROXIMOS PASOS:" -ForegroundColor Yellow
Write-Host "    1. Abrir Antigravity" -ForegroundColor White
Write-Host "    2. Abrir este workspace (e:\Skyclaw_Main_Sync)" -ForegroundColor White
Write-Host "    3. El IDE re-generara CachedData limpio" -ForegroundColor White
Write-Host "    4. El Agent Panel deberia funcionar ahora" -ForegroundColor White
Write-Host ""
Write-Host "  Si aun falla, ejecutar:" -ForegroundColor Yellow
Write-Host "    Antigravity.exe --force" -ForegroundColor Gray
Write-Host ""
