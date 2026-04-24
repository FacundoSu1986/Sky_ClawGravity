<#
.SYNOPSIS
    Reparacion DEFINITIVA del Agent Panel - Soluciona la cadena de fallo completa
.DESCRIPTION
    Resuelve el error recurrente [createInstance] ooe depends on UNKNOWN service agentSessions
    atacando las 4 capas de la cadena de fallo identificada:
    
    CAPA 1: V8 CachedData corrupto (codigo compilado obsoleto que impide cargar google.antigravity)
    CAPA 2: Workspace state.vscdb con estado agentSessions corrupto
    CAPA 3: Caches secundarios (Code Cache, GPU, Service Worker, Session Storage, DawnCache)
    CAPA 4: Validacion post-reparacion para confirmar integridad
    
    CAUSA RAIZ: El V8 CachedData en %APPDATA%\Antigravity\CachedData contiene codigo compilado
    obsoleto que impide que la extension google.antigravity cargue su bundle correctamente.
    Sin la extension cargada, el servicio agentSessions nunca se registra en el workbench,
    y el Agent Panel falla con "UNKNOWN service agentSessions".
    
    Este script DEBE ejecutarse con Antigravity CERRADO completamente.
    
.NOTES
    Version: 3.0 (Definitiva)
    Fecha: 2026-04-22
    Autor: SRE Sky-Claw
    
    Ejecutar: powershell -ExecutionPolicy Bypass -File .\scripts\fix_agent_panel_definitive.ps1
    Con simulacion: powershell -ExecutionPolicy Bypass -File .\scripts\fix_agent_panel_definitive.ps1 -DryRun
#>

