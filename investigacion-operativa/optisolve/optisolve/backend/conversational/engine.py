"""
Motor conversacional guiado por teoría.
Cada pregunta está motivada por un requerimiento del modelo matemático.
"""
import re
from typing import Dict, List, Optional, Tuple, Any


# ─── MODULE DETECTION ──────────────────────────────────────
LP_KEYWORDS = [
    "producir", "fabricar", "mezcla", "asignar", "maximizar", "minimizar",
    "ganancia", "restricciones", "recursos", "horas disponibles", "maquinado",
    "programación lineal", "simplex", "variables de decisión", "función objetivo",
    "tratamiento", "mano de obra", "materia prima", "presupuesto",
]
STOCK_KEYWORDS = [
    "inventario", "stock", "pedir", "pedido", "almacén", "almacenar",
    "proveedor", "reposición", "lote", "eoq", "faltante", "demanda anual",
    "costo de pedido", "costo de almacenamiento", "punto de reorden",
    "cuánto pedir", "cada cuánto", "lead time",
]
QUEUE_KEYWORDS = [
    "cola", "fila", "espera", "cajero", "servidor", "ventanilla",
    "atención", "clientes por hora", "tasa de llegada", "tasa de servicio",
    "tiempo de espera", "cuántos cajeros", "cuántas cajas", "servicio",
    "banco", "hospital", "peaje", "call center", "supermercado",
]


def detect_module(text: str) -> Tuple[Optional[str], float]:
    """Detect which module (LP/STOCK/QUEUE) a user's text belongs to."""
    text_lower = text.lower()

    scores = {
        "LP": sum(1 for kw in LP_KEYWORDS if kw in text_lower),
        "STOCK": sum(1 for kw in STOCK_KEYWORDS if kw in text_lower),
        "QUEUE": sum(1 for kw in QUEUE_KEYWORDS if kw in text_lower),
    }

    best = max(scores, key=scores.get)
    total = sum(scores.values())
    confidence = scores[best] / total if total > 0 else 0

    if total == 0:
        return None, 0
    return best, confidence


def detect_subtype(module: str, text: str, params: Dict) -> str:
    """Detect specific model subtype within a module."""
    text_lower = text.lower()

    if module == "LP":
        if any(w in text_lower for w in ["entero", "entera", "binari"]):
            return "integer_lp"
        if any(w in text_lower for w in ["dual", "precio sombra"]):
            return "dual"
        return "simplex_standard"

    elif module == "STOCK":
        if any(w in text_lower for w in ["descuento", "rebaja", "bonificación"]):
            return "eoq_discount"
        if any(w in text_lower for w in ["agotamiento", "faltante", "rotura"]):
            return "eoq_shortage"
        if any(w in text_lower for w in ["gradual", "producción propia", "no instantáne"]):
            return "eoq_gradual"
        return "eoq_basic"

    elif module == "QUEUE":
        M = params.get("num_servers_M", 1)
        N = params.get("system_capacity_N")
        if M > 1 and N:
            return "mmm_n"
        elif M > 1:
            return "mmm"
        elif N:
            return "mm1_n"
        return "mm1"

    return "unknown"


# ─── PARAMETER EXTRACTION ──────────────────────────────────
def extract_numbers(text: str) -> List[float]:
    """Extract all numbers from text."""
    # Match integers and decimals, with optional thousand separators
    pattern = r'[\d]+[.,]?[\d]*'
    matches = re.findall(pattern, text)
    numbers = []
    for m in matches:
        try:
            numbers.append(float(m.replace(",", ".")))
        except:
            pass
    return numbers


def extract_lp_params(text: str) -> Dict:
    """Try to extract LP parameters from natural language."""
    # This is a simplified extractor. In production, the LLM does this.
    params = {
        "objective_type": "MAX",
        "objective_coefficients": {},
        "constraints": [],
        "variable_types": {},
    }

    text_lower = text.lower()
    if any(w in text_lower for w in ["minimizar", "costo mínimo", "menor costo"]):
        params["objective_type"] = "MIN"

    return params


