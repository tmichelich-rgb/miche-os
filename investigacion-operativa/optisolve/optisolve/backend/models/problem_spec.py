"""
Problem Spec: Contrato formal entre AI Builder y Solver Layer.
Basado en la arquitectura de OptiSolve.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid


class ModuleType(str, Enum):
    LP = "LP"
    STOCK = "STOCK"
    QUEUE = "QUEUE"


class ObjectiveType(str, Enum):
    MAX = "MAX"
    MIN = "MIN"


class ConstraintSense(str, Enum):
    LEQ = "<="
    GEQ = ">="
    EQ = "="


class VariableType(str, Enum):
    CONTINUOUS = "continuous"
    INTEGER = "integer"
    BINARY = "binary"


class ReplenishmentType(str, Enum):
    INSTANTANEOUS = "instantaneous"
    GRADUAL = "gradual"


class QueueDiscipline(str, Enum):
    FIFO = "FIFO"
    LIFO = "LIFO"
    PRIO = "PRIO"
    SIRO = "SIRO"


# --- LP Sub-schemas ---
class LPConstraint(BaseModel):
    name: str = ""
    coeffs: Dict[str, float]
    sense: ConstraintSense = ConstraintSense.LEQ
    rhs: float


class VariableBound(BaseModel):
    lb: Optional[float] = 0
    ub: Optional[float] = None


class LPModelSpec(BaseModel):
    objective_type: ObjectiveType
    objective_coefficients: Dict[str, float]
    constraints: List[LPConstraint]
    variable_bounds: Optional[Dict[str, VariableBound]] = None
    variable_types: Optional[Dict[str, VariableType]] = None
    constraint_names: Optional[List[str]] = None


# --- Stock Sub-schemas ---
class DiscountBracket(BaseModel):
    qty_min: float
    price: float


class StockModelSpec(BaseModel):
    demand_D: float = Field(gt=0, description="Demanda anual")
    order_cost_k: float = Field(ge=0, description="Costo por pedido ($)")
    holding_cost_c1: float = Field(gt=0, description="Costo almac. ($/un/año)")
    acquisition_cost_b: float = Field(ge=0, description="Precio unitario ($)")
    shortage_cost_c2: Optional[float] = Field(None, description="Costo faltante ($/un/año)")
    lead_time_LT: float = Field(ge=0, description="Tiempo entrega (años)")
    safety_stock_Sp: float = Field(ge=0, default=0, description="Stock protección (un)")
    planning_horizon_T: float = Field(gt=0, default=1.0, description="Horizonte (años)")
    replenishment_type: ReplenishmentType = ReplenishmentType.INSTANTANEOUS
    production_rate_p: Optional[float] = Field(None, description="Tasa producción (un/año)")
    discount_schedule: Optional[List[DiscountBracket]] = None


# --- Queue Sub-schemas ---
class QueueModelSpec(BaseModel):
    arrival_rate_lambda: float = Field(gt=0, description="Tasa llegada (clientes/hora)")
    service_rate_mu: float = Field(gt=0, description="Tasa servicio por servidor (clientes/hora)")
    num_servers_M: int = Field(ge=1, default=1, description="Número de servidores")
    system_capacity_N: Optional[int] = Field(None, description="Capacidad sistema (null=infinita)")
    population_size: Optional[int] = Field(None, description="Tamaño población (null=infinita)")
    discipline: QueueDiscipline = QueueDiscipline.FIFO
    impatience_alpha: Optional[float] = None
    cost_per_wait_ce: Optional[float] = Field(None, description="Costo espera ($/cliente/hora)")
    cost_per_server_cs: Optional[float] = Field(None, description="Costo servidor ($/hora)")
    revenue_per_service_u: Optional[float] = Field(None, description="Ingreso por servicio ($)")


# --- Assumption ---
class Assumption(BaseModel):
    text: str
    justification: str
    source: Optional[str] = None  # "Miranda Cap. X" or "user_confirmed"


# --- RAG Citation ---
class RAGCitation(BaseModel):
    book: str
    chapter: int
    section: str
    page_range: str
    chunk_type: str
    relevance_score: float


# --- Full Problem Spec ---
class ProblemSpec(BaseModel):
    problem_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    module: ModuleType
    subtype: str
    version: str = "1.0.0"
    created_at: datetime = Field(default_factory=datetime.now)
    user_input: str = ""
    facts: Dict[str, Any] = {}
    assumptions: List[Assumption] = []
    model_spec: Dict[str, Any] = {}  # Union of LP/Stock/Queue specs
    rag_citations: List[RAGCitation] = []
    validation: Dict[str, Any] = {"passed": False, "errors": []}
    solution: Optional[Dict[str, Any]] = None
    sensitivity: Optional[Dict[str, Any]] = None
    decision: Optional[Dict[str, Any]] = None
    warnings: List[str] = []


# --- API Request/Response ---
class SolveRequest(BaseModel):
    """Simple solve request from frontend."""
    module: ModuleType
    subtype: Optional[str] = None
    params: Dict[str, Any]
    user_input: Optional[str] = ""


class ConversationMessage(BaseModel):
    role: str  # "user" | "system" | "assistant"
    content: str
    data: Optional[Dict[str, Any]] = None


class ConversationRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: List[ConversationMessage] = []
