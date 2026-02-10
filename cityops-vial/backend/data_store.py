"""
CityOps Vial - In-Memory Data Store
Almacenamiento en memoria para MVP (en producción sería PostgreSQL + PostGIS)
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import random
import uuid

from models import (
    Incident, Crew, Assignment, Evidence, AuditEntry, SourceReport, Location,
    IncidentStatus, IncidentType, Severity, CrewStatus, AssignmentStatus, SourceType,
    generate_id, generate_tracking_code, KPIMetrics
)
from jurisdiction_engine import get_jurisdiction_engine
from scoring_engine import get_scoring_engine, SLAUrgencyCalculator


class DataStore:
    """
    Almacenamiento en memoria con datos demo de CABA/GBA.
    """

    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.crews: Dict[str, Crew] = {}
        self.assignments: Dict[str, Assignment] = {}
        self.evidence: Dict[str, Evidence] = {}
        self.audit_log: List[AuditEntry] = []

        self._load_demo_data()

    def _load_demo_data(self):
        """Carga datos demo para CABA y GBA"""
        self._create_demo_crews()
        self._create_demo_incidents()

    def _create_demo_crews(self):
        """Crea cuadrillas demo"""
        crews_data = [
            # CABA - GCBA
            ("crew-gcba-1", "Cuadrilla Centro 1", "auth-gcba-transporte", -34.6037, -58.3816, "pothole_repair"),
            ("crew-gcba-2", "Cuadrilla Centro 2", "auth-gcba-transporte", -34.6158, -58.4333, "pothole_repair"),
            ("crew-gcba-3", "Cuadrilla Norte", "auth-gcba-transporte", -34.5741, -58.4277, "pothole_repair"),
            ("crew-gcba-4", "Cuadrilla Sur", "auth-gcba-transporte", -34.6500, -58.3900, "pothole_repair"),
            ("crew-gcba-5", "Cuadrilla Señalización", "auth-gcba-transporte", -34.6200, -58.4000, "signage"),

            # CABA - AUSA (Autopistas)
            ("crew-ausa-1", "Cuadrilla AUSA Norte", "auth-ausa", -34.6100, -58.4200, "pothole_repair"),
            ("crew-ausa-2", "Cuadrilla AUSA Sur", "auth-ausa", -34.6400, -58.4100, "pothole_repair"),

            # GBA - AUBASA
            ("crew-aubasa-1", "Cuadrilla BA-LP Km 20", "auth-aubasa", -34.7200, -58.2800, "pothole_repair"),
            ("crew-aubasa-2", "Cuadrilla BA-LP Km 40", "auth-aubasa", -34.8200, -58.1500, "pothole_repair"),
            ("crew-aubasa-3", "Cuadrilla Acceso Oeste", "auth-aubasa", -34.6300, -58.6000, "pothole_repair"),

            # Municipios GBA
            ("crew-ave-1", "Cuadrilla Avellaneda", "auth-ave", -34.6600, -58.3600, "pothole_repair"),
            ("crew-lan-1", "Cuadrilla Lanús", "auth-lan", -34.7100, -58.3900, "pothole_repair"),
            ("crew-qui-1", "Cuadrilla Quilmes", "auth-qui", -34.7200, -58.2500, "pothole_repair"),
        ]

        for crew_id, name, auth_id, lat, lon, crew_type in crews_data:
            crew = Crew(
                id=crew_id,
                authority_id=auth_id,
                name=name,
                crew_type=crew_type,
                status=CrewStatus.AVAILABLE,
                location=Location(lat, lon),
                member_count=random.randint(3, 6),
                capabilities=["bacheo", "reparación_menor"] if crew_type == "pothole_repair" else ["señalización"],
                today_assignments=random.randint(0, 2),
                location_updated_at=datetime.now()
            )
            self.crews[crew_id] = crew

    def _create_demo_incidents(self):
        """Crea incidentes demo distribuidos en CABA/GBA"""
        jur_engine = get_jurisdiction_engine()
        scoring_engine = get_scoring_engine()

        # Ubicaciones de incidentes demo en CABA y GBA
        incident_locations = [
            # CABA - Centro
            (-34.6037, -58.3816, "Av. Corrientes 1200, CABA", IncidentType.POTHOLE, Severity.HIGH),
            (-34.6083, -58.3772, "Av. 9 de Julio 800, CABA", IncidentType.POTHOLE, Severity.CRITICAL),
            (-34.6118, -58.4173, "Av. Rivadavia 4500, CABA", IncidentType.CRACK, Severity.MEDIUM),
            (-34.5875, -58.3974, "Av. Santa Fe 3200, CABA", IncidentType.POTHOLE, Severity.HIGH),
            (-34.6200, -58.3650, "Av. Belgrano 1800, CABA", IncidentType.DEBRIS, Severity.MEDIUM),

            # CABA - Zona Sur
            (-34.6450, -58.3850, "Av. Caseros 2500, CABA", IncidentType.POTHOLE, Severity.MEDIUM),
            (-34.6380, -58.3700, "Av. Montes de Oca 1200, CABA", IncidentType.POTHOLE, Severity.LOW),

            # CABA - Autopistas
            (-34.6250, -58.4100, "Autopista 25 de Mayo km 3", IncidentType.POTHOLE, Severity.CRITICAL),
            (-34.6320, -58.4500, "Autopista Perito Moreno km 5", IncidentType.CRACK, Severity.HIGH),

            # GBA - Autopista BA-La Plata
            (-34.7000, -58.3200, "Autopista BA-LP km 12", IncidentType.POTHOLE, Severity.HIGH),
            (-34.7800, -58.2000, "Autopista BA-LP km 28", IncidentType.POTHOLE, Severity.MEDIUM),
            (-34.8500, -58.0800, "Autopista BA-LP km 45", IncidentType.DEBRIS, Severity.CRITICAL),

            # GBA - Municipios
            (-34.6650, -58.3500, "Av. Mitre 800, Avellaneda", IncidentType.POTHOLE, Severity.MEDIUM),
            (-34.7050, -58.3950, "Av. H. Yrigoyen 2300, Lanús", IncidentType.POTHOLE, Severity.HIGH),
            (-34.7150, -58.2600, "Av. Calchaquí 500, Quilmes", IncidentType.CRACK, Severity.LOW),
        ]

        base_time = datetime.now()

        for i, (lat, lon, address, inc_type, severity) in enumerate(incident_locations):
            # Variar tiempos de reporte
            hours_ago = random.uniform(0.5, 48)
            first_reported = base_time - timedelta(hours=hours_ago)

            location = Location(lat, lon, accuracy_m=random.uniform(5, 30))

            # Determinar jurisdicción
            jur, auth, segment = jur_engine.determine_responsibility(location)

            # Crear source reports
            report_count = random.randint(1, 8)
            source_reports = []
            for r in range(report_count):
                report_time = first_reported + timedelta(minutes=random.uniform(0, 60 * hours_ago * 0.8))
                source_reports.append(SourceReport(
                    id=generate_id(),
                    source_type=SourceType.CITIZEN_APP,
                    location=location,
                    reported_at=report_time,
                    description=f"Bache {'grande' if severity in (Severity.HIGH, Severity.CRITICAL) else 'mediano'} en la vía",
                    reliability_score=random.uniform(0.5, 0.9)
                ))

            incident = Incident(
                id=generate_id(),
                status=random.choice([IncidentStatus.NEW, IncidentStatus.VALIDATED, IncidentStatus.ASSIGNED]),
                location=location,
                incident_type=inc_type,
                severity_estimate=severity,
                report_count=report_count,
                first_reported_at=first_reported,
                last_reported_at=max(r.reported_at for r in source_reports),
                jurisdiction_id=jur.id if jur else None,
                authority_id=auth.id if auth else None,
                road_segment_id=segment.id if segment else None,
                address_text=address,
                source_reports=source_reports,
                created_at=first_reported
            )

            # Calcular confianza y risk score
            incident.confidence_score = scoring_engine.compute_confidence(incident)
            risk_result = scoring_engine.compute_risk_score(incident, segment, random.randint(0, 3))
            incident.risk_score = risk_result['risk_score']

            # Calcular SLA
            if jur:
                response_h, resolution_h = jur_engine.get_sla_for_incident(incident)
                incident.sla_deadline = incident.first_reported_at + timedelta(hours=resolution_h)

            # Crear asignación para algunos
            if incident.status == IncidentStatus.ASSIGNED:
                # Encontrar cuadrilla de la misma autoridad
                matching_crews = [c for c in self.crews.values() if c.authority_id == incident.authority_id]
                if matching_crews:
                    crew = random.choice(matching_crews)
                    assignment = Assignment(
                        id=generate_id(),
                        incident_id=incident.id,
                        crew_id=crew.id,
                        authority_id=crew.authority_id,
                        status=random.choice([AssignmentStatus.PENDING, AssignmentStatus.EN_ROUTE]),
                        priority_rank=i + 1,
                        optimizer_score=incident.risk_score,
                        eta_minutes=int(crew.travel_time_to(incident.location)),
                        estimated_cost=random.randint(30000, 80000)
                    )
                    self.assignments[assignment.id] = assignment
                    incident.current_assignment_id = assignment.id

            self.incidents[incident.id] = incident

    # =============================================
    # INCIDENT OPERATIONS
    # =============================================

    def create_incident(self, data: dict) -> Incident:
        """Crea un nuevo incidente desde un reporte ciudadano"""
        jur_engine = get_jurisdiction_engine()
        scoring_engine = get_scoring_engine()

        location = Location(
            data['location']['lat'],
            data['location']['lon'],
            data['location'].get('accuracy_m', 10)
        )

        # Determinar jurisdicción
        jur, auth, segment = jur_engine.determine_responsibility(location)

        # Crear source report
        source_report = SourceReport(
            id=generate_id(),
            source_type=SourceType.CITIZEN_APP,
            location=location,
            reported_at=datetime.now(),
            description=data.get('description', ''),
            media_urls=data.get('media_urls', []),
            reporter_id=data.get('reporter_id', ''),
            reliability_score=0.5  # Nuevo usuario, confianza base
        )

        # Verificar si existe incidente cercano (deduplicación simple)
        existing = self._find_nearby_incident(location, max_distance_km=0.1)
        if existing:
            # Agregar reporte al incidente existente
            existing.source_reports.append(source_report)
            existing.report_count += 1
            existing.last_reported_at = datetime.now()
            existing.confidence_score = scoring_engine.compute_confidence(existing)
            risk_result = scoring_engine.compute_risk_score(existing, segment)
            existing.risk_score = risk_result['risk_score']
            existing.updated_at = datetime.now()
            self._log_audit('incident', existing.id, 'report_added', 'api', data.get('reporter_id', 'anonymous'))
            return existing

        # Crear nuevo incidente
        incident_type = IncidentType(data.get('incident_type', 'pothole'))
        incident = Incident(
            id=generate_id(),
            status=IncidentStatus.NEW,
            location=location,
            incident_type=incident_type,
            source_reports=[source_report],
            jurisdiction_id=jur.id if jur else None,
            authority_id=auth.id if auth else None,
            road_segment_id=segment.id if segment else None,
            address_text=data.get('address', f"Lat: {location.lat:.4f}, Lon: {location.lon:.4f}")
        )

        # Calcular severidad, confianza y riesgo
        incident.severity_estimate = scoring_engine.estimate_severity(incident)
        incident.confidence_score = scoring_engine.compute_confidence(incident)
        risk_result = scoring_engine.compute_risk_score(incident, segment)
        incident.risk_score = risk_result['risk_score']

        # Calcular SLA
        if jur:
            response_h, resolution_h = jur_engine.get_sla_for_incident(incident)
            incident.sla_deadline = incident.first_reported_at + timedelta(hours=resolution_h)

        self.incidents[incident.id] = incident
        self._log_audit('incident', incident.id, 'create', 'api', data.get('reporter_id', 'anonymous'))

        return incident

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self.incidents.get(incident_id)

    def get_incidents(
        self,
        status: List[str] = None,
        jurisdiction_id: str = None,
        authority_id: str = None,
        severity: List[str] = None,
        min_risk_score: float = None,
        bbox: tuple = None,
        limit: int = 100
    ) -> List[Incident]:
        """Obtiene incidentes con filtros"""
        results = list(self.incidents.values())

        if status:
            results = [i for i in results if i.status.value in status]
        if jurisdiction_id:
            results = [i for i in results if i.jurisdiction_id == jurisdiction_id]
        if authority_id:
            results = [i for i in results if i.authority_id == authority_id]
        if severity:
            results = [i for i in results if i.severity_estimate.value in severity]
        if min_risk_score is not None:
            results = [i for i in results if i.risk_score >= min_risk_score]
        if bbox:
            min_lon, min_lat, max_lon, max_lat = bbox
            results = [i for i in results if min_lon <= i.location.lon <= max_lon and min_lat <= i.location.lat <= max_lat]

        # Ordenar por risk_score desc
        results.sort(key=lambda i: i.risk_score, reverse=True)

        return results[:limit]

    def update_incident(self, incident_id: str, updates: dict) -> Optional[Incident]:
        """Actualiza un incidente"""
        incident = self.incidents.get(incident_id)
        if not incident:
            return None

        old_status = incident.status.value

        for key, value in updates.items():
            if key == 'status':
                incident.status = IncidentStatus(value)
                if value == 'resolved':
                    incident.resolved_at = datetime.now()
                elif value == 'closed':
                    incident.closed_at = datetime.now()
            elif hasattr(incident, key):
                setattr(incident, key, value)

        incident.updated_at = datetime.now()

        self._log_audit('incident', incident_id, 'update', 'api', 'system', {
            'old_status': old_status,
            'new_status': incident.status.value,
            'updates': updates
        })

        return incident

    def _find_nearby_incident(self, location: Location, max_distance_km: float = 0.1) -> Optional[Incident]:
        """Busca incidente cercano para deduplicación"""
        for incident in self.incidents.values():
            if incident.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.REJECTED):
                dist = location.distance_to(incident.location)
                if dist <= max_distance_km:
                    return incident
        return None

    # =============================================
    # CREW OPERATIONS
    # =============================================

    def get_crew(self, crew_id: str) -> Optional[Crew]:
        return self.crews.get(crew_id)

    def get_crews(
        self,
        authority_id: str = None,
        status: List[str] = None,
        available_only: bool = False
    ) -> List[Crew]:
        results = list(self.crews.values())

        if authority_id:
            results = [c for c in results if c.authority_id == authority_id]
        if status:
            results = [c for c in results if c.status.value in status]
        if available_only:
            results = [c for c in results if c.can_accept_assignment()]

        return results

    def update_crew_location(self, crew_id: str, lat: float, lon: float) -> Optional[Crew]:
        crew = self.crews.get(crew_id)
        if crew:
            crew.location = Location(lat, lon)
            crew.location_updated_at = datetime.now()
        return crew

    def update_crew_status(self, crew_id: str, status: str) -> Optional[Crew]:
        crew = self.crews.get(crew_id)
        if crew:
            crew.status = CrewStatus(status)
        return crew

    # =============================================
    # ASSIGNMENT OPERATIONS
    # =============================================

    def create_assignment(self, incident_id: str, crew_id: str, optimizer_data: dict = None) -> Optional[Assignment]:
        """Crea una asignación"""
        incident = self.incidents.get(incident_id)
        crew = self.crews.get(crew_id)

        if not incident or not crew:
            return None

        assignment = Assignment(
            id=generate_id(),
            incident_id=incident_id,
            crew_id=crew_id,
            authority_id=crew.authority_id,
            status=AssignmentStatus.PENDING,
            eta_minutes=int(crew.travel_time_to(incident.location)),
            optimizer_score=optimizer_data.get('score', 0) if optimizer_data else 0,
            optimizer_reasoning=optimizer_data.get('reasoning', {}) if optimizer_data else {},
            estimated_cost=45000
        )

        self.assignments[assignment.id] = assignment

        # Actualizar incidente
        incident.current_assignment_id = assignment.id
        incident.status = IncidentStatus.ASSIGNED
        incident.updated_at = datetime.now()

        # Actualizar cuadrilla
        crew.status = CrewStatus.ASSIGNED
        crew.today_assignments += 1

        self._log_audit('assignment', assignment.id, 'create', 'system', 'optimizer')

        return assignment

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        return self.assignments.get(assignment_id)

    def get_assignments(
        self,
        incident_id: str = None,
        crew_id: str = None,
        status: List[str] = None
    ) -> List[Assignment]:
        results = list(self.assignments.values())

        if incident_id:
            results = [a for a in results if a.incident_id == incident_id]
        if crew_id:
            results = [a for a in results if a.crew_id == crew_id]
        if status:
            results = [a for a in results if a.status.value in status]

        return results

    def update_assignment(self, assignment_id: str, updates: dict) -> Optional[Assignment]:
        assignment = self.assignments.get(assignment_id)
        if not assignment:
            return None

        for key, value in updates.items():
            if key == 'status':
                assignment.status = AssignmentStatus(value)
                if value == 'en_route':
                    assignment.accepted_at = datetime.now()
                    # Actualizar crew
                    crew = self.crews.get(assignment.crew_id)
                    if crew:
                        crew.status = CrewStatus.EN_ROUTE
                elif value == 'on_site':
                    assignment.actual_arrival_at = datetime.now()
                    crew = self.crews.get(assignment.crew_id)
                    if crew:
                        crew.status = CrewStatus.WORKING
                    # Actualizar incidente
                    incident = self.incidents.get(assignment.incident_id)
                    if incident:
                        incident.status = IncidentStatus.IN_PROGRESS
                elif value == 'completed':
                    assignment.work_completed_at = datetime.now()
                    # Actualizar crew
                    crew = self.crews.get(assignment.crew_id)
                    if crew:
                        crew.status = CrewStatus.AVAILABLE
                    # Actualizar incidente
                    incident = self.incidents.get(assignment.incident_id)
                    if incident:
                        incident.status = IncidentStatus.RESOLVED
                        incident.resolved_at = datetime.now()
            elif hasattr(assignment, key):
                setattr(assignment, key, value)

        self._log_audit('assignment', assignment_id, 'update', 'api', 'crew', updates)

        return assignment

    # =============================================
    # KPI CALCULATIONS
    # =============================================

    def compute_kpis(self, from_date: datetime = None, to_date: datetime = None) -> KPIMetrics:
        """Calcula KPIs para el período especificado"""
        if not to_date:
            to_date = datetime.now()
        if not from_date:
            from_date = to_date - timedelta(days=7)

        # Filtrar incidentes del período
        period_incidents = [
            i for i in self.incidents.values()
            if i.created_at and from_date <= i.created_at <= to_date
        ]

        resolved = [i for i in period_incidents if i.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)]

        kpis = KPIMetrics(
            period_start=from_date,
            period_end=to_date,
            total_incidents=len(period_incidents),
            total_resolved=len(resolved),
            resolution_rate=len(resolved) / len(period_incidents) if period_incidents else 0
        )

        # Tiempos promedio
        resolution_times = []
        for i in resolved:
            if i.resolved_at and i.first_reported_at:
                hours = (i.resolved_at - i.first_reported_at).total_seconds() / 3600
                resolution_times.append(hours)

        if resolution_times:
            kpis.avg_total_resolution_hours = sum(resolution_times) / len(resolution_times)

        # SLA compliance
        sla_met = sum(1 for i in resolved if i.resolved_at and i.sla_deadline and i.resolved_at <= i.sla_deadline)
        kpis.sla_compliance_rate = sla_met / len(resolved) if resolved else 0
        kpis.sla_breaches = len(resolved) - sla_met

        # Backlog
        now = datetime.now()
        open_incidents = [i for i in self.incidents.values() if i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED, IncidentStatus.REJECTED)]
        kpis.backlog_over_24h = sum(1 for i in open_incidents if i.get_age_hours() > 24)
        kpis.backlog_over_48h = sum(1 for i in open_incidents if i.get_age_hours() > 48)

        # Por severidad
        for sev in Severity:
            sev_incidents = [i for i in period_incidents if i.severity_estimate == sev]
            sev_resolved = [i for i in sev_incidents if i in resolved]
            avg_time = 0
            if sev_resolved:
                times = [(i.resolved_at - i.first_reported_at).total_seconds() / 3600 for i in sev_resolved if i.resolved_at and i.first_reported_at]
                avg_time = sum(times) / len(times) if times else 0

            kpis.by_severity[sev.value] = {
                'count': len(sev_incidents),
                'resolved': len(sev_resolved),
                'avg_resolution_hours': round(avg_time, 1)
            }

        # Por autoridad
        jur_engine = get_jurisdiction_engine()
        for auth in jur_engine.authorities:
            auth_incidents = [i for i in period_incidents if i.authority_id == auth.id]
            auth_resolved = [i for i in auth_incidents if i in resolved]
            auth_sla_met = sum(1 for i in auth_resolved if i.resolved_at and i.sla_deadline and i.resolved_at <= i.sla_deadline)

            if auth_incidents:
                kpis.by_authority[auth.id] = {
                    'authority_name': auth.name,
                    'incidents': len(auth_incidents),
                    'resolved': len(auth_resolved),
                    'sla_compliance': auth_sla_met / len(auth_resolved) if auth_resolved else 0
                }

        return kpis

    # =============================================
    # AUDIT LOG
    # =============================================

    def _log_audit(self, entity_type: str, entity_id: str, action: str, actor_type: str, actor_id: str, changes: dict = None):
        entry = AuditEntry(
            id=generate_id(),
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            changes=changes or {}
        )
        self.audit_log.append(entry)

    def get_audit_log(self, entity_type: str = None, entity_id: str = None, limit: int = 100) -> List[AuditEntry]:
        results = self.audit_log

        if entity_type:
            results = [e for e in results if e.entity_type == entity_type]
        if entity_id:
            results = [e for e in results if e.entity_id == entity_id]

        # Ordenar por timestamp desc
        results.sort(key=lambda e: e.timestamp, reverse=True)

        return results[:limit]


# Singleton
_data_store = None

def get_data_store() -> DataStore:
    global _data_store
    if _data_store is None:
        _data_store = DataStore()
    return _data_store