def extract_stock_params(text: str) -> Dict:
    """Try to extract stock parameters."""
    params = {}
    text_lower = text.lower()

    # Common patterns
    patterns = {
        "demand_D": [
            r'(?:vendo|consumo|demanda|venta)\s*(?:de\s+)?(?:unas?\s+)?(\d+[\.,]?\d*)\s*(?:unidades?)?',
            r'(\d+[\.,]?\d*)\s*unidades?\s*(?:por\s+)?a[ñn]o',
        ],
        "order_cost_k": [
            r'(?:pedido|pedir).*?(?:gasto|cuesta|costo)\s*(?:como\s*)?\$?\s*(\d+[\.,]?\d*)',
            r'(?:gasto|cuesta)\s*(?:como\s*)?\$?\s*(\d+[\.,]?\d*).*?(?:flete|papeleo|pedido)',
        ],
        "holding_cost_c1": [
            r'almacenar.*?(?:cuesta|costo)\s*(?:m[aá]s\s+o\s+menos\s*)?\$?\s*(\d+[\.,]?\d*)',
            r'\$?\s*(\d+[\.,]?\d*)\s*(?:por\s+)?(?:a[ñn]o)?.*?(?:almac|stock|mantener)',
        ],
        "acquisition_cost_b": [
            r'(?:me\s+sale)\s*\$?\s*(\d+[\.,]?\d*)',
            r'(?:precio\s+(?:unitario|de\s+compra)).*?\$?\s*(\d+[\.,]?\d*)',
            r'(?:sale)\s*\$?\s*(\d+[\.,]?\d*)',
        ],
        "lead_time_days": [
            r'(?:tarda|demora|entrega).*?(\d+)\s*d[ií]as',
            r'(\d+)\s*d[ií]as?\s*(?:en\s+)?(?:entreg|llegar|demora)',
        ],
    }

    for param, pats in patterns.items():
        for pat in pats:
            match = re.search(pat, text_lower)
            if match:
                val = match.group(1).replace(",", ".")
                params[param] = float(val)
                break

    # Convert lead time from days to years
    if "lead_time_days" in params:
        params["lead_time_LT"] = params.pop("lead_time_days") / 365

    return params


def extract_queue_params(text: str) -> Dict:
    """Try to extract queue parameters."""
    params = {}
    text_lower = text.lower()

    patterns = {
        "arrival_rate_lambda": [
            r'(\d+[\.,]?\d*)\s*clientes?\s*por\s*hora',
            r'llegan?\s*(?:en\s+promedio\s+)?(\d+[\.,]?\d*)\s*(?:clientes?)?(?:\s*por\s*hora)?',
        ],
        "service_rate_mu": [
            r'atiende[n]?\s*(?:en\s+promedio\s+)?(\d+[\.,]?\d*)\s*clientes?\s*por\s*hora',
            r'(\d+[\.,]?\d*)\s*clientes?\s*por\s*hora.*?(?:atender|servicio)',
        ],
        "num_servers_M": [
            r'(\d+)\s*(?:cajeros?|servidores?|ventanillas?|cajas?)',
        ],
        "cost_per_wait_ce": [
            r'\$?\s*(\d+[\.,]?\d*)\s*(?:en\s+)?(?:satisfacci[oó]n|p[ée]rdida|por\s*minuto|espera)',
        ],
        "cost_per_server_cs": [
            r'(?:cajero|servidor).*?\$?\s*(\d+[\.,]?\d*)\s*/?\s*hora',
            r'\$?\s*(\d+[\.,]?\d*)\s*/?\s*hora.*?(?:cajero|servidor)',
        ],
    }

    for param, pats in patterns.items():
        for pat in pats:
            match = re.search(pat, text_lower)
            if match:
                val = match.group(1).replace(",", ".")
                if param == "num_servers_M":
                    params[param] = int(float(val))
                else:
                    params[param] = float(val)
                break

    return params


