"""Core package for Sky-Claw daemon components."""

from .models import CircuitBreakerTripped, WSLInteropError
from .database import DatabaseAgent
from .schemas import (
    ModMetadata,
    ScrapingQuery,
    SecurityAuditRequest,
    SecurityAuditResponse,
    AgentToolRequest,
    AgentToolResponse,
    RouteClassification,
)
from .contracts import (
    validate_input,
    validate_output,
    validate_contract,
    get_contract_schema,
    get_schema_class,
    list_registered_schemas,
    verify_contract,
)
from .validators import (
    SSRFValidator,
    SSRFValidationResult,
    validate_url_ssrf,
    PathTraversalValidator,
    PathValidationResult,
    validate_path_traversal,
    validate_path_strict,
)

__all__ = [
    # Excepciones
    "CircuitBreakerTripped",
    "WSLInteropError",
    # Database
    "DatabaseAgent",
    # Schemas
    "ModMetadata",
    "ScrapingQuery",
    "SecurityAuditRequest",
    "SecurityAuditResponse",
    "AgentToolRequest",
    "AgentToolResponse",
    "RouteClassification",
    # Contracts
    "validate_input",
    "validate_output",
    "validate_contract",
    "get_contract_schema",
    "get_schema_class",
    "list_registered_schemas",
    "verify_contract",
    # Validators
    "SSRFValidator",
    "SSRFValidationResult",
    "validate_url_ssrf",
    "PathTraversalValidator",
    "PathValidationResult",
    "validate_path_traversal",
    "validate_path_strict",
]
