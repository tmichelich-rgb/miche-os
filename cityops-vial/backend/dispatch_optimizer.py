"""
CityOps Vial - Dispatch Optimizer
Optimización de asignación de cuadrillas a incidentes usando OR-Tools o heurística
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import math

from models import (
    Incident, Crew, Assignment, Location,
    IncidentStatus, CrewStatus, AssignmentStatus, Severity,
    generate_id
)
from scoring_engine import SLAUrgencyCalculator

# Try to import OR-Tools, fallback to heuristic if not available
try:
    from ortools.linear_solver import pywraplp
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False
    print("⚠️ OR-Tools no disponible, usando optimizador heurístico")


@dataclass
class DispatchRecommendation:
    incident_id: str
    incident_summary: Dict
    recommended_crew: Dict
    alternative_crews: List[Dict]
    optimizer_reasoning: Dict
    final_score: float

    def to_dict(self):
        return {
            'incident_id': self.incident_id,
            'incident_summary': self.incident_summary,
            'recommended_crew': self.recommended_crew,
            'alternative_crews': self.alternative_crews,
            'optimizer_reasoning': self.optimizer_reasoning,
            'final_score': round(self.final_score, 2)
        }


@dataclass
class DispatchPlan:
    recommendations: List[DispatchRecommendation]
    unassignable: List[Dict]
    solver_status: str
    solve_time_ms: float
    total_processed: int
    total_assigned: int
    objective_value: float

    def to_dict(self):
        return {
            'recommendations': [r.to_dict() for r in self.recommendations],
            'unassignable_incidents': self.unassignable,
            'optimization_stats': {
                'solver_status': self.solver_status,
                'solve_time_ms': round(self.solve_time_ms, 1),
                'total_incidents_processed': self.total_processed,
                'total_assigned': self.total_assigned,
                'objective_value': round(self.objective_value, 2)
            }
        }


class DispatchOptimizer:
    """
    Optimizador de asignación de cuadrillas a incidentes.

    Objetivo: Maximizar cobertura de riesgo ponderada - costos de viaje

    Constraints:
    1. Cada incidente recibe máximo una cuadrilla
    2. Cada cuadrilla puede tener máximo K asignaciones en el horizonte
    3. Compatibilidad de capacidades (cuadrilla debe poder reparar el tipo de incidente)
    4. Tiempo de viaje no excede turno restante
    5. Incidentes críticos deben ser asignados (soft constraint con alta penalidad)
    """

    def __init__(self):
        self.max_assignments_per_crew = 4
        self.travel_speed_kmh = 30  # Velocidad promedio urbana

    def optimize(
        self,
        incidents: List[Incident],
        crews: List[Crew],
        authority_id: Optional[str] = None,
        time_horizon_hours: int = 8,
        prioritize_critical: bool = True
    ) -> DispatchPlan:
        """
        Ejecuta la optimización de despacho.
        """
        start_time = datetime.now()

        # Filtrar incidentes pendientes
        pending_incidents = [
            i for i in incidents
            if i.status in (IncidentStatus.NEW, IncidentStatus.VALIDATED)
            and (authority_id is None or i.authority_id == authority_id)
        ]

        # Filtrar cuadrillas disponibles
        available_crews = [
            c for c in crews
            if c.can_accept_assignment()
            and (authority_id is None or c.authority_id == authority_id)
        ]

        if not pending_incidents:
            return DispatchPlan(
                recommendations=[],
                unassignable=[],
                solver_status='no_incidents',
                solve_time_ms=0,
                total_processed=0,
                total_assigned=0,
                objective_value=0
            )

        if not available_crews:
            return DispatchPlan(
                recommendations=[],
                unassignable=[
                    {'incident_id': i.id, 'reason': 'no_crews_available'}
                    for i in pending_incidents
                ],
                solver_status='no_crews',
                solve_time_ms=0,
                total_processed=len(pending_incidents),
                total_assigned=0,
                objective_value=0
            )

        # Elegir solver
        if ORTOOLS_AVAILABLE and len(pending_incidents) > 3:
            plan = self._optimize_ortools(pending_incidents, available_crews, time_horizon_hours, prioritize_critical)
        else:
            plan = self._optimize_greedy(pending_incidents, available_crews, time_horizon_hours)

        end_time = datetime.now()
        plan.solve_time_ms = (end_time - start_time).total_seconds() * 1000

        return plan

    def _optimize_ortools(
        self,
        incidents: List[Incident],
        crews: List[Crew],
        time_horizon_hours: int,
        prioritize_critical: bool
    ) -> DispatchPlan:
        """
        Optimización usando OR-Tools (programación lineal entera mixta).
        """
        solver = pywraplp.Solver.CreateSolver('SCIP')
        if not solver:
            # Fallback a CBC si SCIP no está disponible
            solver = pywraplp.Solver.CreateSolver('CBC')
        if not solver:
            return self._optimize_greedy(incidents, crews, time_horizon_hours)

        n_incidents = len(incidents)
        n_crews = len(crews)

        # Precomputar matrices
        compatibility = self._compute_compatibility(incidents, crews)
        travel_times = self._compute_travel_times(incidents, crews)
        benefits = self._compute_benefits(incidents, crews)

        # Variables de decisión: x[i,j] = 1 si crew j asignada a incident i
        x = {}
        for i in range(n_incidents):
            for j in range(n_crews):
                x[i, j] = solver.BoolVar(f'x_{i}_{j}')

        # =============================================
        # CONSTRAINTS
        # =============================================

        # C1: Cada incidente máximo una cuadrilla
        for i in range(n_incidents):
            solver.Add(sum(x[i, j] for j in range(n_crews)) <= 1)

        # C2: Cada cuadrilla máximo K asignaciones
        for j in range(n_crews):
            remaining = self.max_assignments_per_crew - crews[j].today_assignments
            solver.Add(sum(x[i, j] for i in range(n_incidents)) <= remaining)

        # C3: Compatibilidad
        for i in range(n_incidents):
            for j in range(n_crews):
                if not compatibility[i][j]:
                    solver.Add(x[i, j] == 0)

        # C4: Tiempo de viaje no excede turno
        for j in range(n_crews):
            remaining_shift = crews[j].get_remaining_shift_hours() * 60  # minutos
            # Tiempo total de viajes asignados
            solver.Add(
                sum(x[i, j] * travel_times[i][j] for i in range(n_incidents)) <= remaining_shift
            )

        # =============================================
        # FUNCIÓN OBJETIVO
        # =============================================
        # Maximizar: sum(benefit[i,j] * x[i,j]) - sum(travel_cost[i,j] * x[i,j])

        objective_terms = []
        for i in range(n_incidents):
            for j in range(n_crews):
                net_benefit = benefits[i][j] - (travel_times[i][j] * 0.5)  # Penalizar viaje
                objective_terms.append(x[i, j] * net_benefit)

        # Bonus por asignar incidentes críticos
        if prioritize_critical:
            for i, incident in enumerate(incidents):
                if incident.severity_estimate == Severity.CRITICAL:
                    for j in range(n_crews):
                        objective_terms.append(x[i, j] * 50)  # Bonus alto

        solver.Maximize(sum(objective_terms))

        # =============================================
        # RESOLVER
        # =============================================
        status = solver.Solve()

        if status not in (pywraplp.Solver.OPTIMAL, pywraplp.Solver.FEASIBLE):
            return self._optimize_greedy(incidents, crews, time_horizon_hours)

        # =============================================
        # EXTRAER SOLUCIÓN
        # =============================================
        recommendations = []
        assigned_incidents = set()

        for i, incident in enumerate(incidents):
            for j, crew in enumerate(crews):
                if x[i, j].solution_value() > 0.5:
                    # Encontrar alternativas
                    alternatives = self._find_alternatives(incident, crews, j, compatibility[i], travel_times[i])

                    rec = DispatchRecommendation(
                        incident_id=incident.id,
                        incident_summary={
                            'address': incident.address_text,
                            'risk_score': incident.risk_score,
                            'severity': incident.severity_estimate.value,
                            'type': incident.incident_type.value
                        },
                        recommended_crew={
                            'crew_id': crew.id,
                            'crew_name': crew.name,
                            'authority_id': crew.authority_id,
                            'current_location': crew.location.to_dict(),
                            'eta_minutes': int(travel_times[i][j]),
                            'compatibility_score': 1.0 if compatibility[i][j] else 0.0
                        },
                        alternative_crews=alternatives,
                        optimizer_reasoning={
                            'risk_score_contribution': incident.risk_score,
                            'sla_urgency_factor': SLAUrgencyCalculator.compute_urgency(incident),
                            'travel_time_penalty': round(travel_times[i][j] * 0.5, 2),
                            'net_benefit': round(benefits[i][j] - travel_times[i][j] * 0.5, 2),
                            'explanation': self._generate_explanation(incident, crew, travel_times[i][j])
                        },
                        final_score=benefits[i][j]
                    )
                    recommendations.append(rec)
                    assigned_incidents.add(incident.id)
                    break

        # Incidentes no asignados
        unassignable = []
        for incident in incidents:
            if incident.id not in assigned_incidents:
                reason = self._determine_unassignable_reason(incident, crews, compatibility)
                unassignable.append({
                    'incident_id': incident.id,
                    'reason': reason,
                    'details': f"Incidente en {incident.address_text}"
                })

        # Ordenar por score
        recommendations.sort(key=lambda r: r.final_score, reverse=True)
        for rank, rec in enumerate(recommendations):
            rec.optimizer_reasoning['priority_rank'] = rank + 1

        return DispatchPlan(
            recommendations=recommendations,
            unassignable=unassignable,
            solver_status='optimal' if status == pywraplp.Solver.OPTIMAL else 'feasible',
            solve_time_ms=0,  # Se actualiza después
            total_processed=len(incidents),
            total_assigned=len(recommendations),
            objective_value=solver.Objective().Value()
        )

    def _optimize_greedy(
        self,
        incidents: List[Incident],
        crews: List[Crew],
        time_horizon_hours: int
    ) -> DispatchPlan:
        """
        Optimización greedy cuando OR-Tools no está disponible.
        Asigna incidentes en orden de riesgo a la cuadrilla más cercana compatible.
        """
        # Ordenar incidentes por score de riesgo (mayor primero)
        sorted_incidents = sorted(incidents, key=lambda i: (
            i.severity_estimate == Severity.CRITICAL,
            i.risk_score,
            SLAUrgencyCalculator.compute_urgency(i)
        ), reverse=True)

        # Track de asignaciones por cuadrilla
        crew_assignments = {c.id: 0 for c in crews}
        recommendations = []
        assigned_incidents = set()

        for incident in sorted_incidents:
            best_crew = None
            best_travel = float('inf')
            best_score = -float('inf')

            for crew in crews:
                # Verificar si puede aceptar más asignaciones
                remaining = self.max_assignments_per_crew - crew.today_assignments - crew_assignments[crew.id]
                if remaining <= 0:
                    continue

                # Verificar compatibilidad
                if not self._check_compatibility(incident, crew):
                    continue

                # Calcular tiempo de viaje
                travel_time = crew.travel_time_to(incident.location)

                # Verificar que no exceda turno
                if travel_time > crew.get_remaining_shift_hours() * 60:
                    continue

                # Calcular score
                benefit = self._compute_benefit(incident, crew)
                score = benefit - (travel_time * 0.5)

                if score > best_score:
                    best_score = score
                    best_crew = crew
                    best_travel = travel_time

            if best_crew:
                # Encontrar alternativas
                alternatives = []
                for crew in crews:
                    if crew.id != best_crew.id and self._check_compatibility(incident, crew):
                        travel = crew.travel_time_to(incident.location)
                        if travel < best_crew.get_remaining_shift_hours() * 60:
                            alternatives.append({
                                'crew_id': crew.id,
                                'crew_name': crew.name,
                                'eta_minutes': int(travel),
                                'not_recommended_reason': 'Mayor tiempo de viaje' if travel > best_travel else 'Menor capacidad'
                            })
                alternatives = alternatives[:3]  # Top 3

                rec = DispatchRecommendation(
                    incident_id=incident.id,
                    incident_summary={
                        'address': incident.address_text,
                        'risk_score': incident.risk_score,
                        'severity': incident.severity_estimate.value,
                        'type': incident.incident_type.value
                    },
                    recommended_crew={
                        'crew_id': best_crew.id,
                        'crew_name': best_crew.name,
                        'authority_id': best_crew.authority_id,
                        'current_location': best_crew.location.to_dict(),
                        'eta_minutes': int(best_travel),
                        'compatibility_score': 1.0
                    },
                    alternative_crews=alternatives,
                    optimizer_reasoning={
                        'risk_score_contribution': incident.risk_score,
                        'sla_urgency_factor': SLAUrgencyCalculator.compute_urgency(incident),
                        'travel_time_penalty': round(best_travel * 0.5, 2),
                        'explanation': self._generate_explanation(incident, best_crew, best_travel)
                    },
                    final_score=best_score
                )
                recommendations.append(rec)
                assigned_incidents.add(incident.id)
                crew_assignments[best_crew.id] += 1

        # Incidentes no asignados
        unassignable = []
        for incident in incidents:
            if incident.id not in assigned_incidents:
                unassignable.append({
                    'incident_id': incident.id,
                    'reason': 'no_compatible_crew_available',
                    'details': f"No hay cuadrilla disponible compatible para {incident.address_text}"
                })

        # Asignar ranking
        for rank, rec in enumerate(recommendations):
            rec.optimizer_reasoning['priority_rank'] = rank + 1

        return DispatchPlan(
            recommendations=recommendations,
            unassignable=unassignable,
            solver_status='greedy_heuristic',
            solve_time_ms=0,
            total_processed=len(incidents),
            total_assigned=len(recommendations),
            objective_value=sum(r.final_score for r in recommendations)
        )

    def _compute_compatibility(self, incidents: List[Incident], crews: List[Crew]) -> List[List[bool]]:
        """Matriz de compatibilidad incidente x cuadrilla"""
        return [
            [self._check_compatibility(inc, crew) for crew in crews]
            for inc in incidents
        ]

    def _check_compatibility(self, incident: Incident, crew: Crew) -> bool:
        """Verifica si una cuadrilla puede atender un incidente"""
        # Por ahora, todas las cuadrillas tipo pothole_repair pueden atender baches
        # En producción, esto verificaría capacidades específicas
        if incident.incident_type.value in ('pothole', 'crack'):
            return 'bacheo' in crew.capabilities or crew.crew_type == 'pothole_repair'
        if incident.incident_type.value == 'signage':
            return 'señalización' in crew.capabilities or crew.crew_type == 'signage'
        return True  # General maintenance puede todo

    def _compute_travel_times(self, incidents: List[Incident], crews: List[Crew]) -> List[List[float]]:
        """Matriz de tiempos de viaje en minutos"""
        return [
            [crew.travel_time_to(inc.location) for crew in crews]
            for inc in incidents
        ]

    def _compute_benefits(self, incidents: List[Incident], crews: List[Crew]) -> List[List[float]]:
        """Matriz de beneficios de asignar crew j a incident i"""
        return [
            [self._compute_benefit(inc, crew) for crew in crews]
            for inc in incidents
        ]

    def _compute_benefit(self, incident: Incident, crew: Crew) -> float:
        """Beneficio de asignar una cuadrilla a un incidente"""
        base = incident.risk_score
        urgency = SLAUrgencyCalculator.compute_urgency(incident)
        return base * urgency

    def _find_alternatives(
        self,
        incident: Incident,
        crews: List[Crew],
        selected_idx: int,
        compatibility_row: List[bool],
        travel_times_row: List[float]
    ) -> List[Dict]:
        """Encuentra cuadrillas alternativas"""
        alternatives = []
        selected_travel = travel_times_row[selected_idx]

        for j, crew in enumerate(crews):
            if j == selected_idx or not compatibility_row[j]:
                continue

            travel = travel_times_row[j]
            reason = "Mayor tiempo de viaje" if travel > selected_travel else "Menor disponibilidad"

            alternatives.append({
                'crew_id': crew.id,
                'crew_name': crew.name,
                'eta_minutes': int(travel),
                'not_recommended_reason': reason
            })

        # Ordenar por ETA y tomar top 3
        alternatives.sort(key=lambda a: a['eta_minutes'])
        return alternatives[:3]

    def _generate_explanation(self, incident: Incident, crew: Crew, travel_minutes: float) -> str:
        """Genera explicación en lenguaje natural"""
        parts = []

        if incident.severity_estimate == Severity.CRITICAL:
            parts.append("Incidente CRÍTICO - prioridad máxima")
        elif incident.severity_estimate == Severity.HIGH:
            parts.append("Alta prioridad por severidad elevada")

        urgency = SLAUrgencyCalculator.compute_urgency(incident)
        if urgency > 2.5:
            parts.append("SLA en riesgo inminente")
        elif urgency > 2.0:
            parts.append("Proximidad a vencimiento de SLA")

        parts.append(f"ETA: {int(travel_minutes)} min")
        parts.append(f"Cuadrilla más cercana compatible: {crew.name}")

        return " | ".join(parts)

    def _determine_unassignable_reason(
        self,
        incident: Incident,
        crews: List[Crew],
        compatibility: List[List[bool]]
    ) -> str:
        """Determina por qué un incidente no pudo ser asignado"""
        incident_idx = None
        for i, inc in enumerate(compatibility):
            if any(inc):
                continue
            return 'no_compatible_crew'

        any_available = any(c.can_accept_assignment() for c in crews)
        if not any_available:
            return 'all_crews_busy'

        return 'constraint_conflict'


def create_assignment_from_recommendation(
    rec: DispatchRecommendation,
    incident: Incident,
    crew: Crew
) -> Assignment:
    """Crea un Assignment a partir de una recomendación del optimizador"""
    return Assignment(
        id=generate_id(),
        incident_id=rec.incident_id,
        crew_id=rec.recommended_crew['crew_id'],
        authority_id=rec.recommended_crew['authority_id'],
        status=AssignmentStatus.PENDING,
        priority_rank=rec.optimizer_reasoning.get('priority_rank', 0),
        optimizer_score=rec.final_score,
        optimizer_reasoning=rec.optimizer_reasoning,
        eta_minutes=rec.recommended_crew['eta_minutes'],
        estimated_cost=45000  # Costo promedio estimado ARS
    )


# Singleton
_optimizer = None

def get_optimizer() -> DispatchOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = DispatchOptimizer()
    return _optimizer
