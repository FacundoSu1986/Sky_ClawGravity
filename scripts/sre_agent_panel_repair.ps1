<#
.SYNOPSIS
    SRE Agent Panel Repair - Diagnostico y reparacion IPC Antigravity
.DESCRIPTION
    Diagnostica y repara la comunicacion entre VS Code Host (Antigravity)
    y el Language Server / Agent Server de Gemini Code Assist.
.NOTES
    Ejecutar: powershell -ExecutionPolicy Bypass -File .\scripts\sre_agent_panel_repair.ps1
#>

param(
    [switch]$DryRun = $false,
    [switch]$AutoFix = $false,
    [switch]$SkipGit = $false,
    [switch]$SkipProcesses = $false
)

$ErrorActionPreference = "Continue"

# ============================================================
# CONSTANTES
# ============================================================
$AG_USER_DATA = "$env:APPDATA\Antigravity"
$AG_EXTENSIONS = "$env:USERPROFILE\.antigravity\extensions"
$PROJECT_ROOT = $PSScriptRoot | Split-Path -Parent
$TIMESTAMP = Get-Date -Format "yyyyMMdd_HHmmss"
$LOG_FILE = "$PROJECT_ROOT\sre_repair_log_$TIMESTAMP.txt"

$script:Errors = @()
$script:Warnings = @()
$script:Fixed = @()

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
    Write-Host "=== PASO ${Num}: ${Title} ===" -ForegroundColor Cyan
    Add-Content -Path $LOG_FILE -Value "`n=== PASO ${Num}: ${Title} ===" -ErrorAction SilentlyContinue
}

function Add-Diag([string]$Type, [string]$Message, [string]$File = "") {
    $entry = @{ Type = $Type; Message = $Message; File = $File; Timestamp = Get-Date -Format "o" }
    switch ($Type) {
        "ERROR" { $script:Errors += $entry }
        "WARNING" { $script:Warnings += $entry }
        "FIXED" { $script:Fixed += $entry }
    }
}

# ============================================================
# INICIO
# ============================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "  SRE AGENT PANEL REPAIR UTILITY v2.0" -ForegroundColor Yellow
Write-Host "  Antigravity IPC Diagnostics & Repair" -ForegroundColor Yellow
Write-Host "  Timestamp: $TIMESTAMP" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

"=== SRE Agent Panel Repair Log - $TIMESTAMP ===" | Out-File -FilePath $LOG_FILE -Encoding UTF8

# ============================================================
# PASO 1: INSPECCION DE REGISTROS
# ============================================================
Write-Step 1 "INSPECCION DE REGISTROS DEL SISTEMA"

