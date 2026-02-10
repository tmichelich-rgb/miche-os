"""
Solver de Teoría de Colas.
Basado en: Miranda, "Teoría de Colas"
Modelos: M/M/1, M/M/1/N, M/M/M, M/M/M/N, con optimización económica.
"""
import math
from typing import Dict, Optional, List


def solve_queue(problem_spec: Dict) -> Dict:
    """
    Resuelve un problema de colas según el subtipo.

    problem_spec.model_spec debe contener:
      - arrival_rate_lambda: tasa de llegada (clientes/hora)
      - service_rate_mu: tasa de servicio por servidor (clientes/hora)
      - num_servers_M: número de servidores
      - system_capacity_N: capacidad del sistema (null = infinita)
      - discipline: "FIFO" (default)
      - cost_per_wait_ce: costo de espera por cliente por hora
      - cost_per_server_cs: costo por servidor por hora
      - revenue_per_service_u: ingreso por servicio
    """
    spec = problem_spec
    ms = spec.get("model_spec", spec)

    lam = float(ms.get("arrival_rate_lambda", 0))
    mu = float(ms.get("service_rate_mu", 0))
    M = int(ms.get("num_servers_M", 1))
    N = ms.get("system_capacity_N")
    ce = ms.get("cost_per_wait_ce")
    cs = ms.get("cost_per_server_cs")
    u = ms.get("revenue_per_service_u")
    impatience = ms.get("impatience_alpha")

    warnings = []

    # --- Validaciones ---
    if lam <= 0:
        return {"status": "ERROR", "message": "La tasa de llegada (λ) debe ser positiva.", "warnings": []}
    if mu <= 0:
        return {"status": "ERROR", "message": "La tasa de servicio (μ) debe ser positiva.", "warnings": []}
    if M < 1:
        return {"status": "ERROR", "message": "Debe haber al menos 1 servidor.", "warnings": []}

    # --- Routing ---
    if N is not None:
        N = int(N)
        if M == 1:
            result = _solve_mm1_n(lam, mu, N, warnings)
        else:
            result = _solve_mmm_n(lam, mu, M, N, warnings)
    else:
        if M == 1:
            result = _solve_mm1(lam, mu, warnings)
        else:
            result = _solve_mmm(lam, mu, M, warnings)

    if result.get("status") == "ERROR":
        return result

    # --- Optimización económica ---
    if ce is not None and cs is not None:
        ce = float(ce)
        cs = float(cs)
        econ = _economic_optimization(lam, mu, M, N, ce, cs, u, warnings)
        result["economic_analysis"] = econ

    # --- Decisión operativa ---
    result["decision"] = _generate_queue_decision(result, M, lam, mu, ce, cs)

    return result


def _solve_mm1(lam, mu, warnings) -> Dict:
    """
    M/M/1: Un servidor, capacidad infinita (Miranda Cap. 2).
    Condición: ρ = λ/μ < 1
    """
    rho = lam / mu

    if rho >= 1:
        return {
            "status": "INESTABLE",
            "message": (
                f"ρ = λ/μ = {lam}/{mu} = {rho:.3f} ≥ 1. "
                f"El sistema es INESTABLE: la cola crece indefinidamente. "
                f"Se necesita que la tasa de servicio supere la de llegadas (μ > λ). "
                f"Considere agregar servidores o aumentar la velocidad de servicio."
            ),
            "warnings": warnings,
            "rho": round(rho, 4),
        }

    # Fórmulas Miranda Cap. 2
    p0 = 1 - rho                              # P(sistema vacío)
    L = lam / (mu - lam)                      # Clientes en sistema
    Lc = lam**2 / (mu * (mu - lam))          # Clientes en cola
    W = 1 / (mu - lam)                        # Tiempo en sistema
    Wc = lam / (mu * (mu - lam))             # Tiempo en cola
    H = rho                                    # Clientes siendo atendidos
    Ts = 1 / mu                               # Tiempo de servicio

    # Probabilidad de esperar
    prob_wait = rho  # P(Wc > 0)

    # p(n) distribution for first 10 states
    state_probs = {}
    for n in range(11):
        state_probs[n] = round(rho**n * (1 - rho), 6)

    return {
        "status": "ÓPTIMO",
        "model": "M/M/1",
        "kendall": "P/P/1",
        "results": {
            "rho": round(rho, 4),
            "p0": round(p0, 4),
            "L": round(L, 4),
            "Lc": round(Lc, 4),
            "W_hours": round(W, 4),
            "W_minutes": round(W * 60, 2),
            "Wc_hours": round(Wc, 4),
            "Wc_minutes": round(Wc * 60, 2),
            "H": round(H, 4),
            "Ts_minutes": round(Ts * 60, 2),
            "prob_wait": round(prob_wait, 4),
            "utilization_pct": round(rho * 100, 2),
        },
        "state_probabilities": state_probs,
        "sensitivity": _queue_sensitivity_rho(lam, mu, 1),
        "warnings": warnings,
        "formulas_used": {
            "L": "λ / (μ - λ)",
            "Lc": "λ² / μ(μ - λ)",
            "W": "1 / (μ - λ)",
            "Wc": "λ / μ(μ - λ)",
            "p(n)": "ρⁿ(1 - ρ)",
            "condition": "ρ = λ/μ < 1",
            "source": "Miranda, Teoría de Colas, Cap. 2"
        }
    }


