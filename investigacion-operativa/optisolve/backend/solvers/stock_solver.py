"""
Solver de Inventarios / Gestión de Stocks.
Basado en: Miranda, "Sistemas de Optimización de Stocks"
Modelos: EOQ básico, con agotamiento, reposición gradual, descuentos, stock de protección.
"""
import math
from typing import Dict, Optional, List


def solve_stock(problem_spec: Dict) -> Dict:
    """
    Resuelve un problema de inventarios según el subtipo.

    problem_spec.model_spec debe contener:
      - demand_D: demanda anual
      - order_cost_k: costo por pedido
      - holding_cost_c1: costo de almacenamiento por unidad por año
      - acquisition_cost_b: precio unitario de compra
      - shortage_cost_c2: costo de faltante (null si no aplica)
      - lead_time_LT: tiempo de entrega (en años)
      - safety_stock_Sp: stock de protección
      - planning_horizon_T: horizonte (generalmente 1 año)
      - replenishment_type: "instantaneous" | "gradual"
      - production_rate_p: tasa de producción (solo si gradual)
      - discount_schedule: [{qty_min, price}] o null
    """
    spec = problem_spec
    subtype = spec.get("subtype", "eoq_basic")
    ms = spec.get("model_spec", spec)  # Support both nested and flat

    D = float(ms.get("demand_D", 0))
    k = float(ms.get("order_cost_k", 0))
    c1 = float(ms.get("holding_cost_c1", 0))
    b = float(ms.get("acquisition_cost_b", 0))
    c2 = ms.get("shortage_cost_c2")
    LT = float(ms.get("lead_time_LT", 0))
    Sp = float(ms.get("safety_stock_Sp", 0))
    T = float(ms.get("planning_horizon_T", 1))
    rep_type = ms.get("replenishment_type", "instantaneous")
    prod_rate = ms.get("production_rate_p")
    discounts = ms.get("discount_schedule")

    warnings = []

    # --- Validaciones ---
    if D <= 0:
        return {"status": "ERROR", "message": "La demanda (D) debe ser positiva.", "warnings": []}
    if k < 0:
        return {"status": "ERROR", "message": "El costo de pedido (k) no puede ser negativo.", "warnings": []}
    if c1 <= 0:
        return {"status": "ERROR", "message": "El costo de almacenamiento (c1) debe ser positivo.", "warnings": []}
    if T <= 0:
        return {"status": "ERROR", "message": "El horizonte de planificación (T) debe ser positivo.", "warnings": []}

    if c2 is not None:
        c2 = float(c2)
        if c2 <= 0:
            warnings.append("El costo de faltante (c2) debe ser positivo. Se ignora el agotamiento.")
            c2 = None

    # --- Routing por subtipo ---
    if discounts and len(discounts) > 0:
        return _solve_eoq_discounts(D, k, c1, b, T, LT, Sp, discounts, warnings)
    elif c2 is not None:
        return _solve_eoq_shortage(D, k, c1, c2, b, T, LT, Sp, warnings)
    elif rep_type == "gradual" and prod_rate:
        return _solve_eoq_gradual(D, k, c1, b, T, LT, Sp, float(prod_rate), warnings)
    else:
        return _solve_eoq_basic(D, k, c1, b, T, LT, Sp, warnings)


def _solve_eoq_basic(D, k, c1, b, T, LT, Sp, warnings) -> Dict:
    """
    EOQ Básico (Miranda Cap. 2).
    qo = √(2kD / Tc1)
    to = (T/D) · qo
    CTEo = bD + √(2kDTc1) + Sp·c1
    """
    # Lote óptimo
    qo = math.sqrt(2 * k * D / (T * c1))

    # Intervalo óptimo entre pedidos
    to = (T / D) * qo

    # Número óptimo de pedidos
    no = D / qo

    # Costo total esperado
    # CTE = b·D + (D/q)·k + (q/2)·T·c1 + Sp·c1·T
    cost_acquisition = b * D
    cost_ordering = (D / qo) * k
    cost_holding = (qo / 2) * T * c1
    cost_safety = Sp * c1 * T
    CTE = cost_acquisition + cost_ordering + cost_holding + cost_safety

    # Demanda diaria (365 días)
    d_daily = D / 365

    # Punto de reorden
    LT_days = LT * 365
    SR = LT * D / T + Sp

    # Stock máximo
    S_max = qo + Sp

    # --- Sensibilidad (Miranda Cap. 2) ---
    # λ = ½(α + 1/α) donde α = q/qo
    sensitivity = _eoq_sensitivity(qo, D, k, c1, T, b)

    decision = {
        "summary": f"Modelo EOQ básico (Miranda Cap.2). Reposición instantánea, sin faltantes.",
        "actions": [
            f"Pedir {qo:.0f} unidades cada vez (lote óptimo).",
            f"Hacer un pedido cada {to*365:.1f} días ({no:.1f} pedidos/año).",
            f"Cuando el stock baje a {SR:.0f} unidades, emitir nuevo pedido.",
            f"Stock máximo: {S_max:.0f} unidades.",
            f"Mantener {Sp:.0f} unidades como stock de seguridad.",
        ],
        "costs": {
            "costo_adquisicion": round(cost_acquisition, 2),
            "costo_pedidos": round(cost_ordering, 2),
            "costo_almacenamiento": round(cost_holding, 2),
            "costo_proteccion": round(cost_safety, 2),
            "costo_total": round(CTE, 2),
        }
    }

    return {
        "status": "ÓPTIMO",
        "subtype": "eoq_basic",
        "results": {
            "qo": round(qo, 2),
            "to_years": round(to, 6),
            "to_days": round(to * 365, 1),
            "no_orders": round(no, 2),
            "SR_reorder_point": round(SR, 2),
            "S_max": round(S_max, 2),
            "d_daily": round(d_daily, 2),
            "CTE": round(CTE, 2),
        },
        "sensitivity": sensitivity,
        "decision": decision,
        "warnings": warnings,
        "formulas_used": {
            "qo": "√(2kD / Tc₁)",
            "to": "(T/D) · qo",
            "CTE": "bD + √(2kDTc₁) + Sp·c₁",
            "SR": "LT·(D/T) + Sp",
            "source": "Miranda, Sistemas de Optimización de Stocks, Cap. 2"
        }
    }


