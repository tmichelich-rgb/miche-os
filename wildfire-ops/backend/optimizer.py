"""
Wildfire Operations Allocation Engine - Optimization Core
Implements constraint-based resource allocation for firefighting operations.

For MVP: Uses priority-weighted greedy allocation with constraint propagation.
Structured to be easily upgradable to OR-Tools/PuLP when available.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum
import math
import json

class AssetType(Enum):
    AIRCRAFT = "aircraft"
    BRIGADE = "brigade"
    WATER_TRUCK = "water_truck"

@dataclass
class Location:
    lat: float
    lon: float
    name: str = ""

    def distance_to(self, other: 'Location') -> float:
        """Haversine distance in km"""
        R = 6371
        lat1, lat2 = math.radians(self.lat), math.radians(other.lat)
        dlat = math.radians(other.lat - self.lat)
        dlon = math.radians(other.lon - self.lon)
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

@dataclass
class Fire:
    id: str
    location: Location
    intensity: float  # 0-1 scale (from FRP or brightness)
    area_km2: float
    spread_rate: float  # km/hr based on conditions
    threat_score: float = 0.0  # computed: population + infrastructure at risk
    cluster_id: Optional[str] = None

    def compute_threat(self, protected_assets: List['ProtectedAsset'], wind_vector: Tuple[float, float] = (0, 0)) -> float:
        """Compute threat score based on proximity to assets and wind direction"""
        threat = 0.0
        wind_speed, wind_dir = wind_vector

        for asset in protected_assets:
            dist = self.location.distance_to(asset.location)
            if dist < 50:  # Within 50km threat radius
                # Base threat from proximity
                base_threat = asset.value * (1 - dist/50)

                # Wind factor: fires upwind of assets are more threatening
                if wind_speed > 0:
                    fire_to_asset_angle = math.atan2(
                        asset.location.lat - self.location.lat,
                        asset.location.lon - self.location.lon
                    )
                    wind_angle = math.radians(wind_dir)
                    angle_diff = abs(fire_to_asset_angle - wind_angle)
                    wind_factor = 1 + 0.5 * math.cos(angle_diff) * (wind_speed / 50)
                else:
                    wind_factor = 1.0

                threat += base_threat * wind_factor * self.intensity

        self.threat_score = threat
        return threat

@dataclass
class ProtectedAsset:
    id: str
    location: Location
    asset_type: str  # town, hospital, power_line, national_park
    value: float  # priority weight
    population: int = 0

@dataclass
class Resource:
    id: str
    asset_type: AssetType
    location: Location
    base_location: Location

    # Capacity constraints
    hours_remaining: float
    max_hours: float
    capacity: float  # water capacity (L) or personnel count

    # Movement constraints
    speed_kmh: float
    range_km: float

    # Operational constraints
    shift_hours_remaining: float
    max_shift_hours: float
    refuel_time_hours: float

    # State
    assigned_to: Optional[str] = None
    status: str = "available"

    def can_reach(self, target: Location) -> bool:
        dist = self.location.distance_to(target)
        return_dist = target.distance_to(self.base_location)
        return (dist + return_dist) <= self.range_km

    def travel_time(self, target: Location) -> float:
        return self.location.distance_to(target) / self.speed_kmh

    def effective_capacity(self, fire: 'Fire') -> float:
        """Capacity actually deliverable given constraints"""
        travel = self.travel_time(fire.location)
        if travel > self.hours_remaining or travel > self.shift_hours_remaining:
            return 0.0

        # Time available for operations after travel
        ops_time = min(self.hours_remaining, self.shift_hours_remaining) - travel

        if self.asset_type == AssetType.AIRCRAFT:
            # Drops per hour * capacity per drop
            return ops_time * 2 * self.capacity
        elif self.asset_type == AssetType.BRIGADE:
            # Containment rate (km of fire line per hour)
            return ops_time * self.capacity * 0.5
        else:  # Water truck
            return self.capacity * (ops_time / 0.5)  # Trips possible

@dataclass
class Constraint:
    name: str
    description: str
    is_binding: bool = False
    slack: float = 0.0
    shadow_price: float = 0.0  # How much objective improves per unit relaxation

@dataclass
class Assignment:
    resource_id: str
    fire_id: str
    priority: int
    travel_time_hours: float
    effective_capacity: float
    contribution_to_objective: float
    binding_constraints: List[str] = field(default_factory=list)
    explanation: str = ""

@dataclass
class AllocationPlan:
    assignments: List[Assignment]
    objective_value: float
    unassigned_fires: List[str]
    unassigned_resources: List[str]
    binding_constraints: List[Constraint]
    timestamp: str
    scenario_name: str

    def to_dict(self) -> dict:
        return {
            "assignments": [
                {
                    "resource_id": a.resource_id,
                    "fire_id": a.fire_id,
                    "priority": a.priority,
                    "travel_time_hours": round(a.travel_time_hours, 2),
                    "effective_capacity": round(a.effective_capacity, 1),
                    "contribution": round(a.contribution_to_objective, 2),
                    "binding_constraints": a.binding_constraints,
                    "explanation": a.explanation
                }
                for a in self.assignments
            ],
            "objective_value": round(self.objective_value, 2),
            "unassigned_fires": self.unassigned_fires,
            "unassigned_resources": self.unassigned_resources,
            "binding_constraints": [
                {
                    "name": c.name,
                    "description": c.description,
                    "is_binding": c.is_binding,
                    "slack": round(c.slack, 2)
                }
                for c in self.binding_constraints
            ],
            "timestamp": self.timestamp,
            "scenario": self.scenario_name
        }

class WildfireOptimizer:
    """
    Constraint-based allocation optimizer for wildfire response.

    Objective: Minimize expected damage = sum(fire_threat * (1 - containment_probability))

    Constraints:
    1. Aircraft flight hours
    2. Aircraft range (must return to base)
    3. Brigade travel time
    4. Crew shift limits
    5. Water truck capacity cycles
    6. Max simultaneous operations per fire cluster
    7. Minimum response per high-threat fire
    8. Resource type compatibility
    """

    def __init__(self):
        self.fires: List[Fire] = []
        self.resources: List[Resource] = []
        self.protected_assets: List[ProtectedAsset] = []
        self.constraints: List[Constraint] = []
        self.wind_vector: Tuple[float, float] = (0, 0)  # (speed_kmh, direction_degrees)

        # Constraint parameters
        self.max_ops_per_cluster = 4
        self.min_response_threshold = 0.7  # Threat score above which response is mandatory

    def set_scenario(self, wind_speed: float = 0, wind_direction: float = 0,
                     grounded_aircraft: List[str] = None):
        """Apply scenario modifications"""
        self.wind_vector = (wind_speed, wind_direction)

        if grounded_aircraft:
            for r in self.resources:
                if r.id in grounded_aircraft:
                    r.status = "grounded"
                    r.hours_remaining = 0

        # Recompute fire threats with new wind
        for fire in self.fires:
            fire.compute_threat(self.protected_assets, self.wind_vector)

    def _build_constraints(self) -> List[Constraint]:
        """Initialize constraint tracking"""
        return [
            Constraint("aircraft_hours", "Total aircraft flight hours available"),
            Constraint("aircraft_range", "Aircraft must be able to return to base"),
            Constraint("brigade_travel", "Brigade ground travel time limits"),
            Constraint("crew_shifts", "Maximum crew shift duration"),
            Constraint("water_capacity", "Water truck refill cycle capacity"),
            Constraint("cluster_ops", f"Max {self.max_ops_per_cluster} simultaneous ops per cluster"),
            Constraint("min_response", "High-threat fires require minimum response"),
            Constraint("type_compat", "Resource type must be compatible with fire conditions"),
        ]

    def optimize(self, scenario_name: str = "baseline") -> AllocationPlan:
        """
        Run the allocation optimization.

        Algorithm: Priority-weighted assignment with constraint propagation
        1. Rank fires by threat score
        2. For each fire, find best available resource considering constraints
        3. Assign and propagate constraint updates (one resource per fire)
        4. Track binding constraints and compute shadow prices
        """
        from datetime import datetime
        import copy

        self.constraints = self._build_constraints()
        assignments: List[Assignment] = []

        # Sort fires by threat (highest first)
        sorted_fires = sorted(self.fires, key=lambda f: f.threat_score, reverse=True)

        # Track resource usage
        resource_usage = {r.id: {"hours": 0, "assignments": 0} for r in self.resources}
        cluster_ops = {}  # cluster_id -> count

        # Deep copy resources to track state without modifying originals
        available = {}
        for r in self.resources:
            if r.status == "available":
                r_copy = copy.copy(r)
                r_copy.location = copy.copy(r.location)
                r_copy.base_location = copy.copy(r.base_location)
                available[r.id] = r_copy

        assigned_resources = set()  # Track which resources are committed
        objective_value = 0.0
        unassigned_fires = []

        for priority, fire in enumerate(sorted_fires):
            cluster_id = fire.cluster_id or fire.id
            current_cluster_ops = cluster_ops.get(cluster_id, 0)

            # Find best resource for this fire
            best_assignment = None
            best_score = -float('inf')
            binding = []

            for rid, resource in available.items():
                # Skip already assigned resources (one resource per fire for MVP)
                if rid in assigned_resources:
                    continue

                # Check constraints
                constraints_ok = True
                local_binding = []

                # C1: Aircraft hours
                if resource.asset_type == AssetType.AIRCRAFT:
                    travel = resource.travel_time(fire.location)
                    if resource.hours_remaining < travel * 2:
                        constraints_ok = False
                        local_binding.append("aircraft_hours")

                # C2: Range constraint
                if not resource.can_reach(fire.location):
                    constraints_ok = False
                    local_binding.append("aircraft_range")

                # C3/C4: Travel time and shift limits
                travel_time = resource.travel_time(fire.location)
                if travel_time > resource.shift_hours_remaining:
                    constraints_ok = False
                    local_binding.append("crew_shifts")

                # C6: Cluster operations limit
                if current_cluster_ops >= self.max_ops_per_cluster:
                    constraints_ok = False
                    local_binding.append("cluster_ops")

                # C8: Type compatibility (aircraft best for remote, brigades for containment)
                type_score = 1.0
                if fire.intensity > 0.7 and resource.asset_type == AssetType.WATER_TRUCK:
                    type_score = 0.3  # Less effective
                # Prefer aircraft for high-intensity fires
                if fire.intensity > 0.8 and resource.asset_type == AssetType.AIRCRAFT:
                    type_score = 1.3

                if constraints_ok:
                    # Score = threat reduction potential
                    capacity = resource.effective_capacity(fire)
                    containment_potential = min(1.0, capacity / (fire.area_km2 * 10))
                    score = fire.threat_score * containment_potential * type_score - travel_time * 0.1

                    if score > best_score:
                        best_score = score
                        best_assignment = Assignment(
                            resource_id=rid,
                            fire_id=fire.id,
                            priority=priority + 1,
                            travel_time_hours=travel_time,
                            effective_capacity=capacity,
                            contribution_to_objective=fire.threat_score * containment_potential,
                            binding_constraints=local_binding,
                            explanation=self._explain_assignment(resource, fire, containment_potential)
                        )
                else:
                    binding.extend(local_binding)

            if best_assignment:
                assignments.append(best_assignment)
                objective_value += best_assignment.contribution_to_objective

                # Update state
                rid = best_assignment.resource_id
                assigned_resources.add(rid)  # Mark as committed
                resource_usage[rid]["hours"] += best_assignment.travel_time_hours * 2
                resource_usage[rid]["assignments"] += 1
                cluster_ops[cluster_id] = current_cluster_ops + 1

                # Mark binding constraints
                for c in self.constraints:
                    if c.name in binding:
                        c.is_binding = True
            else:
                unassigned_fires.append(fire.id)
                # C7: Check if this violates min response
                if fire.threat_score > self.min_response_threshold:
                    for c in self.constraints:
                        if c.name == "min_response":
                            c.is_binding = True

        unassigned_resources = [rid for rid in available.keys() if rid not in assigned_resources]

        return AllocationPlan(
            assignments=assignments,
            objective_value=objective_value,
            unassigned_fires=unassigned_fires,
            unassigned_resources=unassigned_resources,
            binding_constraints=[c for c in self.constraints if c.is_binding],
            timestamp=datetime.now().isoformat(),
            scenario_name=scenario_name
        )

    def _explain_assignment(self, resource: Resource, fire: Fire, containment: float) -> str:
        """Generate human-readable explanation for assignment decision"""
        asset_name = resource.asset_type.value.replace("_", " ").title()

        parts = [f"{asset_name} {resource.id} assigned to Fire {fire.id}"]
        parts.append(f"Threat score: {fire.threat_score:.2f}")
        parts.append(f"Travel time: {resource.travel_time(fire.location):.1f}h")
        parts.append(f"Expected containment contribution: {containment*100:.0f}%")

        if self.wind_vector[0] > 0:
            parts.append(f"Wind factor considered: {self.wind_vector[0]:.0f} km/h from {self.wind_vector[1]:.0f}°")

        return " | ".join(parts)

    def compare_scenarios(self, scenario_a: AllocationPlan, scenario_b: AllocationPlan) -> dict:
        """Compare two allocation plans and explain differences"""
        diff = {
            "objective_delta": scenario_b.objective_value - scenario_a.objective_value,
            "assignment_changes": [],
            "new_binding_constraints": [],
            "explanation": ""
        }

        a_assignments = {a.fire_id: a for a in scenario_a.assignments}
        b_assignments = {a.fire_id: a for a in scenario_b.assignments}

        for fire_id in set(a_assignments.keys()) | set(b_assignments.keys()):
            a_assign = a_assignments.get(fire_id)
            b_assign = b_assignments.get(fire_id)

            if a_assign and not b_assign:
                diff["assignment_changes"].append({
                    "fire_id": fire_id,
                    "change": "dropped",
                    "reason": "No longer feasible under new constraints"
                })
            elif b_assign and not a_assign:
                diff["assignment_changes"].append({
                    "fire_id": fire_id,
                    "change": "added",
                    "resource": b_assign.resource_id
                })
            elif a_assign and b_assign and a_assign.resource_id != b_assign.resource_id:
                diff["assignment_changes"].append({
                    "fire_id": fire_id,
                    "change": "reassigned",
                    "from": a_assign.resource_id,
                    "to": b_assign.resource_id
                })

        # New binding constraints
        a_binding = {c.name for c in scenario_a.binding_constraints}
        b_binding = {c.name for c in scenario_b.binding_constraints}
        diff["new_binding_constraints"] = list(b_binding - a_binding)

        # Generate explanation
        if diff["objective_delta"] < 0:
            diff["explanation"] = f"Scenario '{scenario_b.scenario_name}' reduces coverage by {abs(diff['objective_delta']):.1f} points. "
        else:
            diff["explanation"] = f"Scenario '{scenario_b.scenario_name}' improves coverage by {diff['objective_delta']:.1f} points. "

        if diff["new_binding_constraints"]:
            diff["explanation"] += f"New constraints became binding: {', '.join(diff['new_binding_constraints'])}. "

        if diff["assignment_changes"]:
            diff["explanation"] += f"{len(diff['assignment_changes'])} assignments changed."

        return diff


# Demo data generator for Chubut/Los Alerces region
def create_demo_scenario():
    """Create realistic demo data for Chubut, Argentina"""

    optimizer = WildfireOptimizer()

    # Protected assets in Chubut
    optimizer.protected_assets = [
        ProtectedAsset("esquel", Location(-42.9167, -71.3167, "Esquel"), "town", 0.9, 32000),
        ProtectedAsset("trevelin", Location(-43.0833, -71.4667, "Trevelin"), "town", 0.7, 8000),
        ProtectedAsset("los_alerces", Location(-42.75, -71.7, "Los Alerces NP"), "national_park", 1.0, 0),
        ProtectedAsset("futaleufú_dam", Location(-43.1833, -71.6, "Futaleufú Dam"), "power_line", 0.85, 0),
        ProtectedAsset("hospital_esquel", Location(-42.92, -71.32, "Hospital Zonal"), "hospital", 0.95, 0),
    ]

    # Active fires (simulated based on typical FIRMS pattern)
    optimizer.fires = [
        Fire("F001", Location(-42.85, -71.55, "Lago Futalaufquen N"), 0.8, 2.5, 0.3),
        Fire("F002", Location(-42.78, -71.62, "Cerro Alto"), 0.9, 4.0, 0.5, cluster_id="cluster_north"),
        Fire("F003", Location(-42.82, -71.58, "Valle Turbio"), 0.7, 1.8, 0.2, cluster_id="cluster_north"),
        Fire("F004", Location(-43.05, -71.48, "Near Trevelin"), 0.6, 1.2, 0.15),
        Fire("F005", Location(-42.95, -71.65, "Cordón Rivadavia"), 0.85, 3.5, 0.4),
    ]

    # Compute initial threats
    for fire in optimizer.fires:
        fire.compute_threat(optimizer.protected_assets)

    # Resources
    esquel_base = Location(-42.9167, -71.3167, "Esquel Airport")

    optimizer.resources = [
        # Aircraft
        Resource("AC001", AssetType.AIRCRAFT, esquel_base, esquel_base,
                hours_remaining=6.0, max_hours=8.0, capacity=3000,
                speed_kmh=250, range_km=400, shift_hours_remaining=8.0,
                max_shift_hours=10.0, refuel_time_hours=0.5),
        Resource("AC002", AssetType.AIRCRAFT, esquel_base, esquel_base,
                hours_remaining=4.5, max_hours=8.0, capacity=5000,
                speed_kmh=200, range_km=350, shift_hours_remaining=6.0,
                max_shift_hours=10.0, refuel_time_hours=0.75),

        # Brigades
        Resource("BR001", AssetType.BRIGADE, Location(-42.93, -71.35, "Esquel Station"), esquel_base,
                hours_remaining=8.0, max_hours=12.0, capacity=20,
                speed_kmh=40, range_km=150, shift_hours_remaining=6.0,
                max_shift_hours=8.0, refuel_time_hours=0.25),
        Resource("BR002", AssetType.BRIGADE, Location(-43.08, -71.45, "Trevelin Station"),
                Location(-43.0833, -71.4667, "Trevelin"),
                hours_remaining=10.0, max_hours=12.0, capacity=15,
                speed_kmh=35, range_km=120, shift_hours_remaining=7.0,
                max_shift_hours=8.0, refuel_time_hours=0.25),
        Resource("BR003", AssetType.BRIGADE, esquel_base, esquel_base,
                hours_remaining=6.0, max_hours=12.0, capacity=25,
                speed_kmh=45, range_km=180, shift_hours_remaining=5.0,
                max_shift_hours=8.0, refuel_time_hours=0.25),

        # Water trucks
        Resource("WT001", AssetType.WATER_TRUCK, Location(-42.90, -71.30, "Depot 1"), esquel_base,
                hours_remaining=8.0, max_hours=10.0, capacity=10000,
                speed_kmh=50, range_km=200, shift_hours_remaining=8.0,
                max_shift_hours=10.0, refuel_time_hours=0.3),
        Resource("WT002", AssetType.WATER_TRUCK, Location(-43.10, -71.50, "Depot 2"),
                Location(-43.0833, -71.4667, "Trevelin"),
                hours_remaining=6.0, max_hours=10.0, capacity=8000,
                speed_kmh=45, range_km=180, shift_hours_remaining=6.0,
                max_shift_hours=10.0, refuel_time_hours=0.3),
    ]

    return optimizer


if __name__ == "__main__":
    # Test the optimizer
    opt = create_demo_scenario()

    print("=== Baseline Scenario ===")
    baseline = opt.optimize("baseline")
    print(json.dumps(baseline.to_dict(), indent=2))

    print("\n=== Wind Shift Scenario ===")
    opt2 = create_demo_scenario()
    opt2.set_scenario(wind_speed=35, wind_direction=270)  # Strong westerly
    wind_plan = opt2.optimize("wind_shift_west_35kmh")
    print(json.dumps(wind_plan.to_dict(), indent=2))

    print("\n=== Comparison ===")
    print(json.dumps(opt2.compare_scenarios(baseline, wind_plan), indent=2))