def _solve_mm1_n(lam, mu, N, warnings) -> Dict:
    """
    M/M/1/N: Un servidor, capacidad finita N (Miranda Cap. 2).
    No requiere ρ < 1 (siempre estable).
    """
    rho = lam / mu

    if abs(rho - 1.0) < 1e-10:
        # Caso especial ρ = 1
        p0 = 1 / (N + 1)
        state_probs = {n: round(p0, 6) for n in range(N + 1)}
    else:
        p0 = (1 - rho) / (1 - rho**(N + 1))
        state_probs = {}
        for n in range(N + 1):
            state_probs[n] = round(rho**n * p0, 6)

    # Tasa efectiva de ingreso
    pN = state_probs[N]
    lam_eff = lam * (1 - pN)
    rejection_rate = lam * pN

    # L (clientes en sistema)
    if abs(rho - 1.0) < 1e-10:
        L = N / 2
    else:
        L = rho * (1 - (N + 1) * rho**N + N * rho**(N + 1)) / ((1 - rho) * (1 - rho**(N + 1)))

    W = L / lam_eff if lam_eff > 0 else 0
    H = lam_eff / mu
    Lc = L - H
    Wc = Lc / lam_eff if lam_eff > 0 else 0

    if rho >= 1:
        warnings.append(
            f"ρ = {rho:.3f} ≥ 1, pero el sistema es estable gracias a la capacidad finita N={N}. "
            f"Sin embargo, la tasa de rechazo es alta ({pN*100:.1f}% de clientes rechazados)."
        )

    return {
        "status": "ÓPTIMO",
        "model": "M/M/1/N",
        "kendall": f"P/P/1/{N}",
        "results": {
            "rho": round(rho, 4),
            "N_capacity": N,
            "p0": round(p0, 6),
            "pN_rejection": round(pN, 6),
            "lambda_effective": round(lam_eff, 4),
            "rejection_rate": round(rejection_rate, 4),
            "L": round(L, 4),
            "Lc": round(Lc, 4),
            "W_hours": round(W, 4),
            "W_minutes": round(W * 60, 2),
            "Wc_hours": round(Wc, 4),
            "Wc_minutes": round(Wc * 60, 2),
            "H": round(H, 4),
            "utilization_pct": round(H * 100, 2),
        },
        "state_probabilities": state_probs,
        "warnings": warnings,
        "formulas_used": {
            "p0": "(1-ρ) / (1-ρ^(N+1))",
            "p(n)": "ρⁿ · p(0)",
            "L": "ρ[1-(N+1)ρᴺ+Nρᴺ⁺¹] / (1-ρ)(1-ρᴺ⁺¹)",
            "λ_eff": "λ(1 - p(N))",
            "source": "Miranda, Teoría de Colas, Cap. 2"
        }
    }