$logDir = "$AG_USER_DATA\logs"
if (-not (Test-Path $logDir)) {
    Write-Status "!" "Directorio de logs no encontrado: $logDir" "Red"
    Add-Diag "ERROR" "Directorio de logs no encontrado" $logDir
}
else {
    $latestSession = Get-ChildItem $logDir -Directory | Sort-Object Name -Descending | Select-Object -First 1
    if ($latestSession) {
        Write-Status "i" "Sesion de logs mas reciente: $($latestSession.Name)" "Cyan"

        # Analizar exthost.log
        $exthostLog = Join-Path $latestSession.FullName "window1\exthost\exthost.log"
        if (Test-Path $exthostLog) {
            Write-Status ">" "Analizando exthost.log..." "Cyan"
            $patterns = @("ConnectionRefused", "ECONNREFUSED", "ECONNRESET", "EPIPE",
                "timeout", "Timeout", "Token Expired", "crash", "fatal",
                "Exception", "No bundle location", "ENOENT")
            foreach ($p in $patterns) {
                $found = Select-String -Path $exthostLog -Pattern $p -ErrorAction SilentlyContinue
                if ($found) {
                    foreach ($m in $found) {
                        $msg = "[$p] Line $($m.LineNumber): $($m.Line.Substring(0, [Math]::Min(200, $m.Line.Length)))"
                        Write-Status "!" "  $msg" "Yellow"
                        Add-Diag "WARNING" $msg $exthostLog
                    }
                }
            }
        }

        # Analizar Gemini Agent log
        $outputDirs = Get-ChildItem (Join-Path $latestSession.FullName "window1\exthost") -Directory -Filter "output_logging_*" -ErrorAction SilentlyContinue
        foreach ($od in $outputDirs) {
            $agentLog = Get-ChildItem $od.FullName -Filter "*Gemini Code Assist Agent*" -ErrorAction SilentlyContinue
            if ($agentLog) {
                foreach ($al in $agentLog) {
                    Write-Status ">" "Analizando $($al.Name)..." "Cyan"
                    $errs = Select-String -Path $al.FullName -Pattern "\[ERROR\]", "Exception", "ENOENT", "YAMLException" -ErrorAction SilentlyContinue
                    if ($errs) {
                        foreach ($e in $errs) {
                            $msg = "Agent Error L$($e.LineNumber): $($e.Line.Substring(0, [Math]::Min(200, $e.Line.Length)))"
                            Write-Status "!" "  $msg" "Red"
                            Add-Diag "ERROR" $msg $al.FullName
                        }
                    }
                }
            }
        }

        # Crash logs
        $crashLog = Get-ChildItem $latestSession.FullName -Filter "Antigravity Crash Logs.log" -Recurse -ErrorAction SilentlyContinue
        if ($crashLog) {
            foreach ($cl in $crashLog) {
                $content = Get-Content $cl.FullName -ErrorAction SilentlyContinue
                if ($content -and $content.Count -gt 0) {
                    Write-Status "!" "CRASH LOGS en $($cl.FullName)" "Red"
                    Add-Diag "ERROR" "Crash logs detectados" $cl.FullName
                }
                else {
                    Write-Status "OK" "Crash logs vacios (sin crashes)" "Green"
                }
            }
        }
    }
}

# ============================================================
# PASO 2: REPARACION DE GIT CONFIG
# ============================================================
Write-Step 2 "REPARACION DE GIT CONFIG"

if (-not $SkipGit) {
    $gitConfig = Join-Path $PROJECT_ROOT ".git\config"
    if (Test-Path $gitConfig) {
        $content = Get-Content $gitConfig -Raw
        $needsFix = $false

        if ($content -match 'repositoryformatversion\s*=\s*(\d+)') {
            $ver = [int]$Matches[1]
            if ($ver -gt 0) {
                Write-Status "!" "repositoryformatversion = $ver (debe ser 0)" "Red"
                Add-Diag "ERROR" "repositoryformatversion = $ver" $gitConfig
                $needsFix = $true
            }
            else {
                Write-Status "OK" "repositoryformatversion = 0 (correcto)" "Green"
            }
        }

        if ($content -match '\[extensions\][\s\S]*?worktreeConfig\s*=\s*true') {
            Write-Status "!" "extensions.worktreeConfig = true (causa fallos en Antigravity)" "Red"
            Add-Diag "ERROR" "extensions.worktreeConfig = true" $gitConfig
            $needsFix = $true
        }
        else {
            Write-Status "OK" "Sin extensions.worktreeConfig (correcto)" "Green"
        }

        if ($needsFix -and -not $DryRun) {
            Copy-Item $gitConfig "$gitConfig.sre_backup_$TIMESTAMP" -Force
            $content = $content -replace 'repositoryformatversion\s*=\s*\d+', 'repositoryformatversion = 0'
            # Regex ampliado: captura la seccion [extensions] completa tanto con tabs como
            # con espacios (formato comun en git configs generados por distintas herramientas).
            $content = $content -replace '(?ms)^\[extensions\]\s*\r?\n.*?(?=^\[|\z)', ''
            $content = $content.TrimEnd() + "`n"
            Set-Content $gitConfig $content -NoNewline
            Write-Status "OK" ".git/config corregido" "Green"
            Add-Diag "FIXED" "Git config corregido" $gitConfig
        }
        elseif ($needsFix -and $DryRun) {
            Write-Status "i" "DryRun: Se corregiria .git/config" "Yellow"
        }
    }
    else {
        Write-Status "!" "No se encontro .git/config" "Yellow"
    }
}