def _solve_eoq_shortage(D, k, c1, c2, b, T, LT, Sp, warnings) -> Dict:
    """
    EOQ con agotamiento admitido (Miranda Cap. 4).
    qo = √(2kD(c1+c2) / Tc1c2)
    So = qo · √(c2 / (c1+c2))   [stock máximo antes de agotar]
    """
    qo = math.sqrt(2 * k * D * (c1 + c2) / (T * c1 * c2))
    So = qo * math.sqrt(c2 / (c1 + c2))
    shortage_max = qo - So  # máximo faltante

    to = (T / D) * qo
    no = D / qo

    # Costos
    cost_acquisition = b * D
    cost_ordering = (D / qo) * k
    cost_holding = (So ** 2) * T * c1 / (2 * qo)
    cost_shortage = ((qo - So) ** 2) * T * c2 / (2 * qo)
    cost_safety = Sp * c1 * T
    CTE = cost_acquisition + cost_ordering + cost_holding + cost_shortage + cost_safety

    SR = LT * D / T + Sp - shortage_max

    sensitivity = _eoq_sensitivity(qo, D, k, c1, T, b, c2=c2)

    decision = {
        "summary": f"Modelo EOQ con agotamiento (Miranda Cap.4). Se permite faltante controlado.",
        "actions": [
            f"Pedir {qo:.0f} unidades cada vez.",
            f"Hacer un pedido cada {to*365:.1f} días.",
            f"Stock máximo alcanzado: {So:.0f} unidades.",
            f"Faltante máximo permitido: {shortage_max:.0f} unidades.",
            f"Punto de reorden: {SR:.0f} unidades.",
        ],
        "costs": {
            "costo_adquisicion": round(cost_acquisition, 2),
            "costo_pedidos": round(cost_ordering, 2),
            "costo_almacenamiento": round(cost_holding, 2),
            "costo_faltante": round(cost_shortage, 2),
            "costo_total": round(CTE, 2),
        }
    }

    return {
        "status": "ÓPTIMO",
        "subtype": "eoq_shortage",
        "results": {
            "qo": round(qo, 2),
            "So": round(So, 2),
            "shortage_max": round(shortage_max, 2),
            "to_days": round(to * 365, 1),
            "no_orders": round(no, 2),
            "SR": round(SR, 2),
            "CTE": round(CTE, 2),
        },
        "sensitivity": sensitivity,
        "decision": decision,
        "warnings": warnings,
        "formulas_used": {
            "qo": "√(2kD(c₁+c₂) / Tc₁c₂)",
            "So": "qo · √(c₂ / (c₁+c₂))",
            "source": "Miranda, Sistemas de Optimización de Stocks, Cap. 4"
        }
    }


