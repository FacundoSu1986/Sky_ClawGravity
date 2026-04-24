import os
import sys
import platform
import subprocess
import json
from pathlib import Path


def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode().strip()
    except:
        return "ERROR: Comando fallido"


def check_ag_health():
    print("=== ANTIGRAVITY AGENT PANEL DIAGNOSTIC (2026) ===")

    # 1. Información del Sistema y Venv
    print(f"\n[1] OS: {platform.system()} {platform.release()}")
    print(f"[1] Python Executable: {sys.executable}")

    # 2. Check de Librerías Críticas para el Chat (NiceGUI es el motor)
    print("\n[2] Verificando dependencias del Chat UI...")
    libs = ["nicegui", "keyring", "mypy", "pyyaml", "fastapi"]
    for lib in libs:
        ver = run_cmd(f"pip show {lib} | findstr Version")
        print(f"  - {lib}: {ver if ver else 'MISSING'}")

    # 3. Integridad de la Carpeta .antigravity
    print("\n[3] Inspeccionando Metadatos de Antigravity...")
    ag_path = Path(".antigravity")
    if ag_path.exists():
        files = [f.name for f in ag_path.glob("*")]
        print(f"  - Contenido detectado: {files}")
        if "session.lock" in files:
            print("  - [!] ADVERTENCIA: 'session.lock' detectado. Esto bloquea el Agent Panel.")
    else:
        print("  - [!] ERROR: Carpeta .antigravity NO ENCONTRADA.")

    # 4. Procesos del Orquestador
    print("\n[4] Buscando procesos de IA colgados...")
    # Buscamos procesos que suelen bloquear el puerto del socket del chat
    processes = run_cmd('tasklist | findstr /I "antigravity gemini python"')
    print(processes if processes else "  - No se detectaron procesos activos.")

    # 5. Mypy Ghosting Check (Basado en tu log anterior)
    print("\n[5] Check de Sockets Mypy...")
    mypy_socket = Path(os.path.expanduser("~")) / "AppData/Roaming/Antigravity/User/workspaceStorage"
    print(f"  - Storage Path existe: {mypy_socket.exists()}")


if __name__ == "__main__":
    check_ag_health()
