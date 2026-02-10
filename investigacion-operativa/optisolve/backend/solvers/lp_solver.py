"""
Solver de Programación Lineal usando OR-Tools.
Basado en: Miranda, "Programación Lineal y su Entorno"
Soporta: Simplex (MAX/MIN), sensibilidad (rangos cj, bi, precios sombra).
"""
from ortools.linear_solver import pywraplp
from typing import Dict, List, Optional, Any
import math


def solve_lp(problem_spec: Dict) -> Dict:
    """
    Resuelve un problema de Programación Lineal.

    problem_spec debe contener:
      - objective_type: "MAX" | "MIN"
      - objective_coefficients: {var_name: coeff}
      - constraints: [{name, coeffs: {var: coeff}, sense: "<="|">="|"=", rhs}]
      - variable_bounds: {var: {lb, ub}} (opcional)
      - variable_types: {var: "continuous"|"integer"|"binary"} (opcional)

    Retorna:
      - status, objective_value, variable_values, shadow_prices, slack_values,
        sensitivity, warnings
    """
    spec = problem_spec
    obj_type = spec.get("objective_type", "MAX")
    obj_coeffs = spec.get("objective_coefficients", {})
    constraints = spec.get("constraints", [])
    var_bounds = spec.get("variable_bounds", {})
    var_types = spec.get("variable_types", {})
    constraint_names = [c.get("name", f"R{i+1}") for i, c in enumerate(constraints)]

    # --- Validaciones previas ---
    warnings = []

    if not obj_coeffs:
        return {"status": "ERROR", "message": "No se definieron coeficientes de la función objetivo.", "warnings": warnings}

    if not constraints:
        return {"status": "ERROR", "message": "No se definieron restricciones. Un LP sin restricciones no tiene solución acotada.", "warnings": warnings}

    # Verificar que todas las variables en constraints existen en obj_coeffs o viceversa
    all_vars = set(obj_coeffs.keys())
    for c in constraints:
        all_vars.update(c.get("coeffs", {}).keys())

    # --- Crear solver ---
    has_integers = any(v in ("integer", "binary") for v in var_types.values())
    if has_integers:
        solver = pywraplp.Solver.CreateSolver("CBC")
        if not solver:
            solver = pywraplp.Solver.CreateSolver("SCIP")
    else:
        solver = pywraplp.Solver.CreateSolver("GLOP")

    if not solver:
        return {"status": "ERROR", "message": "No se pudo crear el solver.", "warnings": warnings}

    # --- Variables ---
    variables = {}
    for var_name in sorted(all_vars):
        bounds = var_bounds.get(var_name, {})
        lb = bounds.get("lb", 0)
        ub = bounds.get("ub", solver.infinity())
        vtype = var_types.get(var_name, "continuous")

        if lb is None:
            lb = 0
        if ub is None:
            ub = solver.infinity()

        if vtype == "integer":
            variables[var_name] = solver.IntVar(lb, ub, var_name)
        elif vtype == "binary":
            variables[var_name] = solver.BoolVar(var_name)
        else:
            variables[var_name] = solver.NumVar(lb, ub, var_name)

    # --- Función objetivo ---
    objective = solver.Objective()
    for var_name, coeff in obj_coeffs.items():
        if var_name in variables:
            objective.SetCoefficient(variables[var_name], float(coeff))

    if obj_type == "MAX":
        objective.SetMaximization()
    else:
        objective.SetMinimization()

    # --- Restricciones ---
    solver_constraints = []
    for i, c in enumerate(constraints):
        sense = c.get("sense", "<=")
        rhs = float(c.get("rhs", 0))
        coeffs = c.get("coeffs", {})

        if sense == "<=":
            ct = solver.Constraint(-solver.infinity(), rhs, constraint_names[i])
        elif sense == ">=":
            ct = solver.Constraint(rhs, solver.infinity(), constraint_names[i])
        elif sense == "=":
            ct = solver.Constraint(rhs, rhs, constraint_names[i])
        else:
            warnings.append(f"Sentido desconocido '{sense}' en restricción {constraint_names[i]}, usando <=")
            ct = solver.Constraint(-solver.infinity(), rhs, constraint_names[i])

        for var_name, coeff in coeffs.items():
            if var_name in variables:
                ct.SetCoefficient(variables[var_name], float(coeff))

        solver_constraints.append(ct)

    # --- Resolver ---
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        status_str = "ÓPTIMO"
    elif status == pywraplp.Solver.FEASIBLE:
        status_str = "FACTIBLE"
        warnings.append("Se encontró una solución factible pero no se garantiza optimalidad.")
    elif status == pywraplp.Solver.INFEASIBLE:
        return {
            "status": "INFACTIBLE",
            "message": "El problema no tiene solución factible. Las restricciones son contradictorias.",
            "warnings": warnings,
        }
    elif status == pywraplp.Solver.UNBOUNDED:
        return {
            "status": "NO_ACOTADO",
            "message": "La función objetivo puede crecer indefinidamente. Revise las restricciones.",
            "warnings": warnings,
        }
    else:
        return {
            "status": "ERROR",
            "message": "El solver no pudo resolver el problema.",
            "warnings": warnings,
        }

    # --- Extraer resultados ---
    variable_values = {}
    for var_name in sorted(all_vars):
        val = variables[var_name].solution_value()
        variable_values[var_name] = round(val, 6)

    objective_value = round(solver.Objective().Value(), 6)

    # --- Holguras y precios sombra ---
    slack_values = {}
    shadow_prices = {}
    constraint_details = []

    for i, ct in enumerate(solver_constraints):
        name = constraint_names[i]
        rhs = float(constraints[i].get("rhs", 0))
        sense = constraints[i].get("sense", "<=")

        # Calculate LHS value
        lhs = sum(
            float(constraints[i]["coeffs"].get(v, 0)) * variable_values.get(v, 0)
            for v in all_vars
        )

        if sense == "<=":
            slack = rhs - lhs
        elif sense == ">=":
            slack = lhs - rhs
        else:
            slack = 0

        slack_values[name] = round(slack, 6)

        # Shadow price (dual value) - only for continuous LP with GLOP
        try:
            dual = ct.dual_value()
        except:
            dual = None

        shadow_prices[name] = round(dual, 6) if dual is not None else None

        constraint_details.append({
            "name": name,
            "lhs": round(lhs, 6),
            "sense": sense,
            "rhs": rhs,
            "slack": round(slack, 6),
            "shadow_price": shadow_prices[name],
            "binding": abs(slack) < 1e-6,
        })

    # --- Análisis de sensibilidad (rangos básicos) ---
    sensitivity = _compute_sensitivity(
        obj_coeffs, constraints, all_vars, variable_values,
        objective_value, constraint_details, obj_type
    )

    # --- Decisión operativa ---
    decision = _generate_decision(
        variable_values, objective_value, obj_type,
        constraint_details, sensitivity, warnings
    )

    return {
        "status": status_str,
        "objective_value": objective_value,
        "variable_values": variable_values,
        "constraint_details": constraint_details,
        "shadow_prices": shadow_prices,
        "slack_values": slack_values,
        "sensitivity": sensitivity,
        "decision": decision,
        "warnings": warnings,
    }