def _solve_eoq_gradual(D, k, c1, b, T, LT, Sp, p, warnings) -> Dict:
    """
    EOQ con reposición gradual (Miranda Cap. 3).
    qo = √(2kD / Tc₁(1 - D/pT))
    """
    if p <= D / T:
        return {
            "status": "ERROR",
            "message": f"La tasa de producción ({p}) debe ser mayor que la tasa de demanda ({D/T:.1f}). "
                       f"No se puede acumular stock si se consume más rápido de lo que se produce.",
            "warnings": warnings,
        }

    factor = 1 - D / (p * T)
    qo = math.sqrt(2 * k * D / (T * c1 * factor))
    to = (T / D) * qo

    # Stock máximo (menor que q porque se consume durante producción)
    S_max_prod = qo * factor

    no = D / qo
    cost_acquisition = b * D
    cost_ordering = (D / qo) * k
    cost_holding = (S_max_prod / 2) * T * c1
    CTE = cost_acquisition + cost_ordering + cost_holding + Sp * c1 * T

    sensitivity = _eoq_sensitivity(qo, D, k, c1, T, b)

    decision = {
        "summary": "Modelo EOQ con reposición gradual (Miranda Cap.3). Producción propia o entrega paulatina.",
        "actions": [
            f"Producir/pedir lotes de {qo:.0f} unidades.",
            f"Ciclo de {to*365:.1f} días entre inicios de producción.",
            f"Stock máximo real: {S_max_prod:.0f} unidades (menor que q por consumo durante producción).",
        ],
        "costs": {
            "costo_adquisicion": round(cost_acquisition, 2),
            "costo_pedidos": round(cost_ordering, 2),
            "costo_almacenamiento": round(cost_holding, 2),
            "costo_total": round(CTE, 2),
        }
    }

    return {
        "status": "ÓPTIMO",
        "subtype": "eoq_gradual",
        "results": {
            "qo": round(qo, 2),
            "S_max": round(S_max_prod, 2),
            "to_days": round(to * 365, 1),
            "no_orders": round(no, 2),
            "CTE": round(CTE, 2),
        },
        "sensitivity": sensitivity,
        "decision": decision,
        "warnings": warnings,
        "formulas_used": {
            "qo": "√(2kD / Tc₁(1 - D/pT))",
            "source": "Miranda, Sistemas de Optimización de Stocks, Cap. 3"
        }
    }


def _solve_eoq_discounts(D, k, c1, b, T, LT, Sp, discounts, warnings) -> Dict:
    """
    EOQ con descuentos por cantidad.
    Evalúa cada tramo de precios y compara CTEs.
    """
    # Sort discounts by qty_min ascending
    discounts = sorted(discounts, key=lambda d: d.get("qty_min", 0))

    # Add base price as first option if not present
    options = []

    # For each price break, compute optimal q and CTE
    for disc in discounts:
        qty_min = float(disc.get("qty_min", 0))
        price = float(disc.get("price", b))

        # EOQ at this price
        qo = math.sqrt(2 * k * D / (T * c1))

        # If qo is within this bracket, use it; otherwise use qty_min
        q_use = max(qo, qty_min)

        cost_acq = price * D
        cost_ord = (D / q_use) * k
        cost_hold = (q_use / 2) * T * c1
        cost_safety = Sp * c1 * T
        CTE = cost_acq + cost_ord + cost_hold + cost_safety

        options.append({
            "qty_min": qty_min,
            "price": price,
            "q_used": round(q_use, 2),
            "CTE": round(CTE, 2),
            "cost_breakdown": {
                "adquisicion": round(cost_acq, 2),
                "pedidos": round(cost_ord, 2),
                "almacenamiento": round(cost_hold, 2),
            }
        })

    # Find best option
    best = min(options, key=lambda o: o["CTE"])

    decision = {
        "summary": "Modelo EOQ con descuentos por cantidad. Se evaluaron todos los tramos de precio.",
        "actions": [
            f"Mejor opción: pedir {best['q_used']:.0f} unidades a ${best['price']}/unidad.",
            f"CTE mínimo: ${best['CTE']:,.2f}/año.",
        ],
        "all_options": options,
    }

    return {
        "status": "ÓPTIMO",
        "subtype": "eoq_discount",
        "results": {
            "best_q": best["q_used"],
            "best_price": best["price"],
            "CTE": best["CTE"],
            "all_options": options,
        },
        "decision": decision,
        "warnings": warnings,
    }


def _eoq_sensitivity(qo, D, k, c1, T, b, c2=None) -> Dict:
    """
    Análisis de sensibilidad EOQ (Miranda Cap. 2).
    λ = ½(α + 1/α), donde α = q/qo.
    Error relativo ε = λ - 1.
    """
    # Compute λ for different deviations
    deviations = [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.5]
    table = []
    for alpha in deviations:
        q = qo * alpha
        lam = 0.5 * (alpha + 1 / alpha)
        epsilon = lam - 1
        # CTE variable at this q (excluding fixed acquisition cost)
        cte_var = (D / q) * k + (q / 2) * T * c1
        cte_var_opt = math.sqrt(2 * k * D * T * c1)  # optimal variable cost

        table.append({
            "alpha": round(alpha, 2),
            "q": round(q, 0),
            "lambda": round(lam, 4),
            "epsilon_pct": round(epsilon * 100, 2),
            "cte_variable": round(cte_var, 2),
        })

    return {
        "sensitivity_table": table,
        "interpretation": (
            "La curva de costo es muy plana alrededor del óptimo. "
            f"Desviaciones del ±30% en q producen solo ~4-5% de aumento en costo variable. "
            f"Esto permite ajustar el lote a cantidades prácticas (embalajes, camiones) "
            f"sin perder eficiencia significativa."
        ),
        "formula": "λ = ½(α + 1/α), ε = λ - 1 (Miranda Cap. 2)"
    }
