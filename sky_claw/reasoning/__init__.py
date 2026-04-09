# -*- coding: utf-8 -*-
"""
reasoning package - Motores de razonamiento avanzado para Sky_Claw.

Este paquete implementa algoritmos de razonamiento que extienden
las capacidades de los agentes más allá del Chain-of-Thought lineal.

Módulos:
- tot: Tree-of-Thought engine para exploración sistemática de caminos de razonamiento
- types: Definiciones de tipos, protocolos y estructuras de datos
- strategies: Implementaciones de estrategias de búsqueda
- engine: Motor principal y componentes auxiliares
"""

from .tot import (
    ThoughtNode,
    TreeOfThoughtEngine,
    ToTConfig,
    SearchStrategyType,
    EvaluationResult,
    create_tot_engine,
)

__all__ = [
    "ThoughtNode",
    "TreeOfThoughtEngine",
    "ToTConfig",
    "SearchStrategyType",
    "EvaluationResult",
    "create_tot_engine",
]
