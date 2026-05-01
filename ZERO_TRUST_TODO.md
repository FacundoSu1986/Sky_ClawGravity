# Zero-Trust Post-Purge TODO

## Completado ✅

- `sky_claw/__main__.py` — defaults purificados a argparse puro (Fase 2).
- `sky_claw/config.py` — `_load_from_env()` y gate `SKY_CLAW_ALLOW_ENV_OVERRIDES` eliminados (Fase 2).
- `sky_claw/antigravity/orchestrator/supervisor.py` — paths delegados a `PathResolutionService` (Fase 1).
- `sky_claw/local/tools/dyndolod_service.py` — paths delegados a `PathResolutionService` (Fase 1).
- `sky_claw/local/tools/synthesis_service.py` — paths delegados a `PathResolutionService` (Fase 1).
- `sky_claw/local/tools/xedit_service.py` — paths delegados a `PathResolutionService` (Fase 1).
- `sky_claw/local/auto_detect.py` — `LOCALAPPDATA` reemplazado por `Path.home()` helper (Fase 3).
- `sky_claw/antigravity/security/file_permissions.py` — `USERNAME` reemplazado por `getpass.getuser()` (Fase 3).
- `sky_claw/local/tools_installer.py` — verificado: sin `os.environ` (falso positivo, Fase 3).

## Excepción documentada (single point of contact)

- `sky_claw/antigravity/core/path_resolver.py` — sigue leyendo `os.environ` para paths de herramientas (`SKYRIM_PATH`, `MO2_PATH`, etc.). **Este es el único punto centralizado permitido** hasta que se migren a `config.toml` exclusivo. Ningún otro módulo debe leer estas variables directamente.

## Acción recomendada futura

1. Migrar `PathResolutionService` de `os.environ` a `config.toml` puro.
2. Consolidar secretos restantes en `CredentialVault.get_key(name)` con backend keyring.