# ─── QUESTION GENERATION ───────────────────────────────────
LP_QUESTIONS = {
    "objective_type": {
        "question": "¿Querés maximizar ganancias o minimizar costos?",
        "why": "Necesito saber si la función objetivo busca el mayor beneficio o el menor costo.",
        "options": ["Maximizar (ganancias, producción, ingresos)", "Minimizar (costos, tiempo, desperdicio)"]
    },
    "products": {
        "question": "¿Cuáles son los productos o actividades entre los que tenés que decidir? ¿Y cuánta ganancia o costo genera cada uno?",
        "why": "Cada producto será una variable de decisión (xj) con su coeficiente en la función objetivo (cj).",
    },
    "constraints": {
        "question": "¿Qué recursos tenés limitados? Para cada recurso necesito: nombre, cuánto consume cada producto, y cuánto hay disponible.",
        "why": "Cada recurso limitado genera una restricción del tipo: a₁x₁ + a₂x₂ ≤ b",
    },
    "variable_types": {
        "question": "¿Los productos se pueden fabricar en fracciones (ej: 123.5 unidades) o solo en números enteros?",
        "why": "Si son enteros, se usa Programación Entera (Branch & Bound). Si son continuos, Simplex estándar.",
        "options": ["Fracciones están bien (Simplex)", "Solo enteros (Programación Entera)"]
    },
}

STOCK_QUESTIONS = {
    "demand_D": {
        "question": "¿Cuántas unidades vendés o consumís por año?",
        "why": "La demanda anual (D) es el parámetro central del modelo EOQ.",
    },
    "order_cost_k": {
        "question": "¿Cuánto cuesta hacer un pedido? (incluí flete, administración, recepción)",
        "why": "El costo de pedido (k) determina cuántos pedidos conviene hacer por año.",
    },
    "holding_cost_c1": {
        "question": "¿Cuánto cuesta mantener una unidad en stock por año? (alquiler, seguro, capital inmovilizado)",
        "why": "El costo de almacenamiento (c1) penaliza tener mucho stock. Equilibra contra el costo de pedir.",
    },
    "acquisition_cost_b": {
        "question": "¿Cuál es el precio unitario de compra?",
        "why": "El precio (b) impacta en el costo total y es relevante si hay descuentos por cantidad.",
    },
    "lead_time_LT": {
        "question": "¿Cuánto tarda en llegar un pedido desde que lo hacés? (en días)",
        "why": "El tiempo de entrega (LT) determina cuándo hay que pedir para no quedarse sin stock.",
    },
    "shortage": {
        "question": "¿Es aceptable quedarte sin stock alguna vez, o siempre tenés que tener disponible?",
        "why": "Si se admiten faltantes, el modelo cambia: se agrega un costo de agotamiento (c2) y el lote óptimo es mayor.",
        "options": ["Nunca puede faltar stock", "A veces puedo quedarme sin stock (tiene un costo)"]
    },
    "safety_stock": {
        "question": "¿Querés considerar un stock de seguridad por si el proveedor se atrasa?",
        "why": "El stock de protección (Sp) es un colchón extra que sube el costo de almacenamiento pero protege contra demoras.",
        "options": ["Sí, quiero colchón de seguridad", "No, confío en los tiempos de entrega"]
    },
}

QUEUE_QUESTIONS = {
    "arrival_rate_lambda": {
        "question": "¿Cuántos clientes llegan en promedio por hora?",
        "why": "La tasa de llegada (λ) define la demanda sobre el sistema de servicio.",
    },
    "service_rate_mu": {
        "question": "¿Cuántos clientes puede atender un servidor por hora en promedio?",
        "why": "La tasa de servicio (μ) por servidor determina la capacidad del sistema.",
    },
    "num_servers_M": {
        "question": "¿Cuántos servidores (cajeros, ventanillas, etc.) tenés en paralelo?",
        "why": "El número de servidores (M) cambia el modelo: M=1 es M/M/1, M>1 es M/M/M.",
    },
    "capacity": {
        "question": "¿Hay un límite físico de cuántos clientes pueden esperar? ¿O la cola puede crecer sin límite?",
        "why": "Si hay capacidad finita (N), los clientes que llegan con el sistema lleno se pierden. Cambia a modelo M/M/1/N.",
        "options": ["Sin límite (cola puede crecer)", "Hay un límite de capacidad"]
    },
    "cost_per_wait_ce": {
        "question": "¿Podés estimar cuánto te cuesta (en dinero) que un cliente espere una hora?",
        "why": "El costo de espera (ce) permite optimizar económicamente: ¿conviene agregar servidores?",
    },
    "cost_per_server_cs": {
        "question": "¿Cuánto cuesta operar un servidor por hora?",
        "why": "El costo del servidor (cs) se balancea contra el costo de espera para encontrar el óptimo.",
    },
}