def _compute_mmm_metrics(lam, mu, M) -> Optional[Dict]:
    """Compute M/M/M metrics without sensitivity (avoids recursion)."""
    rho_total = lam / mu
    rho = lam / (M * mu)
    if rho >= 1:
        return None
    sum1 = sum(rho_total**n / math.factorial(n) for n in range(M))
    sum2 = (rho_total**M / math.factorial(M)) * (1 / (1 - rho))
    p0 = 1 / (sum1 + sum2)
    C_erlang = (rho_total**M / math.factorial(M)) * (1 / (1 - rho)) * p0
    Lc = C_erlang * rho / (1 - rho)
    H = rho_total
    L = Lc + H
    Wc = Lc / lam
    W = Wc + 1 / mu
    return {"L": L, "Lc": Lc, "W": W, "Wc": Wc, "rho": rho, "p0": p0, "C_erlang": C_erlang, "H": H}


def _solve_mmm(lam, mu, M, warnings) -> Dict:
    """
    M/M/M: Múltiples servidores, capacidad infinita (Miranda Cap. 3).
    Condición: ρ = λ/(Mμ) < 1
    """
    rho_total = lam / mu  # ρ total (a.k.a. traffic intensity)
    rho = lam / (M * mu)  # ρ por servidor (utilización)

    if rho >= 1:
        return {
            "status": "INESTABLE",
            "message": (
                f"ρ = λ/(Mμ) = {lam}/({M}×{mu}) = {rho:.3f} ≥ 1. "
                f"El sistema con {M} servidores es INESTABLE. "
                f"Se necesitan al menos {math.ceil(lam/mu)} servidores para estabilidad."
            ),
            "warnings": warnings,
            "rho": round(rho, 4),
            "min_servers_needed": math.ceil(lam / mu),
        }

    # p(0) - Miranda Cap. 3
    sum1 = sum(rho_total**n / math.factorial(n) for n in range(M))
    sum2 = (rho_total**M / math.factorial(M)) * (1 / (1 - rho))
    p0 = 1 / (sum1 + sum2)

    # Probabilidad de esperar (Erlang C)
    C_erlang = (rho_total**M / math.factorial(M)) * (1 / (1 - rho)) * p0

    # Lc - clientes en cola
    Lc = C_erlang * rho / (1 - rho)

    # L, W, Wc
    H = rho_total  # clientes siendo atendidos = λ/μ
    L = Lc + H
    Wc = Lc / lam
    W = Wc + 1 / mu

    # State probabilities
    state_probs = {}
    for n in range(min(M + 10, 20)):
        if n < M:
            pn = (rho_total**n / math.factorial(n)) * p0
        else:
            pn = (rho_total**n / (math.factorial(M) * M**(n - M))) * p0
        state_probs[n] = round(pn, 6)

    return {
        "status": "ÓPTIMO",
        "model": "M/M/M",
        "kendall": f"P/P/{M}",
        "results": {
            "M_servers": M,
            "rho_per_server": round(rho, 4),
            "rho_total": round(rho_total, 4),
            "p0": round(p0, 6),
            "prob_wait": round(C_erlang, 4),
            "L": round(L, 4),
            "Lc": round(Lc, 4),
            "W_hours": round(W, 4),
            "W_minutes": round(W * 60, 2),
            "Wc_hours": round(Wc, 4),
            "Wc_minutes": round(Wc * 60, 2),
            "H": round(H, 4),
            "utilization_pct": round(rho * 100, 2),
        },
        "state_probabilities": state_probs,
        "sensitivity": _queue_sensitivity_rho(lam, mu, M),
        "warnings": warnings,
        "formulas_used": {
            "p0": "1 / [Σ(ρᵀⁿ/n!) + (ρᵀᴹ/M!)·1/(1-ρ)]",
            "Lc": "C(M,ρᵀ) · ρ/(1-ρ)",
            "C_erlang": "(ρᵀᴹ/M!)·(1/(1-ρ))·p(0)",
            "condition": "ρ = λ/(Mμ) < 1",
            "source": "Miranda, Teoría de Colas, Cap. 3"
        }
    }