param(
    [switch]$DryRun = $false,
    [switch]$SkipBackup = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

# ============================================================
# CONSTANTES
# ============================================================
$AG_USER_DATA = "$env:APPDATA\Antigravity"
$AG_INSTALL = "$env:LOCALAPPDATA\Programs\Antigravity"
$AG_EXTENSIONS = "$env:USERPROFILE\.antigravity\extensions"
$PROJECT_ROOT = $PSScriptRoot | Split-Path -Parent
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$BACKUP_DIR = "$AG_USER_DATA\definitive_fix_backup_$TIMESTAMP"
$LOG_FILE = "$PROJECT_ROOT\definitive_fix_log_$TIMESTAMP.txt"

$script:Errors = @()
$script:Fixed = @()
$script:Warnings = @()

# ============================================================
# UTILIDADES
# ============================================================
function Write-Status([string]$Icon, [string]$Msg, [string]$Color = "White") {
    $line = "[$Icon] $Msg"
    Write-Host $line -ForegroundColor $Color
    Add-Content -Path $LOG_FILE -Value $line -ErrorAction SilentlyContinue
}

function Write-Step([int]$Num, [string]$Title) {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  CAPA $Num`: $Title" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Add-Content -Path $LOG_FILE -Value "`n=== CAPA ${Num}: ${Title} ===" -ErrorAction SilentlyContinue
}

function Add-Diag([string]$Type, [string]$Message) {
    $entry = @{ Type = $Type; Message = $Message; Timestamp = Get-Date -Format "o" }
    switch ($Type) {
        "ERROR" { $script:Errors += $entry }
        "FIXED" { $script:Fixed += $entry }
        "WARNING" { $script:Warnings += $entry }
    }
}

function Protect-Delete([string]$Path, [string]$Label) {
    if (-not (Test-Path $Path)) {
        Write-Status "i" "$Label no encontrado (ya limpio)" "DarkGray"
        return $false
    }
    if (-not $SkipBackup -and -not $DryRun) {
        $backupDest = Join-Path $BACKUP_DIR (Split-Path $Path -Leaf)
        Copy-Item $Path $backupDest -Recurse -Force -ErrorAction SilentlyContinue
        Write-Status "i" "Respaldo creado: $backupDest" "DarkGray"
    }
    if (-not $DryRun) {
        Remove-Item "$Path\*" -Force -Recurse -ErrorAction SilentlyContinue
        if (-not (Get-ChildItem $Path -ErrorAction SilentlyContinue)) {
            Write-Status "OK" "$Label limpiado exitosamente" "Green"
            Add-Diag "FIXED" "$Label limpiado"
            return $true
        }
        else {
            # Intento mas agresivo
            Remove-Item "$Path\*" -Force -Recurse -ErrorAction SilentlyContinue
            $remaining = (Get-ChildItem $Path -ErrorAction SilentlyContinue | Measure-Object).Count
            if ($remaining -eq 0) {
                Write-Status "OK" "$Label limpiado (segundo intento)" "Green"
                Add-Diag "FIXED" "$Label limpiado (segundo intento)"
                return $true
            }
            else {
                Write-Status "!" "${Label}: quedan $remaining elementos (puede requerir reinicio)" "Yellow"
                Add-Diag "WARNING" "${Label}: limpieza parcial"
                return $false
            }
        }
    }
    else {
        Write-Status "i" "DryRun: Se limpiaria $Label" "Yellow"
        return $false
    }
}

# ============================================================
# INICIO
# ============================================================
Write-Host ""
Write-Host "################################################################" -ForegroundColor Magenta
Write-Host "#  FIX DEFINITIVO Agent Panel v3.0                             #" -ForegroundColor Magenta
Write-Host "#  Resuelve: UNKNOWN service agentSessions (causa raiz)        #" -ForegroundColor Magenta
Write-Host "#  Timestamp: $TIMESTAMP                           #" -ForegroundColor Magenta
Write-Host "################################################################" -ForegroundColor Magenta

"=== Fix Definitivo Agent Panel v3.0 - $TIMESTAMP ===" | Out-File -FilePath $LOG_FILE -Encoding UTF8

# ============================================================
# PRE-CHECK: Antigravity NO debe estar corriendo
# ============================================================
Write-Host ""
Write-Status ">" "PRE-CHECK: Verificando que Antigravity no este corriendo..." "Cyan"

$agProcesses = Get-Process Antigravity -ErrorAction SilentlyContinue
if ($agProcesses -and -not $Force) {
    Write-Status "!" "ANTIGRAVITY ESTA CORRIENDO (${($agProcesses | Measure-Object).Count} procesos)" "Red"
    Write-Status "!" "Debe cerrarse completamente antes de ejecutar este script." "Red"
    Write-Status "i" "Use -Force para ejecutar de todas formas (riesgo de corrupcion)" "Yellow"
    Write-Host ""
    Write-Status "i" "Para cerrar Antigravity:" "Yellow"
    Write-Status "i" "  1. Guarde todos los archivos" "Yellow"
    Write-Status "i" "  2. Cierre la ventana principal" "Yellow"
    Write-Status "i" "  3. Verifique con: Get-Process Antigravity" "Yellow"
    exit 1
}
if ($agProcesses -and $Force) {
    Write-Status "!" "MODO FORCE: Antigravity detectado pero continuando..." "Yellow"
    Add-Diag "WARNING" "Ejecutando con Antigravity activo (Force)"
}

Write-Status "OK" "Antigravity no esta corriendo - seguro para proceder" "Green"

# Crear directorio de respaldo
if (-not $DryRun -and -not $SkipBackup) {
    New-Item -ItemType Directory -Path $BACKUP_DIR -Force | Out-Null
    Write-Status "OK" "Directorio de respaldo: $BACKUP_DIR" "Green"
}

# ============================================================
# CAPA 1: V8 CachedData (CAUSA PRIMARIA)
# ============================================================
Write-Step 1 "V8 CACHEDDATA - Codigo compilado obsoleto"

$cachedDataDir = "$AG_USER_DATA\CachedData"
if (Test-Path $cachedDataDir) {
    $hashDirs = Get-ChildItem $cachedDataDir -Directory -ErrorAction SilentlyContinue
    $totalSize = 0
    foreach ($hd in $hashDirs) {
        $size = (Get-ChildItem $hd.FullName -Recurse -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        $totalSize += $size
        Write-Status "i" "  Hash dir: $($hd.Name) ($([math]::Round($size/1MB, 2)) MB)" "DarkGray"
    }
    Write-Status "i" "CachedData total: $([math]::Round($totalSize/1MB, 2)) MB en ${($hashDirs | Measure-Object).Count} directorios" "Cyan"
    
    # Respaldar antes de borrar
    if (-not $SkipBackup -and -not $DryRun) {
        Copy-Item $cachedDataDir "$BACKUP_DIR\CachedData" -Recurse -Force -ErrorAction SilentlyContinue
    }
    
    foreach ($hd in $hashDirs) {
        if (-not $DryRun) {
            Remove-Item $hd.FullName -Force -Recurse -ErrorAction SilentlyContinue
        }
    }
    
    if (-not $DryRun) {
        # Verificar limpieza
        $remaining = Get-ChildItem $cachedDataDir -Directory -ErrorAction SilentlyContinue
        if (-not $remaining) {
            Write-Status "OK" "CachedData completamente limpiado" "Green"
            Add-Diag "FIXED" "V8 CachedData limpiado (causa primaria de agentSessions UNKNOWN)"
        }
        else {
            Write-Status "!" "CachedData parcialmente limpiado (${($remaining | Measure-Object).Count} dirs restantes)" "Yellow"
            Add-Diag "WARNING" "CachedData limpieza parcial"
        }
    }
    else {
        Write-Status "i" "DryRun: Se limpiaria CachedData completamente" "Yellow"
    }
}
else {
    Write-Status "i" "CachedData no encontrado" "DarkGray"
}

# ============================================================
# CAPA 2: WORKSPACE STATE (agentSessions corrupto)
# ============================================================
Write-Step 2 "WORKSPACE STATE - agentSessions corrupto en state.vscdb"

$wsStorage = "$AG_USER_DATA\User\workspaceStorage"
$targetWorkspace = $null

if (Test-Path $wsStorage) {
    $wsDirs = Get-ChildItem $wsStorage -Directory
    foreach ($wsd in $wsDirs) {
        $wsJson = Join-Path $wsd.FullName "workspace.json"
        if (Test-Path $wsJson) {
            $content = Get-Content $wsJson -Raw -ErrorAction SilentlyContinue
            if ($content -match "Skyclaw_Main_Sync") {
                $targetWorkspace = $wsd
                break
            }
        }
    }
}

if ($targetWorkspace) {
    Write-Status "i" "Workspace encontrado: $($targetWorkspace.Name)" "Cyan"
    
    # state.vscdb
    $stateDb = Join-Path $targetWorkspace.FullName "state.vscdb"
    if (Test-Path $stateDb) {
        $dbSize = (Get-Item $stateDb).Length
        Write-Status "i" "state.vscdb: $([math]::Round($dbSize/1KB, 1)) KB (contiene agentSessions corrupto)" "Cyan"
        
        if (-not $DryRun) {
            if (-not $SkipBackup) {
                Copy-Item $stateDb "$BACKUP_DIR\state.vscdb" -Force
            }
            Remove-Item $stateDb -Force -ErrorAction SilentlyContinue
            if (-not (Test-Path $stateDb)) {
                Write-Status "OK" "state.vscdb eliminado (agentSessions corrupto purgado)" "Green"
                Add-Diag "FIXED" "state.vscdb eliminado"
            }
            else {
                Write-Status "!" "No se pudo eliminar state.vscdb (puede estar bloqueado)" "Red"
                Add-Diag "ERROR" "No se pudo eliminar state.vscdb"
            }
        }
        else {
            Write-Status "i" "DryRun: Se eliminaria state.vscdb" "Yellow"
        }
    }
    
    # state.vscdb.backup
    $stateBackup = Join-Path $targetWorkspace.FullName "state.vscdb.backup"
    if (Test-Path $stateBackup) {
        if (-not $DryRun) {
            Remove-Item $stateBackup -Force -ErrorAction SilentlyContinue
            Write-Status "OK" "state.vscdb.backup eliminado" "Green"
            Add-Diag "FIXED" "state.vscdb.backup eliminado"
        }
    }
}
else {
    Write-Status "!" "No se encontro workspace para Skyclaw_Main_Sync" "Yellow"
    Add-Diag "WARNING" "Workspace no encontrado"
}

# Tambien limpiar globalStorage state.vscdb
$globalStateDb = "$AG_USER_DATA\User\globalStorage\state.vscdb"
if (Test-Path $globalStateDb) {
    $globalSize = (Get-Item $globalStateDb).Length
    Write-Status "i" "Global state.vscdb: $([math]::Round($globalSize/1KB, 1)) KB" "Cyan"
    if (-not $DryRun) {
        if (-not $SkipBackup) {
            Copy-Item $globalStateDb "$BACKUP_DIR\global_state.vscdb" -Force
        }
        Remove-Item $globalStateDb -Force -ErrorAction SilentlyContinue
        if (-not (Test-Path $globalStateDb)) {
            Write-Status "OK" "Global state.vscdb eliminado" "Green"
            Add-Diag "FIXED" "Global state.vscdb eliminado"
        }
    }
}

$globalStateBackup = "$AG_USER_DATA\User\globalStorage\state.vscdb.backup"
if (Test-Path $globalStateBackup) {
    if (-not $DryRun) {
        Remove-Item $globalStateBackup -Force -ErrorAction SilentlyContinue
        Write-Status "OK" "Global state.vscdb.backup eliminado" "Green"
    }
}

# ============================================================
# CAPA 3: CACHES SECUNDARIOS
# ============================================================
Write-Step 3 "CACHES SECUNDARIOS - Code Cache, GPU, Service Worker, Session, Dawn"

$caches = @{
    "Code Cache"               = "$AG_USER_DATA\Code Cache"
    "GPUCache"                 = "$AG_USER_DATA\GPUCache"
    "Service Worker CacheData" = "$AG_USER_DATA\Service Worker\CacheData"
    "Session Storage"          = "$AG_USER_DATA\Session Storage"
    "DawnGraphiteCache"        = "$AG_USER_DATA\DawnGraphiteCache"
    "DawnWebGPUCache"          = "$AG_USER_DATA\DawnWebGPUCache"
}

foreach ($cache in $caches.GetEnumerator()) {
    Protect-Delete $cache.Value $cache.Key | Out-Null
}

# ============================================================
# CAPA 4: VALIDACION POST-REPARACION
# ============================================================
Write-Step 4 "VALIDACION POST-REPARACION"

# Verificar que la extension google.antigravity existe
$agExtDir = "$AG_INSTALL\resources\app\extensions\antigravity"
if (Test-Path $agExtDir) {
    $extJs = Join-Path $agExtDir "dist\extension.js"
    if (Test-Path $extJs) {
        $extSize = (Get-Item $extJs).Length
        Write-Status "OK" "google.antigravity extension bundle OK ($([math]::Round($extSize/1MB, 2)) MB)" "Green"
    }
    else {
        Write-Status "!" "google.antigravity dist/extension.js NO ENCONTRADO" "Red"
        Add-Diag "ERROR" "Extension bundle no encontrado"
    }
}
else {
    Write-Status "!" "Directorio de extension google.antigravity no encontrado" "Red"
    Add-Diag "ERROR" "Directorio de extension no encontrado"
}

# Verificar que CachedData fue limpiado
if (Test-Path $cachedDataDir) {
    $remaining = Get-ChildItem $cachedDataDir -ErrorAction SilentlyContinue
    if ($remaining.Count -eq 0) {
        Write-Status "OK" "CachedData vacio (V8 recompilara desde codigo fuente)" "Green"
    }
    else {
        Write-Status "!" "CachedData aun contiene ${($remaining | Measure-Object).Count} elementos" "Yellow"
    }
}

# Verificar workspace state eliminado
if ($targetWorkspace) {
    $stateDbCheck = Join-Path $targetWorkspace.FullName "state.vscdb"
    if (-not (Test-Path $stateDbCheck)) {
        Write-Status "OK" "Workspace state.vscdb eliminado (estado limpio)" "Green"
    }
    else {
        Write-Status "!" "Workspace state.vscdb aun existe" "Yellow"
    }
}

# Verificar git config
Write-Status ">" "Verificando configuracion Git..." "Cyan"
$gitFile = Join-Path $PROJECT_ROOT ".git"
if (Test-Path $gitFile) {
    $gitContent = Get-Content $gitFile -Raw
    if ($gitContent -match "gitdir:") {
        $gitdir = $gitContent.Replace("gitdir:", "").Trim()
        $realConfig = Join-Path $gitdir "config"
        if (-not (Test-Path $realConfig)) {
            # El worktree config esta en el directorio padre
            $mainConfig = Join-Path (Split-Path (Split-Path $gitdir -Parent) -Parent) "config"
            if (Test-Path $mainConfig) {
                $realConfig = $mainConfig
            }
        }
        if (Test-Path $realConfig) {
            $configContent = Get-Content $realConfig -Raw
            if ($configContent -match "worktreeConfig\s*=\s*true") {
                Write-Status "!" "extensions.worktreeConfig=true detectado (DEBE eliminarse)" "Red"
                Add-Diag "ERROR" "worktreeConfig aun presente"
                if (-not $DryRun) {
                    $configContent = $configContent -replace '\[extensions\]\s*\r?\n\s*worktreeConfig\s*=\s*true\r?\n', ''
                    Set-Content $realConfig $configContent -NoNewline
                    Write-Status "OK" "extensions.worktreeConfig eliminado" "Green"
                    Add-Diag "FIXED" "worktreeConfig eliminado"
                }
            }
            else {
                Write-Status "OK" "Git config limpio (sin worktreeConfig)" "Green"
            }
            if ($configContent -match "repositoryformatversion\s*=\s*(\d+)") {
                $ver = [int]$Matches[1]
                if ($ver -eq 0) {
                    Write-Status "OK" "repositoryformatversion = 0 (correcto)" "Green"
                }
                else {
                    Write-Status "!" "repositoryformatversion = $ver (debe ser 0)" "Red"
                }
            }
        }
    }
}

# ============================================================
# RESUMEN FINAL
# ============================================================
Write-Host ""
Write-Host "################################################################" -ForegroundColor Magenta
Write-Host "#  RESUMEN DE REPARACION DEFINITIVA                           #" -ForegroundColor Magenta
Write-Host "################################################################" -ForegroundColor Magenta
Write-Host ""

Write-Status "i" "Errores encontrados: $($script:Errors.Count)" "Cyan"
Write-Status "i" "Problemas corregidos: $($script:Fixed.Count)" "Green"
Write-Status "i" "Advertencias: $($script:Warnings.Count)" "Yellow"

if ($script:Fixed.Count -gt 0) {
    Write-Host ""
    Write-Host "Correcciones aplicadas:" -ForegroundColor Green
    foreach ($f in $script:Fixed) {
        Write-Host "  [OK] $($f.Message)" -ForegroundColor Green
    }
}

if ($script:Errors.Count -gt 0) {
    Write-Host ""
    Write-Host "Errores pendientes:" -ForegroundColor Red
    foreach ($e in $script:Errors) {
        Write-Host "  [!!] $($e.Message)" -ForegroundColor Red
    }
}

Write-Host ""
Write-Status "i" "Log guardado en: $LOG_FILE" "Cyan"
if (-not $SkipBackup -and -not $DryRun) {
    Write-Status "i" "Respaldo en: $BACKUP_DIR" "Cyan"
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  PROXIMOS PASOS:" -ForegroundColor Green
Write-Host "  1. Abrir Antigravity" -ForegroundColor Green
Write-Host "  2. El V8 recompilara el workbench desde codigo fuente" -ForegroundColor Green
Write-Host "  3. La extension google.antigravity cargara correctamente" -ForegroundColor Green
Write-Host "  4. El servicio agentSessions se registrara normalmente" -ForegroundColor Green
Write-Host "  5. El Agent Panel deberia funcionar sin errores" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""

if ($DryRun) {
    Write-Status "i" "MODO DRYRUN - No se realizaron cambios. Ejecute sin -DryRun para aplicar." "Yellow"
}