def get_missing_params(module: str, params: Dict) -> List[Dict]:
    """
    Return list of questions for missing parameters.
    Each question includes: key, question, why, options (if any).
    """
    missing = []

    if module == "LP":
        questions = LP_QUESTIONS
        required = ["objective_type", "products", "constraints"]
    elif module == "STOCK":
        questions = STOCK_QUESTIONS
        param_map = {
            "demand_D": "demand_D",
            "order_cost_k": "order_cost_k",
            "holding_cost_c1": "holding_cost_c1",
            "acquisition_cost_b": "acquisition_cost_b",
            "lead_time_LT": "lead_time_LT",
        }
        required = [k for k, v in param_map.items() if v not in params]
    elif module == "QUEUE":
        questions = QUEUE_QUESTIONS
        param_map = {
            "arrival_rate_lambda": "arrival_rate_lambda",
            "service_rate_mu": "service_rate_mu",
            "num_servers_M": "num_servers_M",
        }
        required = [k for k, v in param_map.items() if v not in params]
    else:
        return []

    for key in required:
        if key in questions:
            q = questions[key].copy()
            q["key"] = key
            missing.append(q)

    return missing


def generate_confirmation(module: str, subtype: str, params: Dict, assumptions: List[str]) -> str:
    """Generate a confirmation message before solving."""
    lines = [f"**Voy a resolver un modelo {subtype} con estos datos:**\n"]

    if module == "STOCK":
        labels = {
            "demand_D": ("Demanda anual (D)", "unidades/año"),
            "order_cost_k": ("Costo de pedido (k)", "$/pedido"),
            "holding_cost_c1": ("Costo almacenamiento (c₁)", "$/un/año"),
            "acquisition_cost_b": ("Precio unitario (b)", "$/unidad"),
            "lead_time_LT": ("Tiempo de entrega", "años"),
            "safety_stock_Sp": ("Stock de protección (Sp)", "unidades"),
            "shortage_cost_c2": ("Costo de faltante (c₂)", "$/un/año"),
        }
        for key, (label, unit) in labels.items():
            if key in params:
                val = params[key]
                if key == "lead_time_LT":
                    lines.append(f"- {label}: {val*365:.0f} días ({val:.4f} años)")
                else:
                    lines.append(f"- {label}: {val} {unit}")

    elif module == "QUEUE":
        labels = {
            "arrival_rate_lambda": ("Tasa de llegada (λ)", "clientes/hora"),
            "service_rate_mu": ("Tasa de servicio (μ)", "clientes/hora/servidor"),
            "num_servers_M": ("Servidores (M)", ""),
            "system_capacity_N": ("Capacidad (N)", "lugares"),
            "cost_per_wait_ce": ("Costo espera (ce)", "$/cliente/hora"),
            "cost_per_server_cs": ("Costo servidor (cs)", "$/hora"),
        }
        for key, (label, unit) in labels.items():
            if key in params and params[key] is not None:
                lines.append(f"- {label}: {params[key]} {unit}")

    elif module == "LP":
        if "objective_type" in params:
            lines.append(f"- Objetivo: {params['objective_type']}")
        if "objective_coefficients" in params:
            for var, coeff in params["objective_coefficients"].items():
                lines.append(f"- {var}: coeficiente = {coeff}")

    if assumptions:
        lines.append("\n**Supuestos:**")
        for a in assumptions:
            lines.append(f"- {a}")

    lines.append("\n¿Es correcto? Puedo resolver con estos datos o ajustar algo.")
    return "\n".join(lines)
