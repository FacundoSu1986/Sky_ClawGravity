# =============================================================================
# SkyClaw - Bloqueo de acceso al directorio .git para agentes de IA
# =============================================================================
# Este script restringe los permisos de lectura del directorio .git para
# procesos no autorizados, evitando que los agentes de IA (Antigravity, Roo,
# Claude, etc.) escaneen e indexen los 937+ objetos binarios contenidos.
#
# USO:
#   .\local_scripts\scripts\lock_git_dir.ps1 [-Mode {Lock|Unlock|Status}]
#
# MODO "Lock"   (predeterminado): Deniega acceso listado/directorio al grupo
#   "Everyone" (SID S-1-1-0). Git sigue funcionando para el usuario actual.
# MODO "Unlock" : Restaura permisos heredados (desbloqueo de emergencia).
# MODO "Status" : Muestra los permisos actuales de .git
#
# REQUISITOS: Ejecutar como Administrador
# =============================================================================

param(
    [ValidateSet("Lock", "Unlock", "Status")]
    [string]$Mode = "Lock"
)

$ErrorActionPreference = "Stop"
$gitDir = Join-Path $PSScriptRoot "..\..\.git" -Resolve

function Test-Admin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-GitAcl {
    return (Get-Acl -Path $gitDir)
}

function Show-Status {
    Write-Host "`n=== Permisos actuales de .git ===" -ForegroundColor Cyan
    $acl = Get-GitAcl
    $acl.Access | ForEach-Object {
        Write-Host ("  {0,-25} {1,-20} {2,-15} {3}" -f `
            $_.IdentityReference, `
            $_.FileSystemRights, `
            $_.AccessControlType, `
            $_.InheritanceFlags)
    }
    Write-Host ""
}

switch ($Mode) {
    "Status" {
        Show-Status
        exit 0
    }

    "Lock" {
        if (-not (Test-Admin)) {
            Write-Host "[ERROR] Este script requiere privilegios de Administrador." -ForegroundColor Red
            Write-Host "        Ejecutar: Start-Process PowerShell -Verb RunAs -ArgumentList '-File `"$PSCommandPath`" -Mode Lock'" -ForegroundColor Yellow
            exit 1
        }

        Write-Host "`n[BLOQUEO] Restringiendo acceso a: $gitDir" -ForegroundColor Yellow

        # 1. Deshabilitar herencia y copiar reglas existentes
        $acl = Get-GitAcl
        $acl.SetAccessRuleProtection($true, $true)
        Set-Acl -Path $gitDir -AclObject $acl

        # 2. Agregar regla DENY para "Everyone" en listado de contenido
        $everyone = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "Everyone",
            "ReadAndExecute, Synchronize",
            "ContainerInherit, ObjectInherit",
            "None",
            "Deny"
        )
        $acl = Get-GitAcl
        $acl.AddAccessRule($everyone)
        Set-Acl -Path $gitDir -AclObject $acl

        # 3. Asegurar que el usuario actual mantiene acceso completo
        $currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $allowRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $currentUser,
            "FullControl",
            "ContainerInherit, ObjectInherit",
            "None",
            "Allow"
        )
        $acl = Get-GitAcl
        $acl.AddAccessRule($allowRule)
        Set-Acl -Path $gitDir -AclObject $acl

        # 4. Asegurar que SYSTEM mantiene acceso
        $systemRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            "NT AUTHORITY\SYSTEM",
            "FullControl",
            "ContainerInherit, ObjectInherit",
            "None",
            "Allow"
        )
        $acl = Get-GitAcl
        $acl.AddAccessRule($systemRule)
        Set-Acl -Path $gitDir -AclObject $acl

        Write-Host "[OK] Permisos aplicados correctamente." -ForegroundColor Green
        Write-Host "     - DENY: Everyone (ReadAndExecute)" -ForegroundColor Gray
        Write-Host "     - ALLOW: $currentUser (FullControl)" -ForegroundColor Gray
        Write-Host "     - ALLOW: NT AUTHORITY\SYSTEM (FullControl)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "[INFO] Git seguira funcionando para tu usuario." -ForegroundColor Cyan
        Write-Host "[INFO] Los agentes de IA no podran leer .git" -ForegroundColor Cyan

        Show-Status
    }

    "Unlock" {
        if (-not (Test-Admin)) {
            Write-Host "[ERROR] Este script requiere privilegios de Administrador." -ForegroundColor Red
            exit 1
        }

        Write-Host "`n[DESBLOQUEO] Restaurando permisos heredados en: $gitDir" -ForegroundColor Yellow

        $acl = Get-GitAcl
        # Restaurar herencia
        $acl.SetAccessRuleProtection($false, $true)

        # Eliminar reglas DENY de Everyone
        $rules = $acl.Access | Where-Object {
            $_.IdentityReference -match "Everyone" -and $_.AccessControlType -eq "Deny"
        }
        foreach ($rule in $rules) {
            $acl.RemoveAccessRule($rule) | Out-Null
        }

        Set-Acl -Path $gitDir -AclObject $acl

        Write-Host "[OK] Permisos restaurados. .git es accesible nuevamente." -ForegroundColor Green
        Show-Status
    }
}
