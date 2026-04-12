# -*- coding: utf-8 -*-
"""
Tree of Thoughts (ToT) Reasoning Module - Facade

This module provides a unified API for Tree of Thoughts reasoning capabilities.
The implementation has been modularized into separate components:

- types.py: Core type definitions, protocols, and data structures
- strategies.py: Search strategy implementations (BFS, DFS, MCTS, etc.)
- engine.py: Main engine, cycle detection, pruning policies

For direct access to specific components, import from the submodules directly.

References:
- Yao et al. (2023) "Tree of Thoughts: Deliberate Problem Solving with Large Language Models"
- Long (2023) "Large Language Models Are Zero-Shot Reasoners"
"""

# Types and Protocols
from .types import (
    SearchStrategyType,
    EvaluationResult,
    PruningMethod,
    ToTConfig,
    ThoughtNode,
    ThoughtGenerator,
    ThoughtEvaluator,
    SolutionChecker,
    SearchStrategyProtocol,
)

# Search Strategies
from .strategies import (
    BaseSearchStrategy,
    BFSSearchStrategy,
    DFSSearchStrategy,
    BestFirstSearchStrategy,
    BeamSearchStrategy,
    MCTSSearchStrategy,
    create_search_strategy,
)

# Engine and Components
from .engine import (
    CycleDetector,
    PruningPolicy,
    TreeOfThoughtEngine,
    create_tot_engine,
    DefaultThoughtGenerator,
    DefaultThoughtEvaluator,
)

__all__ = [
    # Configuración
    "ToTConfig",
    "SearchStrategyType",
    "EvaluationResult",
    "PruningMethod",
    # Estructuras de datos
    "ThoughtNode",
    # Protocolos
    "ThoughtGenerator",
    "ThoughtEvaluator",
    "SolutionChecker",
    "SearchStrategyProtocol",
    # Estrategias de búsqueda
    "BaseSearchStrategy",
    "BFSSearchStrategy",
    "DFSSearchStrategy",
    "BestFirstSearchStrategy",
    "BeamSearchStrategy",
    "MCTSSearchStrategy",
    # Componentes auxiliares
    "CycleDetector",
    "PruningPolicy",
    # Motor principal
    "TreeOfThoughtEngine",
    # Factory
    "create_tot_engine",
    "create_search_strategy",
    # Implementaciones por defecto
    "DefaultThoughtGenerator",
    "DefaultThoughtEvaluator",
]