def _solve_mmm_n(lam, mu, M, N, warnings) -> Dict:
    """
    M/M/M/N: Múltiples servidores, capacidad finita (Miranda Cap. 3).
    """
    rho_total = lam / mu
    rho = lam / (M * mu)

    # State probabilities
    # p(n) for n <= M: (ρᵀ)ⁿ/n! · p(0)
    # p(n) for M < n <= N: (ρᵀ)ⁿ/(M!·Mⁿ⁻ᴹ) · p(0)
    coeffs = []
    for n in range(N + 1):
        if n <= M:
            coeffs.append(rho_total**n / math.factorial(n))
        else:
            coeffs.append(rho_total**n / (math.factorial(M) * M**(n - M)))

    p0 = 1 / sum(coeffs)

    state_probs = {}
    for n in range(N + 1):
        state_probs[n] = round(coeffs[n] * p0, 6)

    pN = state_probs[N]
    lam_eff = lam * (1 - pN)

    # L
    L = sum(n * state_probs[n] for n in range(N + 1))
    # H
    H = sum(n * state_probs[n] for n in range(1, min(M + 1, N + 1)))
    H += sum(M * state_probs[n] for n in range(M, N + 1))
    H = lam_eff / mu  # Simpler: H = λ_eff / μ

    Lc = L - H
    W = L / lam_eff if lam_eff > 0 else 0
    Wc = Lc / lam_eff if lam_eff > 0 else 0

    return {
        "status": "ÓPTIMO",
        "model": "M/M/M/N",
        "kendall": f"P/P/{M}/{N}",
        "results": {
            "M_servers": M,
            "N_capacity": N,
            "rho_per_server": round(rho, 4),
            "p0": round(p0, 6),
            "pN_rejection": round(pN, 6),
            "lambda_effective": round(lam_eff, 4),
            "rejection_rate": round(lam * pN, 4),
            "L": round(L, 4),
            "Lc": round(Lc, 4),
            "W_hours": round(W, 4),
            "W_minutes": round(W * 60, 2),
            "Wc_hours": round(Wc, 4),
            "Wc_minutes": round(Wc * 60, 2),
            "H": round(H, 4),
            "utilization_pct": round(rho * 100, 2) if rho < 1 else round(H / M * 100, 2),
        },
        "state_probabilities": state_probs,
        "warnings": warnings,
        "formulas_used": {
            "source": "Miranda, Teoría de Colas, Cap. 3"
        }
    }


def _generate_queue_decision(result: Dict, M: int, lam: float, mu: float,
                             ce: float = None, cs: float = None) -> Dict:
    """Generate operational decision for queue problems."""
    r = result.get("results", {})
    model = result.get("model", "")
    decision = {
        "summary": f"Modelo {model} resuelto. Utilización: {r.get('utilization_pct', r.get('rho', 0)*100):.1f}%.",
        "actions": [],
    }

    Wc_min = r.get("Wc_minutes", 0)
    Lc = r.get("Lc", 0)
    prob_wait = r.get("prob_wait", 0)

    decision["actions"].append(f"Tiempo de espera promedio en cola: {Wc_min:.1f} minutos.")
    decision["actions"].append(f"Clientes en cola promedio: {Lc:.2f}.")
    decision["actions"].append(f"Probabilidad de que un cliente deba esperar: {prob_wait*100:.1f}%.")

    econ = result.get("economic_analysis")
    if econ and econ.get("optimal_M"):
        opt_M = econ["optimal_M"]
        if opt_M > M:
            decision["actions"].append(
                f"Recomendación: agregar {opt_M - M} servidor(es) (pasar de {M} a {opt_M})."
            )
        elif opt_M < M:
            decision["actions"].append(
                f"Se podrían reducir servidores de {M} a {opt_M} sin impacto significativo."
            )
        else:
            decision["actions"].append(f"La cantidad actual de {M} servidores es óptima.")

    return decision


