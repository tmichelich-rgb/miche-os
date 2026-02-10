"""
CityOps Vial - Risk Scoring Engine
Calcula el score de riesgo interpretable para cada incidente
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from models import (
    Incident, IncidentType, Severity, Location, RoadSegment
)

class RiskScoringEngine:
    """
    Motor de scoring de riesgo basado en múltiples factores.

    RiskScore = w1·TrafficFactor + w2·SpeedFactor + w3·SeverityFactor +
                w4·RecurrenceFactor + w5·AgeUrgencyFactor + w6·ReportCountFactor

    Score ∈ [0, 100]
    """

    def __init__(self):
        # Pesos configurables
        self.weights = {
            'traffic': 0.20,
            'speed': 0.15,
            'severity': 0.25,
            'recurrence': 0.15,
            'age_urgency': 0.15,
            'report_count': 0.10
        }

        # Valores de severidad
        self.severity_scores = {
            Severity.LOW: 20,
            Severity.MEDIUM: 45,
            Severity.HIGH: 75,
            Severity.CRITICAL: 100
        }

        # Historial de incidentes por zona (para recurrencia)
        self.incident_history: Dict[str, List[datetime]] = {}

    def compute_risk_score(
        self,
        incident: Incident,
        road_segment: Optional[RoadSegment] = None,
        nearby_incidents_90d: int = 0
    ) -> Dict:
        """
        Calcula el score de riesgo y devuelve breakdown detallado.
        """

        factors = {}

        # =============================================
        # F1: Traffic Factor (AADT normalizado)
        # =============================================
        if road_segment and road_segment.aadt:
            # Normalizar AADT entre 0-100 (asumiendo max 150,000)
            traffic_factor = min(100, (road_segment.aadt / 150000) * 100)
        else:
            # Default para calles urbanas sin dato
            traffic_factor = 40

        factors['traffic'] = {
            'value': round(traffic_factor, 1),
            'weight': self.weights['traffic'],
            'contribution': round(traffic_factor * self.weights['traffic'], 2),
            'description': f"TMDA: {road_segment.aadt if road_segment else 'N/A'}"
        }

        # =============================================
        # F2: Speed Factor (límite de velocidad)
        # =============================================
        if road_segment and road_segment.speed_limit_kmh:
            # Normalizar velocidad entre 30-130 km/h
            speed = road_segment.speed_limit_kmh
            speed_factor = min(100, max(0, ((speed - 30) / 100) * 100))
        else:
            speed_factor = 40  # Default urbano

        factors['speed'] = {
            'value': round(speed_factor, 1),
            'weight': self.weights['speed'],
            'contribution': round(speed_factor * self.weights['speed'], 2),
            'description': f"Límite: {road_segment.speed_limit_kmh if road_segment else 'N/A'} km/h"
        }

        # =============================================
        # F3: Severity Factor
        # =============================================
        severity_factor = self.severity_scores.get(incident.severity_estimate, 50)

        factors['severity'] = {
            'value': severity_factor,
            'weight': self.weights['severity'],
            'contribution': round(severity_factor * self.weights['severity'], 2),
            'description': f"Severidad estimada: {incident.severity_estimate.value}"
        }

        # =============================================
        # F4: Recurrence Factor (historial de zona)
        # =============================================
        # Mayor score si hay incidentes recurrentes en la zona
        recurrence_factor = min(100, nearby_incidents_90d * 15)

        factors['recurrence'] = {
            'value': recurrence_factor,
            'weight': self.weights['recurrence'],
            'contribution': round(recurrence_factor * self.weights['recurrence'], 2),
            'description': f"{nearby_incidents_90d} incidentes previos en 90 días"
        }

        # =============================================
        # F5: Age/Urgency Factor
        # =============================================
        # Mayor score cuanto más tiempo lleva sin resolver
        age_hours = incident.get_age_hours()
        if age_hours < 2:
            age_factor = 20
        elif age_hours < 8:
            age_factor = 40
        elif age_hours < 24:
            age_factor = 60
        elif age_hours < 48:
            age_factor = 80
        else:
            age_factor = 100

        factors['age_urgency'] = {
            'value': age_factor,
            'weight': self.weights['age_urgency'],
            'contribution': round(age_factor * self.weights['age_urgency'], 2),
            'description': f"Antigüedad: {age_hours:.1f} horas"
        }

        # =============================================
        # F6: Report Count Factor
        # =============================================
        # Más reportes = mayor confianza y urgencia
        report_factor = min(100, incident.report_count * 12)

        factors['report_count'] = {
            'value': report_factor,
            'weight': self.weights['report_count'],
            'contribution': round(report_factor * self.weights['report_count'], 2),
            'description': f"{incident.report_count} reportes recibidos"
        }

        # =============================================
        # CÁLCULO FINAL
        # =============================================
        total_score = sum(f['contribution'] for f in factors.values())

        # Ajuste por confianza
        confidence_adjusted_score = total_score * incident.confidence_score

        return {
            'risk_score': round(min(100, max(0, confidence_adjusted_score)), 1),
            'raw_score': round(total_score, 1),
            'confidence_factor': incident.confidence_score,
            'factors': factors,
            'risk_level': self._get_risk_level(confidence_adjusted_score),
            'computed_at': datetime.now().isoformat()
        }

    def _get_risk_level(self, score: float) -> str:
        if score >= 75:
            return 'critical'
        elif score >= 55:
            return 'high'
        elif score >= 35:
            return 'medium'
        else:
            return 'low'

    def estimate_severity(self, incident: Incident) -> Severity:
        """
        Estima severidad basada en descripción y tipo de incidente.
        En producción, esto podría usar ML.
        """
        description = ""
        if incident.source_reports:
            description = " ".join(r.description.lower() for r in incident.source_reports)

        # Keywords de severidad
        critical_keywords = ['enorme', 'gigante', 'accidente', 'peligroso', 'emergencia', 'hundimiento']
        high_keywords = ['grande', 'profundo', 'importante', 'serio', 'urgente']
        medium_keywords = ['mediano', 'regular', 'moderado']

        if any(kw in description for kw in critical_keywords):
            return Severity.CRITICAL
        elif any(kw in description for kw in high_keywords):
            return Severity.HIGH
        elif any(kw in description for kw in medium_keywords):
            return Severity.MEDIUM

        # Default por tipo de incidente
        type_severity = {
            IncidentType.POTHOLE: Severity.MEDIUM,
            IncidentType.CRACK: Severity.LOW,
            IncidentType.DEBRIS: Severity.HIGH,
            IncidentType.FLOODING: Severity.CRITICAL,
            IncidentType.SIGNAGE: Severity.LOW,
        }

        return type_severity.get(incident.incident_type, Severity.MEDIUM)

    def compute_confidence(self, incident: Incident) -> float:
        """
        Calcula score de confianza basado en:
        - Cantidad de reportes
        - Diversidad de fuentes
        - Confiabilidad de reportantes
        - Precisión de ubicación
        """
        confidence = 0.3  # Base

        # Más reportes = más confianza
        if incident.report_count >= 5:
            confidence += 0.3
        elif incident.report_count >= 3:
            confidence += 0.2
        elif incident.report_count >= 2:
            confidence += 0.1

        # Promedio de confiabilidad de reportantes
        if incident.source_reports:
            avg_reliability = sum(r.reliability_score for r in incident.source_reports) / len(incident.source_reports)
            confidence += avg_reliability * 0.2

        # Precisión de ubicación
        if incident.location.accuracy_m < 10:
            confidence += 0.15
        elif incident.location.accuracy_m < 30:
            confidence += 0.1

        # Evidencia fotográfica
        has_photo = any(r.media_urls for r in incident.source_reports)
        if has_photo:
            confidence += 0.1

        return min(1.0, confidence)


class SLAUrgencyCalculator:
    """
    Calcula el factor de urgencia basado en proximidad al deadline SLA.
    """

    @staticmethod
    def compute_urgency(incident: Incident) -> float:
        """
        Returns valor entre 1.0 (sin urgencia) y 3.0 (máxima urgencia/vencido)
        """
        if not incident.sla_deadline:
            return 1.0

        now = datetime.now()
        time_remaining = (incident.sla_deadline - now).total_seconds() / 3600  # horas

        if time_remaining <= 0:
            return 3.0  # Ya vencido

        # Asumir SLA total de 24h si no tenemos el dato
        # Calcular qué % del tiempo ha pasado
        age = incident.get_age_hours()
        total_sla = age + time_remaining

        if total_sla <= 0:
            return 3.0

        urgency = 1 + max(0, (1 - time_remaining / total_sla)) * 2
        return min(3.0, urgency)

    @staticmethod
    def get_sla_status_details(incident: Incident) -> Dict:
        """Detalles del estado de SLA"""
        if not incident.sla_deadline:
            return {
                'status': 'unknown',
                'deadline': None,
                'remaining_hours': None,
                'percentage_used': None
            }

        now = datetime.now()
        remaining = (incident.sla_deadline - now).total_seconds() / 3600
        age = incident.get_age_hours()
        total = age + max(0, remaining)
        percentage_used = (age / total * 100) if total > 0 else 100

        if incident.status.value in ('resolved', 'closed'):
            status = 'met' if incident.resolved_at and incident.resolved_at <= incident.sla_deadline else 'breached'
        elif remaining <= 0:
            status = 'breached'
        elif remaining < 2:
            status = 'at_risk'
        else:
            status = 'on_track'

        return {
            'status': status,
            'deadline': incident.sla_deadline.isoformat(),
            'remaining_hours': round(max(0, remaining), 1),
            'percentage_used': round(percentage_used, 1),
            'urgency_factor': SLAUrgencyCalculator.compute_urgency(incident)
        }


# Singleton
_scoring_engine = None

def get_scoring_engine() -> RiskScoringEngine:
    global _scoring_engine
    if _scoring_engine is None:
        _scoring_engine = RiskScoringEngine()
    return _scoring_engine