# ============================================================
# PASO 3: LIMPIEZA DE PROCESOS HUERFANOS
# ============================================================
Write-Step 3 "LIMPIEZA DE PROCESOS HUERFANOS"

if (-not $SkipProcesses) {
    $agentPorts = @(51278, 51177, 51178, 51169, 17896)
    $orphaned = @{}

    foreach ($port in $agentPorts) {
        $conns = netstat -ano | Select-String ":$port\s" | Select-String "LISTENING"
        foreach ($c in $conns) {
            $parts = $c.Line -split '\s+'
            $procId = [int]$parts[-1]
            if ($procId -gt 0 -and -not $orphaned.ContainsKey($procId)) {
                $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($proc) {
                    $mem = [Math]::Round($proc.WorkingSet64 / 1MB, 1)
                    $status = if ($proc.Responding) { "ACTIVO" } else { "NO RESPONDE" }
                    Write-Status "~" "Puerto $port -> PID $procId ($($proc.ProcessName), ${mem}MB, $status)" "Yellow"
                    if (-not $proc.Responding) {
                        $orphaned[$procId] = @{ Port = $port; Reason = "No responde" }
                        Add-Diag "ERROR" "Proceso huerfano PID $procId en puerto $port" ""
                    }
                }
            }
        }
    }

    # Buscar node huerfanos vinculados a Gemini
    $nodeProcs = Get-CimInstance Win32_Process -Filter "name='node.exe'" -ErrorAction SilentlyContinue
    foreach ($np in $nodeProcs) {
        if ($np.CommandLine -match "geminicodeassist|antigravity|cloudcode") {
            $p = Get-Process -Id $np.ProcessId -ErrorAction SilentlyContinue
            if ($p -and -not $p.Responding) {
                Write-Status "!" "Node huerfano PID $($np.ProcessId)" "Red"
                $orphaned[$np.ProcessId] = @{ Port = 0; Reason = "Node huerfano" }
                Add-Diag "ERROR" "Node.exe huerfano PID $($np.ProcessId)" ""
            }
        }
    }

    if ($orphaned.Count -gt 0) {
        Write-Status "!" "$($orphaned.Count) proceso(s) huerfano(s)" "Red"
        if (-not $DryRun) {
            if ($AutoFix -or ((Read-Host "Terminar procesos huerfanos? (s/N)") -eq 's')) {
                foreach ($procId in $orphaned.Keys) {
                    try {
                        Stop-Process -Id $procId -Force
                        Write-Status "OK" "Proceso $procId terminado" "Green"
                        Add-Diag "FIXED" "Proceso huerfano $procId terminado" ""
                    }
                    catch {
                        Write-Status "!" "Error terminando PID $procId : $_" "Red"
                    }
                }
            }
        }
    }
    else {
        Write-Status "OK" "Sin procesos huerfanos" "Green"
    }

    # TIME_WAIT
    $tw = (netstat -ano | Select-String "TIME_WAIT" | Measure-Object).Count
    if ($tw -gt 20) {
        Write-Status "!" "$tw conexiones TIME_WAIT (saturacion)" "Yellow"
        Add-Diag "WARNING" "$tw conexiones TIME_WAIT" ""
    }
    else {
        Write-Status "OK" "$tw TIME_WAIT (normal)" "Green"
    }
}

# ============================================================
# PASO 4: CONFLICTOS DE EXTENSIONES
# ============================================================
Write-Step 4 "VERIFICACION DE CONFLICTOS DE EXTENSIONES"