def _economic_optimization(lam, mu, M_current, N, ce, cs, u, warnings) -> Dict:
    """
    Optimización económica: ¿cuántos servidores minimizan el costo total?
    CT = ce·L + cs·M  (Miranda Cap. 2-3)
    """
    M_min = max(1, math.ceil(lam / mu))  # mínimo para estabilidad
    M_max = M_min + 5  # evaluar hasta 5 extra

    comparisons = []
    for M_test in range(max(1, M_min - 1), M_max + 1):
        rho = lam / (M_test * mu)

        if N is not None:
            res = _solve_mmm_n(lam, mu, M_test, N, []) if M_test > 1 else _solve_mm1_n(lam, mu, N, [])
        else:
            if rho >= 1:
                comparisons.append({
                    "M": M_test,
                    "status": "INESTABLE",
                    "note": f"ρ = {rho:.3f} ≥ 1"
                })
                continue
            if M_test > 1:
                metrics = _compute_mmm_metrics(lam, mu, M_test)
                if metrics is None:
                    comparisons.append({"M": M_test, "status": "INESTABLE", "note": "metrics failed"})
                    continue
                res = {"status": "ÓPTIMO", "results": {
                    "L": metrics["L"], "Lc": metrics["Lc"],
                    "Wc_hours": metrics["Wc"], "W_hours": metrics["W"],
                    "lambda_effective": lam,
                }}
            else:
                res = _solve_mm1(lam, mu, [])

        if res.get("status") in ("ERROR", "INESTABLE"):
            comparisons.append({
                "M": M_test,
                "status": "INESTABLE",
                "note": res.get("message", "")[:100]
            })
            continue

        r = res["results"]
        Wc_hrs = r.get("Wc_hours", 0)
        L_val = r.get("L", 0)
        Lc_val = r.get("Lc", 0)

        # Miranda: CT = ce·L + cs·M
        # ce en $/cliente/hora en el sistema. Si usuario da por minuto, el frontend convierte.
        cost_wait = ce * L_val
        cost_servers = cs * M_test
        cost_total = cost_wait + cost_servers

        revenue = 0
        if u:
            lam_eff = r.get("lambda_effective", lam)
            revenue = float(u) * lam_eff

        comparisons.append({
            "M": M_test,
            "status": "ESTABLE",
            "rho": round(rho, 4),
            "Wc_minutes": round(Wc_hrs * 60, 2),
            "Lc": round(Lc_val, 2),
            "L": round(L_val, 2),
            "cost_wait_per_hour": round(cost_wait, 2),
            "cost_servers_per_hour": round(cost_servers, 2),
            "cost_total_per_hour": round(cost_total, 2),
            "revenue_per_hour": round(revenue, 2) if u else None,
            "profit_per_hour": round(revenue - cost_total, 2) if u else None,
        })

    # Find optimal
    stable = [c for c in comparisons if c.get("status") == "ESTABLE"]
    if stable:
        optimal = min(stable, key=lambda c: c["cost_total_per_hour"])
        optimal["is_optimal"] = True
    else:
        optimal = None

    return {
        "comparisons": comparisons,
        "optimal_M": optimal["M"] if optimal else None,
        "interpretation": (
            f"El número óptimo de servidores es {optimal['M']} "
            f"con un costo total de ${optimal['cost_total_per_hour']:.2f}/hora."
            if optimal else "No se encontró configuración estable."
        )
    }


def _queue_sensitivity_rho(lam, mu, M) -> Dict:
    """Compute sensitivity to changes in λ."""
    results = []
    for factor in [0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3]:
        lam_test = lam * factor
        rho_test = lam_test / (M * mu)
        if rho_test >= 1:
            results.append({
                "lambda_factor": factor,
                "lambda": round(lam_test, 2),
                "rho": round(rho_test, 4),
                "status": "INESTABLE"
            })
        else:
            if M == 1:
                L = lam_test / (mu - lam_test)
                Wc = lam_test / (mu * (mu - lam_test))
            else:
                metrics = _compute_mmm_metrics(lam_test, mu, M)
                if metrics is None:
                    results.append({
                        "lambda_factor": factor,
                        "lambda": round(lam_test, 2),
                        "rho": round(rho_test, 4),
                        "status": "INESTABLE"
                    })
                    continue
                L = metrics["L"]
                Wc = metrics["Wc"]
            results.append({
                "lambda_factor": factor,
                "lambda": round(lam_test, 2),
                "rho": round(rho_test, 4),
                "L": round(L, 2),
                "Wc_minutes": round(Wc * 60, 2),
                "status": "ESTABLE"
            })

    return {
        "lambda_sensitivity": results,
        "interpretation": (
            "La tabla muestra cómo varía el rendimiento del sistema ante cambios en la tasa de llegada. "
            "A medida que ρ se acerca a 1, la cola crece exponencialmente."
        )
    }
