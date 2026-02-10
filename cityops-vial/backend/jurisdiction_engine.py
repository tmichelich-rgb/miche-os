"""
CityOps Vial - Jurisdiction Engine
Determina automáticamente la jurisdicción y autoridad responsable
"""

from typing import List, Optional, Tuple
from models import (
    Location, Jurisdiction, Authority, RoadSegment, Incident,
    JurisdictionLevel, AuthorityType, IncidentType
)

class JurisdictionEngine:
    """
    Motor de asignación jurisdiccional para CABA y GBA.
    Determina quién es responsable de cada incidente según ubicación.
    """

    def __init__(self):
        self.jurisdictions: List[Jurisdiction] = []
        self.authorities: List[Authority] = []
        self.road_segments: List[RoadSegment] = []
        self._load_caba_gba_data()

    def _load_caba_gba_data(self):
        """Carga datos de jurisdicciones de CABA y GBA"""

        # =============================================
        # JURISDICCIONES
        # =============================================

        # Argentina (Nacional)
        argentina = Jurisdiction(
            id="jur-argentina",
            level=JurisdictionLevel.NATIONAL,
            name="República Argentina",
            code="AR",
            bbox=(-73.5, -55.0, -53.5, -21.5)
        )

        # Provincia de Buenos Aires
        prov_ba = Jurisdiction(
            id="jur-prov-ba",
            level=JurisdictionLevel.PROVINCIAL,
            name="Provincia de Buenos Aires",
            code="BA",
            parent_id="jur-argentina",
            bbox=(-63.5, -41.0, -56.5, -33.0),
            sla_response_hours=6,
            sla_resolution_hours=48
        )

        # CABA
        caba = Jurisdiction(
            id="jur-caba",
            level=JurisdictionLevel.MUNICIPAL,
            name="Ciudad Autónoma de Buenos Aires",
            code="CABA",
            parent_id="jur-argentina",
            bbox=(-58.53, -34.71, -58.33, -34.52),
            sla_response_hours=4,
            sla_resolution_hours=24
        )

        # Municipios del GBA
        municipios_gba = [
            ("jur-avellaneda", "Avellaneda", "AVE", (-58.40, -34.70, -58.28, -34.62)),
            ("jur-lanus", "Lanús", "LAN", (-58.43, -34.74, -58.35, -34.68)),
            ("jur-lomas", "Lomas de Zamora", "LDZ", (-58.48, -34.80, -58.38, -34.72)),
            ("jur-quilmes", "Quilmes", "QUI", (-58.32, -34.78, -58.22, -34.68)),
            ("jur-moron", "Morón", "MOR", (-58.68, -34.68, -58.58, -34.62)),
            ("jur-lamatanza", "La Matanza", "MAT", (-58.72, -34.82, -58.48, -34.62)),
            ("jur-sanmartin", "San Martín", "SMT", (-58.58, -34.60, -58.48, -34.52)),
            ("jur-tresdefebrero", "Tres de Febrero", "TDF", (-58.62, -34.62, -58.54, -34.56)),
            ("jur-vicentelopez", "Vicente López", "VLO", (-58.52, -34.55, -58.45, -34.50)),
            ("jur-sanisidro", "San Isidro", "SIS", (-58.58, -34.52, -58.48, -34.45)),
            ("jur-tigre", "Tigre", "TIG", (-58.62, -34.48, -58.48, -34.38)),
        ]

        self.jurisdictions = [argentina, prov_ba, caba]

        for jur_id, name, code, bbox in municipios_gba:
            self.jurisdictions.append(Jurisdiction(
                id=jur_id,
                level=JurisdictionLevel.MUNICIPAL,
                name=name,
                code=code,
                parent_id="jur-prov-ba",
                bbox=bbox,
                sla_response_hours=6,
                sla_resolution_hours=48
            ))

        # =============================================
        # AUTORIDADES
        # =============================================

        self.authorities = [
            # Nacional
            Authority(
                id="auth-vialidad-nacional",
                type=AuthorityType.GOVERNMENT_AGENCY,
                name="Vialidad Nacional",
                code="DNV",
                jurisdiction_id="jur-argentina",
                contact_email="reclamos@vialidad.gob.ar"
            ),
            Authority(
                id="auth-aubasa",
                type=AuthorityType.CONCESSIONAIRE,
                name="AUBASA",
                code="AUBASA",
                jurisdiction_id="jur-prov-ba",
                contact_email="reclamos@aubasa.com.ar"
            ),
            # CABA
            Authority(
                id="auth-gcba-transporte",
                type=AuthorityType.GOVERNMENT_AGENCY,
                name="Secretaría de Transporte GCBA",
                code="GCBA-TR",
                jurisdiction_id="jur-caba",
                contact_email="vialidad@buenosaires.gob.ar"
            ),
            Authority(
                id="auth-ausa",
                type=AuthorityType.CONCESSIONAIRE,
                name="AUSA - Autopistas Urbanas",
                code="AUSA",
                jurisdiction_id="jur-caba",
                contact_email="reclamos@ausa.com.ar"
            ),
        ]

        # Autoridades municipales GBA
        for jur in self.jurisdictions:
            if jur.level == JurisdictionLevel.MUNICIPAL and jur.parent_id == "jur-prov-ba":
                self.authorities.append(Authority(
                    id=f"auth-{jur.code.lower()}",
                    type=AuthorityType.GOVERNMENT_AGENCY,
                    name=f"Obras Públicas {jur.name}",
                    code=f"OP-{jur.code}",
                    jurisdiction_id=jur.id
                ))

        # =============================================
        # ROAD SEGMENTS (principales)
        # =============================================

        self.road_segments = [
            # Autopista 25 de Mayo (AUSA)
            RoadSegment(
                id="seg-25mayo-1",
                road_type="highway",
                road_name="Autopista 25 de Mayo",
                jurisdiction_id="jur-caba",
                authority_id="auth-ausa",
                start_location=Location(-34.6345, -58.3850),
                end_location=Location(-34.6150, -58.4350),
                aadt=120000,
                speed_limit_kmh=100,
                lanes=6
            ),
            # Autopista Perito Moreno (AUSA)
            RoadSegment(
                id="seg-perito-1",
                road_type="highway",
                road_name="Autopista Perito Moreno",
                jurisdiction_id="jur-caba",
                authority_id="auth-ausa",
                start_location=Location(-34.6350, -58.4350),
                end_location=Location(-34.6380, -58.5200),
                aadt=90000,
                speed_limit_kmh=100,
                lanes=6
            ),
            # Av. 9 de Julio (GCBA)
            RoadSegment(
                id="seg-9julio",
                road_type="municipal_street",
                road_name="Av. 9 de Julio",
                jurisdiction_id="jur-caba",
                authority_id="auth-gcba-transporte",
                start_location=Location(-34.5950, -58.3810),
                end_location=Location(-34.6350, -58.3830),
                aadt=80000,
                speed_limit_kmh=60,
                lanes=16
            ),
            # Av. Rivadavia (GCBA)
            RoadSegment(
                id="seg-rivadavia",
                road_type="municipal_street",
                road_name="Av. Rivadavia",
                jurisdiction_id="jur-caba",
                authority_id="auth-gcba-transporte",
                start_location=Location(-34.6090, -58.3700),
                end_location=Location(-34.6350, -58.5200),
                aadt=50000,
                speed_limit_kmh=50,
                lanes=6
            ),
            # Autopista Buenos Aires - La Plata (AUBASA)
            RoadSegment(
                id="seg-balaplata",
                road_type="highway",
                road_name="Autopista Buenos Aires - La Plata",
                jurisdiction_id="jur-prov-ba",
                authority_id="auth-aubasa",
                start_location=Location(-34.6400, -58.3700),
                end_location=Location(-34.9200, -57.9500),
                aadt=95000,
                speed_limit_kmh=120,
                lanes=6
            ),
            # Acceso Oeste (AUBASA)
            RoadSegment(
                id="seg-accesooeste",
                road_type="highway",
                road_name="Acceso Oeste",
                jurisdiction_id="jur-prov-ba",
                authority_id="auth-aubasa",
                start_location=Location(-34.6200, -58.4800),
                end_location=Location(-34.6100, -58.8500),
                aadt=85000,
                speed_limit_kmh=120,
                lanes=6
            ),
            # Ruta Nacional 3 (Vialidad Nacional)
            RoadSegment(
                id="seg-rn3",
                road_type="national_route",
                road_name="Ruta Nacional 3",
                jurisdiction_id="jur-argentina",
                authority_id="auth-vialidad-nacional",
                start_location=Location(-34.7000, -58.4500),
                end_location=Location(-34.9500, -58.3000),
                aadt=35000,
                speed_limit_kmh=80,
                lanes=4
            ),
        ]

        # Asignar autoridad por defecto a cada jurisdicción
        for jur in self.jurisdictions:
            if jur.id == "jur-caba":
                jur.default_authority_id = "auth-gcba-transporte"
            elif jur.id == "jur-argentina":
                jur.default_authority_id = "auth-vialidad-nacional"
            elif jur.level == JurisdictionLevel.MUNICIPAL:
                jur.default_authority_id = f"auth-{jur.code.lower()}"

    def find_jurisdiction(self, location: Location) -> Optional[Jurisdiction]:
        """
        Encuentra la jurisdicción más específica para una ubicación.
        Prioridad: Municipal > Provincial > Nacional
        """
        matches = []
        for jur in self.jurisdictions:
            if jur.contains(location):
                matches.append(jur)

        if not matches:
            return None

        # Ordenar por especificidad (municipal > provincial > nacional)
        priority = {
            JurisdictionLevel.MUNICIPAL: 3,
            JurisdictionLevel.PROVINCIAL: 2,
            JurisdictionLevel.NATIONAL: 1
        }
        matches.sort(key=lambda j: priority.get(j.level, 0), reverse=True)
        return matches[0]

    def find_road_segment(self, location: Location) -> Optional[RoadSegment]:
        """Encuentra el segmento de ruta más cercano"""
        best_segment = None
        best_distance = float('inf')

        for seg in self.road_segments:
            # Distancia al punto medio del segmento
            mid_lat = (seg.start_location.lat + seg.end_location.lat) / 2
            mid_lon = (seg.start_location.lon + seg.end_location.lon) / 2
            mid = Location(mid_lat, mid_lon)
            dist = location.distance_to(mid)

            # Solo considerar si está relativamente cerca (< 1km)
            if dist < 1.0 and dist < best_distance:
                best_distance = dist
                best_segment = seg

        return best_segment

    def determine_responsibility(self, location: Location) -> Tuple[Optional[Jurisdiction], Optional[Authority], Optional[RoadSegment]]:
        """
        Determina jurisdicción, autoridad responsable y segmento de ruta.

        Lógica:
        1. Si está en un segmento de ruta conocido → usar autoridad del segmento
        2. Si no → usar autoridad por defecto de la jurisdicción
        """
        jurisdiction = self.find_jurisdiction(location)
        if not jurisdiction:
            return None, None, None

        road_segment = self.find_road_segment(location)

        if road_segment:
            # Usar autoridad del segmento
            authority = next((a for a in self.authorities if a.id == road_segment.authority_id), None)
        else:
            # Usar autoridad por defecto de la jurisdicción
            authority = next((a for a in self.authorities if a.id == jurisdiction.default_authority_id), None)

        return jurisdiction, authority, road_segment

    def get_jurisdiction_by_id(self, jur_id: str) -> Optional[Jurisdiction]:
        return next((j for j in self.jurisdictions if j.id == jur_id), None)

    def get_authority_by_id(self, auth_id: str) -> Optional[Authority]:
        return next((a for a in self.authorities if a.id == auth_id), None)

    def get_jurisdictions_summary(self) -> List[dict]:
        """Resumen de jurisdicciones para API"""
        return [j.to_dict() for j in self.jurisdictions]

    def get_authorities_summary(self) -> List[dict]:
        """Resumen de autoridades para API"""
        return [a.to_dict() for a in self.authorities]

    def get_sla_for_incident(self, incident: Incident) -> Tuple[int, int]:
        """
        Obtiene los tiempos de SLA según severidad y jurisdicción.
        Returns (response_hours, resolution_hours)
        """
        jur = self.get_jurisdiction_by_id(incident.jurisdiction_id) if incident.jurisdiction_id else None

        base_response = jur.sla_response_hours if jur else 4
        base_resolution = jur.sla_resolution_hours if jur else 24

        # Ajustar por severidad
        severity_multiplier = {
            'critical': 0.5,  # Mitad del tiempo
            'high': 0.75,
            'medium': 1.0,
            'low': 1.5
        }

        mult = severity_multiplier.get(incident.severity_estimate.value, 1.0)

        return int(base_response * mult), int(base_resolution * mult)


# Singleton
_jurisdiction_engine = None

def get_jurisdiction_engine() -> JurisdictionEngine:
    global _jurisdiction_engine
    if _jurisdiction_engine is None:
        _jurisdiction_engine = JurisdictionEngine()
    return _jurisdiction_engine