$conflicts = @(
    @{ Id = "GitHub.copilot"; Name = "GitHub Copilot"; Reason = "Intercepta solicitudes LSP de Gemini" },
    @{ Id = "saoudrizwan.claude-dev"; Name = "Cline (Claude Dev)"; Reason = "Compite por proveedor de IA" },
    @{ Id = "Anthropic.claude-code"; Name = "Claude Code"; Reason = "Interfiere con proveedor Gemini" }
)

$installed = Get-ChildItem $AG_EXTENSIONS -Directory -ErrorAction SilentlyContinue
$detected = @()

foreach ($ext in $conflicts) {
    $found = $installed | Where-Object { $_.Name -like "$($ext.Id)*" }
    if ($found) {
        Write-Status "!" "Conflictiva: $($ext.Name) ($($found.Name))" "Red"
        Write-Status "  " "  Razon: $($ext.Reason)" "Yellow"
        $detected += $ext
        Add-Diag "WARNING" "Extension conflictiva: $($ext.Name)" $found.FullName
    }
}

if ($detected.Count -eq 0) {
    Write-Status "OK" "Sin extensiones conflictivas" "Green"
}
else {
    Write-Host ""
    Write-Status "!" "DESACTIVAR TEMPORALMENTE:" "Yellow"
    foreach ($d in $detected) {
        Write-Host "    - $($d.Name)" -ForegroundColor Yellow
    }
    Write-Host "    Via: Ctrl+Shift+P -> Extensions: Disable" -ForegroundColor Gray
}

# Verificar Gemini extension
$geminiExt = $installed | Where-Object { $_.Name -like "google.geminicodeassist*" }
if ($geminiExt) {
    Write-Status "OK" "Gemini Code Assist: $($geminiExt.Name)" "Green"
}
else {
    Write-Status "!" "Gemini Code Assist NO encontrado" "Red"
    Add-Diag "ERROR" "Extension Gemini no encontrada" $AG_EXTENSIONS
}

# ============================================================
# PASO 5: RECONFIGURACION DE ESTADO
# ============================================================
Write-Step 5 "RECONFIGURACION DE ESTADO DE SESION"

$statePaths = @(
    "$PROJECT_ROOT\.antigravity\state.json",
    "$AG_USER_DATA\User\globalStorage\google.geminicodeassist\state.json",
    "$AG_USER_DATA\User\globalStorage\google.antigravity\state.json"
)

foreach ($sp in $statePaths) {
    if (Test-Path $sp) {
        Write-Status "!" "Estado encontrado: $sp" "Yellow"
        try {
            $json = Get-Content $sp -Raw
            $null = $json | ConvertFrom-Json
            # Nota: 'null' es un valor JSON valido; solo 'undefined' y 'NaN' indican
            # valores de JavaScript serializados incorrectamente como strings literales.
            if ($json -match "\bundefined\b|\bNaN\b") {
                Write-Status "!" "  Puntero corrupto en $sp" "Red"
                Add-Diag "ERROR" "Puntero corrupto" $sp
                if (-not $DryRun) {
                    Copy-Item $sp "$sp.corrupt_backup_$TIMESTAMP" -Force
                }
            }
            else {
                Write-Status "OK" "  Estado valido" "Green"
            }
        }
        catch {
            Write-Status "!" "  JSON invalido: $_" "Red"
            Add-Diag "ERROR" "JSON invalido en estado" $sp
        }
    }
}

# Lock files
$locks = Get-ChildItem "$AG_USER_DATA\User\globalStorage\google.geminicodeassist" -Filter "*.lock" -Recurse -ErrorAction SilentlyContinue
if ($locks) {
    Write-Status "!" "$($locks.Count) lock file(s) encontrado(s)" "Yellow"
    if (-not $DryRun -and $AutoFix) {
        foreach ($lf in $locks) {
            Remove-Item $lf.FullName -Force -ErrorAction SilentlyContinue
            Write-Status "OK" "Lock eliminado: $($lf.Name)" "Green"
            Add-Diag "FIXED" "Lock eliminado" $lf.FullName
        }
    }
}

