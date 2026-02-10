"""
CityOps Vial - Data Models
Gestión integral de incidentes viales para Argentina
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
import math
import uuid
import json

# ============================================
# ENUMS
# ============================================

class IncidentStatus(Enum):
    NEW = "new"
    VALIDATED = "validated"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"

class IncidentType(Enum):
    POTHOLE = "pothole"
    CRACK = "crack"
    DEBRIS = "debris"
    SIGNAGE = "signage"
    FLOODING = "flooding"
    OTHER = "other"

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class JurisdictionLevel(Enum):
    NATIONAL = "national"
    PROVINCIAL = "provincial"
    MUNICIPAL = "municipal"

class AuthorityType(Enum):
    GOVERNMENT_AGENCY = "government_agency"
    CONCESSIONAIRE = "concessionaire"
    CONTRACTOR = "contractor"

class CrewStatus(Enum):
    AVAILABLE = "available"
    ASSIGNED = "assigned"
    EN_ROUTE = "en_route"
    WORKING = "working"
    OFF_DUTY = "off_duty"

class AssignmentStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EN_ROUTE = "en_route"
    ON_SITE = "on_site"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class SourceType(Enum):
    CITIZEN_APP = "citizen_app"
    WAZE = "waze"
    CALL_CENTER = "call_center"
    INSPECTION = "inspection"
    SENSOR = "sensor"

# ============================================
# LOCATION & GEO
# ============================================

@dataclass
class Location:
    lat: float
    lon: float
    accuracy_m: float = 10.0

    def distance_to(self, other: 'Location') -> float:
        """Haversine distance in km"""
        R = 6371
        lat1, lat2 = math.radians(self.lat), math.radians(other.lat)
        dlat = math.radians(other.lat - self.lat)
        dlon = math.radians(other.lon - self.lon)
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    def to_dict(self):
        return {"lat": self.lat, "lon": self.lon, "accuracy_m": self.accuracy_m}

    @staticmethod
    def from_dict(d):
        return Location(d["lat"], d["lon"], d.get("accuracy_m", 10.0))

# ============================================
# JURISDICTION & AUTHORITY
# ============================================

@dataclass
class Jurisdiction:
    id: str
    level: JurisdictionLevel
    name: str
    code: str
    parent_id: Optional[str] = None
    # Simplified: bounding box instead of full polygon
    bbox: Tuple[float, float, float, float] = None  # (min_lon, min_lat, max_lon, max_lat)
    default_authority_id: Optional[str] = None
    sla_response_hours: int = 4
    sla_resolution_hours: int = 24

    def contains(self, loc: Location) -> bool:
        if not self.bbox:
            return False
        min_lon, min_lat, max_lon, max_lat = self.bbox
        return min_lon <= loc.lon <= max_lon and min_lat <= loc.lat <= max_lat

    def to_dict(self):
        return {
            "id": self.id,
            "level": self.level.value,
            "name": self.name,
            "code": self.code,
            "parent_id": self.parent_id,
            "bbox": self.bbox,
            "sla_response_hours": self.sla_response_hours,
            "sla_resolution_hours": self.sla_resolution_hours
        }

@dataclass
class Authority:
    id: str
    type: AuthorityType
    name: str
    code: str
    jurisdiction_id: str
    contact_email: str = ""
    contact_phone: str = ""
    active: bool = True

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "code": self.code,
            "jurisdiction_id": self.jurisdiction_id,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "active": self.active
        }

# ============================================
# ROAD SEGMENT
# ============================================

@dataclass
class RoadSegment:
    id: str
    road_type: str  # national_route, provincial_route, municipal_street, highway
    road_name: str
    jurisdiction_id: str
    authority_id: str
    # Simplified: just start/end points instead of full linestring
    start_location: Location
    end_location: Location
    aadt: int = 10000  # Annual Average Daily Traffic
    speed_limit_kmh: int = 60
    lanes: int = 2
    incident_history_score: float = 0.0

    def contains_point(self, loc: Location) -> bool:
        """Check if point is near this segment (simplified)"""
        # Calculate distance to segment line
        dist_to_start = loc.distance_to(self.start_location)
        dist_to_end = loc.distance_to(self.end_location)
        segment_length = self.start_location.distance_to(self.end_location)

        # Point is "on" segment if sum of distances is close to segment length
        tolerance = 0.5  # km
        return (dist_to_start + dist_to_end) < (segment_length + tolerance)

    def to_dict(self):
        return {
            "id": self.id,
            "road_type": self.road_type,
            "road_name": self.road_name,
            "jurisdiction_id": self.jurisdiction_id,
            "authority_id": self.authority_id,
            "aadt": self.aadt,
            "speed_limit_kmh": self.speed_limit_kmh,
            "lanes": self.lanes
        }

# ============================================
# INCIDENT
# ============================================

@dataclass
class SourceReport:
    id: str
    source_type: SourceType
    location: Location
    reported_at: datetime
    description: str = ""
    media_urls: List[str] = field(default_factory=list)
    reporter_id: str = ""
    reliability_score: float = 0.5

    def to_dict(self):
        return {
            "id": self.id,
            "source_type": self.source_type.value,
            "location": self.location.to_dict(),
            "reported_at": self.reported_at.isoformat(),
            "description": self.description,
            "media_urls": self.media_urls,
            "reliability_score": self.reliability_score
        }

@dataclass
class Incident:
    id: str
    status: IncidentStatus
    location: Location
    incident_type: IncidentType

    # Computed fields
    severity_estimate: Severity = Severity.MEDIUM
    risk_score: float = 50.0
    confidence_score: float = 0.5

    # Tracking
    report_count: int = 1
    first_reported_at: datetime = None
    last_reported_at: datetime = None

    # Jurisdiction
    jurisdiction_id: Optional[str] = None
    authority_id: Optional[str] = None
    road_segment_id: Optional[str] = None
    address_text: str = ""

    # Assignment
    current_assignment_id: Optional[str] = None

    # SLA
    sla_deadline: Optional[datetime] = None

    # Resolution
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # Source reports
    source_reports: List[SourceReport] = field(default_factory=list)

    # Metadata
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        now = datetime.now()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if not self.first_reported_at:
            self.first_reported_at = now
        if not self.last_reported_at:
            self.last_reported_at = now

    def get_sla_status(self) -> str:
        if not self.sla_deadline:
            return "unknown"
        now = datetime.now()
        if self.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
            return "met" if self.resolved_at and self.resolved_at <= self.sla_deadline else "breached"
        if now > self.sla_deadline:
            return "breached"
        remaining = (self.sla_deadline - now).total_seconds() / 3600
        if remaining < 2:
            return "at_risk"
        return "on_track"

    def get_age_hours(self) -> float:
        return (datetime.now() - self.first_reported_at).total_seconds() / 3600

    def to_dict(self):
        return {
            "id": self.id,
            "status": self.status.value,
            "location": self.location.to_dict(),
            "incident_type": self.incident_type.value,
            "severity_estimate": self.severity_estimate.value,
            "risk_score": round(self.risk_score, 1),
            "confidence_score": round(self.confidence_score, 2),
            "report_count": self.report_count,
            "first_reported_at": self.first_reported_at.isoformat() if self.first_reported_at else None,
            "last_reported_at": self.last_reported_at.isoformat() if self.last_reported_at else None,
            "jurisdiction_id": self.jurisdiction_id,
            "authority_id": self.authority_id,
            "address_text": self.address_text,
            "current_assignment_id": self.current_assignment_id,
            "sla_deadline": self.sla_deadline.isoformat() if self.sla_deadline else None,
            "sla_status": self.get_sla_status(),
            "age_hours": round(self.get_age_hours(), 1),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "source_reports": [r.to_dict() for r in self.source_reports],
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

# ============================================
# CREW & ASSETS
# ============================================

@dataclass
class Crew:
    id: str
    authority_id: str
    name: str
    crew_type: str  # pothole_repair, signage, general_maintenance
    status: CrewStatus
    location: Location

    # Capacity
    member_count: int = 4
    capabilities: List[str] = field(default_factory=list)

    # Shift
    shift_start_hour: int = 8
    shift_end_hour: int = 18
    max_daily_assignments: int = 6
    today_assignments: int = 0

    # Tracking
    location_updated_at: datetime = None

    def is_on_shift(self) -> bool:
        now = datetime.now()
        return self.shift_start_hour <= now.hour < self.shift_end_hour

    def get_remaining_shift_hours(self) -> float:
        now = datetime.now()
        if not self.is_on_shift():
            return 0
        return max(0, self.shift_end_hour - now.hour - now.minute/60)

    def can_accept_assignment(self) -> bool:
        return (
            self.status == CrewStatus.AVAILABLE and
            self.is_on_shift() and
            self.today_assignments < self.max_daily_assignments
        )

    def travel_time_to(self, target: Location) -> float:
        """Estimate travel time in minutes (assuming 30 km/h average in urban)"""
        distance = self.location.distance_to(target)
        return (distance / 30) * 60  # minutes

    def to_dict(self):
        return {
            "id": self.id,
            "authority_id": self.authority_id,
            "name": self.name,
            "crew_type": self.crew_type,
            "status": self.status.value,
            "location": self.location.to_dict(),
            "member_count": self.member_count,
            "capabilities": self.capabilities,
            "is_on_shift": self.is_on_shift(),
            "remaining_shift_hours": round(self.get_remaining_shift_hours(), 1),
            "today_assignments": self.today_assignments,
            "max_daily_assignments": self.max_daily_assignments,
            "can_accept": self.can_accept_assignment()
        }

# ============================================
# ASSIGNMENT
# ============================================

@dataclass
class Assignment:
    id: str
    incident_id: str
    crew_id: str
    authority_id: str
    status: AssignmentStatus

    # Optimizer data
    priority_rank: int = 0
    optimizer_score: float = 0.0
    optimizer_reasoning: Dict = field(default_factory=dict)

    # Timing
    assigned_at: datetime = None
    accepted_at: datetime = None
    eta_minutes: int = 0
    actual_arrival_at: datetime = None
    work_started_at: datetime = None
    work_completed_at: datetime = None

    # Cost
    estimated_cost: float = 0.0
    actual_cost: float = 0.0

    # Notes
    rejection_reason: str = ""
    completion_notes: str = ""

    def __post_init__(self):
        if not self.assigned_at:
            self.assigned_at = datetime.now()

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "crew_id": self.crew_id,
            "authority_id": self.authority_id,
            "status": self.status.value,
            "priority_rank": self.priority_rank,
            "optimizer_score": round(self.optimizer_score, 2),
            "optimizer_reasoning": self.optimizer_reasoning,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "eta_minutes": self.eta_minutes,
            "actual_arrival_at": self.actual_arrival_at.isoformat() if self.actual_arrival_at else None,
            "work_completed_at": self.work_completed_at.isoformat() if self.work_completed_at else None,
            "estimated_cost": self.estimated_cost,
            "actual_cost": self.actual_cost
        }

# ============================================
# EVIDENCE
# ============================================

@dataclass
class Evidence:
    id: str
    incident_id: str
    assignment_id: Optional[str]
    evidence_type: str  # photo_before, photo_after, video, document
    stage: str  # report, arrival, completion, verification
    file_url: str
    capture_location: Optional[Location] = None
    capture_timestamp: datetime = None
    captured_by_user_id: str = ""
    verified: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "evidence_type": self.evidence_type,
            "stage": self.stage,
            "file_url": self.file_url,
            "capture_location": self.capture_location.to_dict() if self.capture_location else None,
            "capture_timestamp": self.capture_timestamp.isoformat() if self.capture_timestamp else None,
            "verified": self.verified
        }

# ============================================
# AUDIT LOG
# ============================================

@dataclass
class AuditEntry:
    id: str
    entity_type: str
    entity_id: str
    action: str
    actor_type: str  # user, system, api
    actor_id: str
    changes: Dict
    timestamp: datetime = None

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now()

    def to_dict(self):
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "action": self.action,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "changes": self.changes,
            "timestamp": self.timestamp.isoformat()
        }

# ============================================
# KPI METRICS
# ============================================

@dataclass
class KPIMetrics:
    period_start: datetime
    period_end: datetime

    total_incidents: int = 0
    total_resolved: int = 0
    resolution_rate: float = 0.0

    avg_detection_to_assignment_hours: float = 0.0
    avg_assignment_to_resolution_hours: float = 0.0
    avg_total_resolution_hours: float = 0.0

    sla_compliance_rate: float = 0.0
    sla_breaches: int = 0

    backlog_over_24h: int = 0
    backlog_over_48h: int = 0

    recurrence_rate: float = 0.0
    avg_cost_per_incident: float = 0.0
    evidence_coverage_rate: float = 0.0

    by_severity: Dict = field(default_factory=dict)
    by_authority: Dict = field(default_factory=dict)
    by_jurisdiction: Dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat()
            },
            "total_incidents": self.total_incidents,
            "total_resolved": self.total_resolved,
            "resolution_rate": round(self.resolution_rate, 2),
            "avg_detection_to_assignment_hours": round(self.avg_detection_to_assignment_hours, 1),
            "avg_assignment_to_resolution_hours": round(self.avg_assignment_to_resolution_hours, 1),
            "avg_total_resolution_hours": round(self.avg_total_resolution_hours, 1),
            "sla_compliance_rate": round(self.sla_compliance_rate, 2),
            "sla_breaches": self.sla_breaches,
            "backlog_over_24h": self.backlog_over_24h,
            "backlog_over_48h": self.backlog_over_48h,
            "recurrence_rate": round(self.recurrence_rate, 2),
            "avg_cost_per_incident": round(self.avg_cost_per_incident, 0),
            "evidence_coverage_rate": round(self.evidence_coverage_rate, 2),
            "by_severity": self.by_severity,
            "by_authority": self.by_authority
        }


# ============================================
# HELPER FUNCTIONS
# ============================================

def generate_id() -> str:
    return str(uuid.uuid4())

def generate_tracking_code() -> str:
    """Generate human-readable tracking code like INC-2024-00001234"""
    import random
    year = datetime.now().year
    num = random.randint(10000, 99999999)
    return f"INC-{year}-{num:08d}"
