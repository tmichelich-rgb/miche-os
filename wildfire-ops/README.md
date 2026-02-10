# 🔥 Wildfire Ops Allocation Engine
## Chubut / Los Alerces Region - Argentina

A decision-support system for allocating firefighting resources to active wildfires under constraints. This is **not** a chatbot or RAG demo — it's an **operational optimization engine** with auditable decisions.

![Architecture](https://img.shields.io/badge/Pattern-Foundry--Style-blue)
![Optimization](https://img.shields.io/badge/Engine-Constraint--Based-orange)
![Data](https://img.shields.io/badge/Source-NASA%20FIRMS-green)

---

## What It Does

Given **active fires** + **resources** + **constraints**, the engine produces:
- **Dispatch Plan**: Which resource goes where, in what order
- **Tradeoff Analysis**: Why each decision was made
- **Scenario Comparison**: "If we change X, Y breaks"

### The "Palantir Moment"

> "Here's what happens if a bridge goes down / aircraft grounded / wind shifts. Notice how the model reallocates and **why**."

---

## Quick Start

```bash
# Start the server
./run.sh

# Or specify a port
python3 backend/server.py 8080
```

Open http://localhost:8080 in your browser.

---

## Features

### 1. Constraint-Based Optimization
- **3 Asset Types**: Aircraft, Brigades, Water Trucks
- **8 Constraints**:
  1. Aircraft flight hours
  2. Aircraft range (must return to base)
  3. Brigade travel time
  4. Crew shift limits
  5. Water truck refill cycles
  6. Max simultaneous ops per cluster
  7. Minimum response for high-threat fires
  8. Resource type compatibility

### 2. Real Data Integration
- **NASA FIRMS API**: Live fire detection (VIIRS/MODIS)
- Bounding box: Chubut / Los Alerces National Park
- Falls back to sample data if no API key

### 3. Scenario Analysis
| Scenario | Description |
|----------|-------------|
| Baseline | Current conditions |
| Wind Shift | Configurable wind speed/direction |
| Aircraft Grounded | AC001 unavailable |
| Custom | Mix and match parameters |

### 4. Auditable Decisions
Every dispatch decision includes:
- Inputs used (timestamped)
- Objective value contribution
- Binding constraints
- Human-readable explanation

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/fires` | Active fires (demo data) |
| `GET /api/firms?api_key=KEY` | NASA FIRMS live data |
| `GET /api/resources` | Available resources |
| `GET /api/protected` | Protected assets (towns, parks) |
| `GET /api/optimize?scenario=X&wind_speed=Y` | Run optimization |
| `GET /api/scenarios?wind_speed=35` | Compare to baseline |

### Example: Run optimization with wind shift
```bash
curl "http://localhost:8080/api/optimize?wind_speed=35&wind_direction=270"
```

### Example: Compare scenarios
```bash
curl "http://localhost:8080/api/scenarios?grounded=AC001"
```

---

## Architecture

```
wildfire-ops/
├── backend/
│   ├── optimizer.py    # Core optimization engine
│   └── server.py       # HTTP API server
├── frontend/
│   └── index.html      # Deck.gl visualization
├── run.sh              # Startup script
└── README.md
```

### Optimization Algorithm

**Objective**: Minimize expected damage
```
damage = Σ (fire_threat × (1 - containment_probability))
```

**Method**: Priority-weighted assignment with constraint propagation
1. Rank fires by threat score (proximity to assets × intensity × wind factor)
2. For each fire, find best feasible resource
3. Assign and propagate constraint updates
4. Track binding constraints

*Note: The algorithm is structured to easily upgrade to OR-Tools/PuLP when available.*

---

## Data Sources

### NASA FIRMS
Get a free API key at: https://firms.modaps.eosdis.nasa.gov/api/area/

The system uses **VIIRS_SNPP_NRT** (375m resolution, ~4hr latency).

### Protected Assets (Demo)
| Asset | Type | Priority |
|-------|------|----------|
| Esquel | Town | 0.9 |
| Trevelin | Town | 0.7 |
| Los Alerces NP | National Park | 1.0 |
| Futaleufú Dam | Infrastructure | 0.85 |
| Hospital Zonal | Hospital | 0.95 |

---

## Loom Demo Script

1. **Show the map**: Fire clusters + protected assets
2. **Show resources**: "We have 2 aircraft, 3 brigades, 2 water trucks"
3. **Run baseline**: "This is the optimal allocation"
4. **Toggle wind shift**: "35 km/h from the west"
5. **Re-optimize**: "Notice AC001 and AC002 swapped — Fire F001 is now higher priority because it's upwind of Esquel"
6. **Click Audit tab**: Show the comparison diff
7. **Ground an aircraft**: "AC001 is down for maintenance"
8. **Re-optimize**: Show cascade effects

> **Key message**: "Every decision is explainable. We can trace why each resource was assigned and what changes if conditions change."

---

## Technical Notes

- **No external dependencies required** beyond Python stdlib
- Frontend uses CDN-loaded Deck.gl and MapLibre
- Designed for air-gapped environments (optional FIRMS API)
- Easily upgradable to OR-Tools for true LP/MIP

---

## Why This Matters for Palantir

This demonstrates:
1. **Optimization, not vibes** — real constraint satisfaction
2. **Operational decision support** — not analytics, not dashboards
3. **Auditability** — every decision traceable
4. **Scenario planning** — "what if" at the core
5. **Real-world grounding** — actual fires, actual geography

This is literally what Foundry is used for.