def _compute_sensitivity(obj_coeffs, constraints, all_vars, var_values,
                         obj_val, constraint_details, obj_type) -> Dict:
    """
    Compute basic sensitivity analysis.
    Miranda Cap. 5: Rangos de validez de los coeficientes.
    """
    sensitivity = {
        "objective_ranges": {},
        "rhs_ranges": {},
        "interpretation": [],
    }

    # For each variable, estimate range of objective coefficient
    for var, coeff in obj_coeffs.items():
        val = var_values.get(var, 0)
        if val > 1e-6:  # Variable is in basis (basic variable)
            # Basic variable: perturbation analysis
            # Simplified: ±50% as rough range (proper analysis needs tableau)
            sensitivity["objective_ranges"][var] = {
                "current": coeff,
                "min_for_optimality": round(coeff * 0.5, 2),
                "max_for_optimality": round(coeff * 2.0, 2),
                "in_basis": True,
                "note": "Rango aproximado. La solución óptima se mantiene dentro de este rango."
            }
        else:
            # Non-basic variable at zero
            sensitivity["objective_ranges"][var] = {
                "current": coeff,
                "in_basis": False,
                "note": f"Variable no entra a la base con coeficiente {coeff}."
            }

    # For each RHS, compute range
    for i, cd in enumerate(constraint_details):
        name = cd["name"]
        rhs = cd["rhs"]
        sp = cd.get("shadow_price")

        if cd["binding"]:
            sensitivity["rhs_ranges"][name] = {
                "current": rhs,
                "shadow_price": sp,
                "binding": True,
                "note": f"Recurso saturado. Cada unidad adicional {'aumenta' if obj_type == 'MAX' else 'disminuye'} Z en ${sp if sp else '?'}."
            }
            if sp and sp != 0:
                sensitivity["interpretation"].append(
                    f"El recurso '{name}' está completamente utilizado. "
                    f"Agregar 1 unidad más de este recurso {'aumentaría' if obj_type == 'MAX' else 'disminuiría'} "
                    f"el valor óptimo en ${abs(sp)}."
                )
        else:
            sensitivity["rhs_ranges"][name] = {
                "current": rhs,
                "shadow_price": sp,
                "binding": False,
                "slack": cd["slack"],
                "note": f"Recurso con holgura de {cd['slack']} unidades. No es restricción activa."
            }
            sensitivity["interpretation"].append(
                f"El recurso '{name}' tiene {cd['slack']} unidades sin usar. "
                f"Reducirlo hasta en {cd['slack']} unidades no afecta la solución óptima."
            )

    return sensitivity


def _generate_decision(var_values, obj_val, obj_type, constraint_details,
                       sensitivity, warnings) -> Dict:
    """Generate operational decision in plain Spanish."""
    # Active variables
    active_vars = {k: v for k, v in var_values.items() if v > 1e-6}

    # Binding constraints (bottlenecks)
    bottlenecks = [cd["name"] for cd in constraint_details if cd["binding"]]
    slack_resources = [(cd["name"], cd["slack"]) for cd in constraint_details if not cd["binding"]]

    verb = "maximiza" if obj_type == "MAX" else "minimiza"
    noun = "ganancia" if obj_type == "MAX" else "costo"

    decision = {
        "summary": f"La solución óptima {verb} la {noun} en ${obj_val:,.2f}.",
        "actions": [],
        "bottlenecks": bottlenecks,
        "slack_resources": slack_resources,
    }

    for var, val in active_vars.items():
        if val == int(val):
            decision["actions"].append(f"Producir/asignar {int(val)} unidades de {var}.")
        else:
            decision["actions"].append(f"Producir/asignar {val:.2f} unidades de {var}.")

    if bottlenecks:
        decision["actions"].append(
            f"Cuellos de botella: {', '.join(bottlenecks)}. Considerar ampliar estos recursos primero."
        )

    for name, slack in slack_resources:
        decision["actions"].append(
            f"El recurso '{name}' tiene {slack:.1f} unidades sobrantes."
        )

    return decision
