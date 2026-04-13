"""Payloads inmutables y validados para eventos del CoreEventBus.

Todos los payloads heredan de ``pydantic.BaseModel`` con
``ConfigDict(frozen=True, strict=True)`` para garantizar serialización
y validación de esquemas al cruzar los límites del bus.

Parte del Sprint 1.5: Strangler Fig — desacoplamiento de ``supervisor.py``.
"""

from __future__ import annotations

import time

from pydantic import BaseModel, ConfigDict, Field


class ModlistChangedPayload(BaseModel):
    """Payload inmutable para el evento ``system.modlist.changed``.

    Publicado por :class:`WatcherDaemon` cuando detecta una modificación
    externa en el ``modlist.txt`` de MO2.

    Attributes:
        profile_name: Nombre del perfil MO2 donde se detectó el cambio.
        modlist_path: Ruta absoluta al ``modlist.txt`` monitoreado.
        previous_mtime: ``st_mtime`` anterior del archivo (epoch float).
        current_mtime: ``st_mtime`` actual del archivo (epoch float).
        detected_at: Timestamp de detección (epoch float, autogenerado).
    """

    model_config = ConfigDict(frozen=True, strict=True)

    profile_name: str
    modlist_path: str
    previous_mtime: float
    current_mtime: float
    detected_at: float = Field(default_factory=time.time)

    def to_log_dict(self) -> dict[str, str | float]:
        """Serialización compatible con el sistema de logging estructurado.

        Returns:
            Diccionario plano con todos los campos del payload.
        """
        return self.model_dump()