# ============================================================
# PASO 6: CORRECCION DE IMPORTACIONES GEMINI.md
# ============================================================
Write-Step 6 "CORRECCION DE IMPORTACIONES GEMINI.md"

$geminiMd = Join-Path $PROJECT_ROOT "GEMINI.md"
if (Test-Path $geminiMd) {
    $content = Get-Content $geminiMd -Raw
    $importMatches = [regex]::Matches($content, '@(\./[^\s\r\n]+)')
    $broken = @()

    foreach ($im in $importMatches) {
        $path = $im.Groups[1].Value
        $full = Join-Path $PROJECT_ROOT $path
        if (-not (Test-Path $full)) {
            Write-Status "!" "Importacion rota: @$path" "Red"
            Add-Diag "ERROR" "Importacion rota: @$path" $geminiMd
            $broken += $im.Value
            $fileName = Split-Path $path -Leaf
            $candidates = Get-ChildItem $PROJECT_ROOT -Filter $fileName -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -notmatch "node_modules|\.git|wt-" } | Select-Object -First 3
            foreach ($c in $candidates) {
                $rel = $c.FullName.Substring($PROJECT_ROOT.Length + 1).Replace('\', '/')
                Write-Status "  " "  Candidato: $rel" "Cyan"
            }
        }
        else {
            Write-Status "OK" "Importacion valida: @$path" "Green"
        }
    }

    if ($broken.Count -eq 0) {
        Write-Status "OK" "Todas las importaciones validas" "Green"
    }
}

# ============================================================
# PASO 7: CORRECCION YAML FRONTMATTER
# ============================================================
Write-Step 7 "CORRECCION YAML FRONTMATTER EN SKILLS"

$skillDirs = @(
    Join-Path $PROJECT_ROOT ".agents\skills",
    Join-Path $PROJECT_ROOT ".antigravity\superpowers\skills"
)

foreach ($sdir in $skillDirs) {
    if (-not (Test-Path $sdir)) { continue }
    $skills = Get-ChildItem $sdir -Filter "SKILL.md" -Recurse -ErrorAction SilentlyContinue
    foreach ($sf in $skills) {
        $c = Get-Content $sf.FullName -Raw
        if ($c -match '^---\s*\r?\n') {
            $fm = [regex]::Match($c, '^---\s*\r?\n([\s\S]*?)\r?\n---')
            if ($fm.Success) {
                $yaml = $fm.Groups[1].Value
                if ($yaml -match 'description:\s*[^\s"].*:' -and $yaml -notmatch 'description:\s*"') {
                    Write-Status "!" "YAML invalido en $($sf.Name)" "Red"
                    Add-Diag "ERROR" "YAML frontmatter invalido" $sf.FullName
                    if (-not $DryRun) {
                        $fixed = $yaml -replace '(description:\s*)([^\s"].*)', '$1"$2"'
                        $fixed = $fixed -replace '(description:\s*".+)(?<!")\s*$', '$1"'
                        $newC = $c.Replace($yaml, $fixed)
                        Set-Content $sf.FullName $newC -NoNewline
                        Write-Status "OK" "YAML corregido en $($sf.Name)" "Green"
                        Add-Diag "FIXED" "YAML corregido" $sf.FullName
                    }
                }
                else {
                    Write-Status "OK" "YAML valido en $($sf.Name)" "Green"
                }
            }
        }
    }
}

# ============================================================
# PASO 8: VERIFICACION IPC
# ============================================================
Write-Step 8 "VERIFICACION DE COMUNICACION IPC"

# Language Server
$lsPorts = netstat -ano | Select-String "LISTENING" | Select-String "127\.0\.0\.1:(5117[0-9]|5116[0-9])"
if ($lsPorts) {
    Write-Status "OK" "Language Server escuchando:" "Green"
    foreach ($lp in $lsPorts) { Write-Status "  " "  $($lp.Line.Trim())" "DarkGray" }
}
else {
    Write-Status "!" "Language Server NO detectado" "Red"
    Add-Diag "ERROR" "Language Server no escuchando" ""
}

