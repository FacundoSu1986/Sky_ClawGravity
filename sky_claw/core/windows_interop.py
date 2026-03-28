import asyncio
import logging
from sky_claw.core.models import LootExecutionParams, WSLInteropError

logger = logging.getLogger("SkyClaw.Interop")

class ModdingToolsAgent:
    @staticmethod
    async def translate_path_wsl_to_win(wsl_path: str) -> str:
        r"""Usa wslpath para convertir rutas de Linux a formato Windows (C:\...)."""
        proc = await asyncio.create_subprocess_exec(
            "wslpath", "-w", wsl_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err_str = stderr.decode('utf-8', errors='replace').strip()
            raise WSLInteropError(f"Fallo en wslpath: {err_str}")
        return stdout.decode('utf-8', errors='replace').strip()

    async def run_loot(self, params: LootExecutionParams) -> dict:
        """Ejecuta LOOT.exe de forma asincrónica previniendo crash por decodificación."""
        loot_exe_wsl = "/mnt/c/Program Files/LOOT/loot.exe"
        game_path_win = "C:\\Steam\\steamapps\\common\\Skyrim Special Edition"
        
        logger.info(f"Ejecutando LOOT para el perfil: {params.profile_name}")
        
        args = [
            loot_exe_wsl,
            "--game", "SkyrimSE",
            "--game-path", game_path_win,
            "--sort"
        ]
        
        if params.update_masterlist:
            args.append("--update-masterlist")
            
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120.0)
        
        # Parche Estándar 2026: Prevención de crash por decodificación en WSL2 cruzando I/O de Windows
        out_str = stdout.decode('utf-8', errors='replace').strip()
        err_str = stderr.decode('utf-8', errors='replace').strip()
        
        if proc.returncode != 0:
            logger.error(f"RCA: LOOT falló con código {proc.returncode}. Stderr: {err_str}")
            return {"status": "error", "logs": err_str}
            
        return {"status": "success", "logs": out_str}