# Agent Server
$agentPort = netstat -ano | Select-String "LISTENING" | Select-String "51278"
if ($agentPort) {
    Write-Status "OK" "Agent Server en puerto 51278" "Green"
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:51278/.well-known/agent-card.json" -TimeoutSec 5 -ErrorAction Stop
        Write-Status "OK" "Agent Card accesible (HTTP $($r.StatusCode))" "Green"
    }
    catch {
        Write-Status "!" "Agent Card no accesible: $_" "Red"
        Add-Diag "ERROR" "Agent Card no accesible" ""
    }
}
else {
    Write-Status "!" "Agent Server NO detectado en 51278" "Red"
    Add-Diag "ERROR" "Agent Server no escuchando" ""
}

# Extension Host
$eh = Get-CimInstance Win32_Process -Filter "name='Antigravity.exe'" -ErrorAction SilentlyContinue |
Where-Object { $_.CommandLine -match "node\.mojom\.NodeService" }
if ($eh) {
    Write-Status "OK" "Extension Host activo (PID: $($eh.ProcessId))" "Green"
}
else {
    Write-Status "!" "Extension Host NO detectado" "Red"
    Add-Diag "ERROR" "Extension Host no detectado" ""
}

# ============================================================
# RESUMEN
# ============================================================
Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "  RESUMEN DE DIAGNOSTICO SRE" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "  Errores:      $($script:Errors.Count)" -ForegroundColor $(if ($script:Errors.Count -gt 0) { "Red" } else { "Green" })
Write-Host "  Advertencias: $($script:Warnings.Count)" -ForegroundColor $(if ($script:Warnings.Count -gt 0) { "Yellow" } else { "Green" })
Write-Host "  Corregidos:   $($script:Fixed.Count)" -ForegroundColor $(if ($script:Fixed.Count -gt 0) { "Cyan" } else { "Green" })

if ($script:Errors.Count -gt 0) {
    Write-Host ""
    Write-Host "  ERRORES:" -ForegroundColor Red
    foreach ($e in $script:Errors) { Write-Host "    - $($e.Message)" -ForegroundColor Red }
}
if ($script:Fixed.Count -gt 0) {
    Write-Host ""
    Write-Host "  CORRECCIONES:" -ForegroundColor Cyan
    foreach ($f in $script:Fixed) { Write-Host "    + $($f.Message)" -ForegroundColor Cyan }
}

Write-Host ""
Write-Host "  Log: $LOG_FILE" -ForegroundColor DarkGray

if ($script:Errors.Count -gt 0 -or $detected.Count -gt 0) {
    Write-Host ""
    Write-Host "  ACCIONES POST-REPARACION:" -ForegroundColor Yellow
    Write-Host "    1. Ctrl+Shift+P -> Developer: Reload Window" -ForegroundColor White
    Write-Host "    2. Si persiste: Developer: Restart Extension Host" -ForegroundColor White
    if ($detected.Count -gt 0) {
        Write-Host "    3. Desactivar extensiones conflictivas" -ForegroundColor White
    }
    Write-Host "    4. Ultimo recurso: Cerrar y reabrir Antigravity" -ForegroundColor White
}

$state = if ($script:Errors.Count -eq 0) { "SANO" } elseif ($script:Fixed.Count -gt 0) { "REPARADO (requiere reload)" } else { "REQUIERE INTERVENCION" }
$color = if ($script:Errors.Count -eq 0) { "Green" } elseif ($script:Fixed.Count -gt 0) { "Yellow" } else { "Red" }
Write-Host ""
Write-Host "  ESTADO: $state" -ForegroundColor $color
Write-Host "============================================================" -ForegroundColor $color
