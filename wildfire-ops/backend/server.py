"""
Wildfire Ops Allocation Engine - HTTP Server
Simple server using Python stdlib - easily upgradable to FastAPI
"""

import http.server
import json
import urllib.parse
import urllib.request
import ssl
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from backend.optimizer import (
    WildfireOptimizer, Fire, Resource, ProtectedAsset, Location,
    AssetType, create_demo_scenario
)

# Cache for FIRMS data
firms_cache = {
    "data": None,
    "timestamp": None,
    "ttl_minutes": 15
}

class WildfireAPIHandler(http.server.BaseHTTPRequestHandler):

    def _send_response(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_file(self, filepath, content_type):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Serve frontend files
        if path == '/' or path == '/index.html':
            self._send_file('frontend/index.html', 'text/html')
            return

        # API endpoints
        if path == '/api/fires':
            self._handle_fires(query)
        elif path == '/api/firms':
            self._handle_firms(query)
        elif path == '/api/resources':
            self._handle_resources()
        elif path == '/api/protected':
            self._handle_protected()
        elif path == '/api/optimize':
            self._handle_optimize(query)
        elif path == '/api/scenarios':
            self._handle_scenarios(query)
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_fires(self, query):
        """Return demo fires with optional FIRMS integration"""
        opt = create_demo_scenario()
        fires = []
        for f in opt.fires:
            fires.append({
                "id": f.id,
                "lat": f.location.lat,
                "lon": f.location.lon,
                "name": f.location.name,
                "intensity": f.intensity,
                "area_km2": f.area_km2,
                "spread_rate": f.spread_rate,
                "threat_score": f.threat_score,
                "cluster_id": f.cluster_id
            })
        self._send_response({"fires": fires, "source": "demo"})

    def _handle_firms(self, query):
        """Fetch NASA FIRMS data for Chubut region"""
        api_key = query.get('api_key', [None])[0]
        days = query.get('days', ['1'])[0]

        if not api_key:
            # Return cached or sample data
            self._send_response({
                "fires": self._get_sample_firms_data(),
                "source": "sample",
                "message": "Using sample data. Provide ?api_key=YOUR_KEY for live FIRMS data"
            })
            return

        # Check cache
        if (firms_cache["data"] and firms_cache["timestamp"] and
            datetime.now() - firms_cache["timestamp"] < timedelta(minutes=firms_cache["ttl_minutes"])):
            self._send_response({
                "fires": firms_cache["data"],
                "source": "cache",
                "cached_at": firms_cache["timestamp"].isoformat()
            })
            return

        # Fetch from FIRMS API
        # Bounding box for Chubut/Los Alerces region
        bbox = "-72.5,-44,-70,-42"  # west, south, east, north

        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{api_key}/VIIRS_SNPP_NRT/{bbox}/{days}"

        try:
            # Create SSL context that doesn't verify certificates (for demo only)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            req = urllib.request.Request(url, headers={'User-Agent': 'WildfireOps/1.0'})
            with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
                csv_data = response.read().decode('utf-8')

            fires = self._parse_firms_csv(csv_data)
            firms_cache["data"] = fires
            firms_cache["timestamp"] = datetime.now()

            self._send_response({
                "fires": fires,
                "source": "FIRMS_API",
                "fetched_at": datetime.now().isoformat(),
                "count": len(fires)
            })

        except Exception as e:
            self._send_response({
                "fires": self._get_sample_firms_data(),
                "source": "sample_fallback",
                "error": str(e),
                "message": "FIRMS API error, using sample data"
            })

    def _parse_firms_csv(self, csv_data):
        """Parse FIRMS CSV response into fire objects"""
        fires = []
        lines = csv_data.strip().split('\n')
        if len(lines) < 2:
            return fires

        headers = lines[0].split(',')
        lat_idx = headers.index('latitude') if 'latitude' in headers else 0
        lon_idx = headers.index('longitude') if 'longitude' in headers else 1
        bright_idx = headers.index('bright_ti4') if 'bright_ti4' in headers else -1
        frp_idx = headers.index('frp') if 'frp' in headers else -1
        conf_idx = headers.index('confidence') if 'confidence' in headers else -1
        date_idx = headers.index('acq_date') if 'acq_date' in headers else -1
        time_idx = headers.index('acq_time') if 'acq_time' in headers else -1

        for i, line in enumerate(lines[1:], 1):
            try:
                parts = line.split(',')
                lat = float(parts[lat_idx])
                lon = float(parts[lon_idx])

                # Compute intensity from brightness/FRP
                intensity = 0.5
                if bright_idx >= 0 and parts[bright_idx]:
                    brightness = float(parts[bright_idx])
                    intensity = min(1.0, (brightness - 300) / 100)
                if frp_idx >= 0 and parts[frp_idx]:
                    frp = float(parts[frp_idx])
                    intensity = min(1.0, frp / 50)

                confidence = 'n'
                if conf_idx >= 0:
                    confidence = parts[conf_idx]

                fires.append({
                    "id": f"FIRMS_{i}",
                    "lat": lat,
                    "lon": lon,
                    "intensity": intensity,
                    "confidence": confidence,
                    "acq_date": parts[date_idx] if date_idx >= 0 else None,
                    "acq_time": parts[time_idx] if time_idx >= 0 else None,
                    "source": "VIIRS"
                })
            except (ValueError, IndexError):
                continue

        return fires

    def _get_sample_firms_data(self):
        """Sample FIRMS-like data for Chubut region"""
        return [
            {"id": "FIRMS_1", "lat": -42.85, "lon": -71.55, "intensity": 0.8, "confidence": "h", "source": "sample"},
            {"id": "FIRMS_2", "lat": -42.78, "lon": -71.62, "intensity": 0.9, "confidence": "h", "source": "sample"},
            {"id": "FIRMS_3", "lat": -42.82, "lon": -71.58, "intensity": 0.7, "confidence": "n", "source": "sample"},
            {"id": "FIRMS_4", "lat": -43.05, "lon": -71.48, "intensity": 0.6, "confidence": "l", "source": "sample"},
            {"id": "FIRMS_5", "lat": -42.95, "lon": -71.65, "intensity": 0.85, "confidence": "h", "source": "sample"},
            {"id": "FIRMS_6", "lat": -42.88, "lon": -71.70, "intensity": 0.65, "confidence": "n", "source": "sample"},
            {"id": "FIRMS_7", "lat": -43.12, "lon": -71.55, "intensity": 0.55, "confidence": "l", "source": "sample"},
        ]

    def _handle_resources(self):
        """Return available resources"""
        opt = create_demo_scenario()
        resources = []
        for r in opt.resources:
            resources.append({
                "id": r.id,
                "type": r.asset_type.value,
                "lat": r.location.lat,
                "lon": r.location.lon,
                "base_lat": r.base_location.lat,
                "base_lon": r.base_location.lon,
                "hours_remaining": r.hours_remaining,
                "max_hours": r.max_hours,
                "capacity": r.capacity,
                "speed_kmh": r.speed_kmh,
                "range_km": r.range_km,
                "status": r.status
            })
        self._send_response({"resources": resources})

    def _handle_protected(self):
        """Return protected assets"""
        opt = create_demo_scenario()
        assets = []
        for a in opt.protected_assets:
            assets.append({
                "id": a.id,
                "lat": a.location.lat,
                "lon": a.location.lon,
                "name": a.location.name,
                "type": a.asset_type,
                "value": a.value,
                "population": a.population
            })
        self._send_response({"protected_assets": assets})

    def _handle_optimize(self, query):
        """Run optimization with optional scenario parameters"""
        scenario = query.get('scenario', ['baseline'])[0]
        wind_speed = float(query.get('wind_speed', ['0'])[0])
        wind_direction = float(query.get('wind_direction', ['0'])[0])
        grounded = query.get('grounded', [''])[0].split(',') if query.get('grounded', [''])[0] else []

        opt = create_demo_scenario()

        if wind_speed > 0 or grounded:
            opt.set_scenario(
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                grounded_aircraft=grounded if grounded else None
            )

        plan = opt.optimize(scenario)
        result = plan.to_dict()

        # Add fire and resource data to response
        result["fires"] = [
            {
                "id": f.id, "lat": f.location.lat, "lon": f.location.lon,
                "threat_score": round(f.threat_score, 2), "intensity": f.intensity
            }
            for f in opt.fires
        ]
        result["resources"] = [
            {
                "id": r.id, "type": r.asset_type.value,
                "lat": r.location.lat, "lon": r.location.lon,
                "status": r.status
            }
            for r in opt.resources
        ]

        self._send_response(result)

    def _handle_scenarios(self, query):
        """Compare two scenarios and return diff"""
        opt_base = create_demo_scenario()
        baseline = opt_base.optimize("baseline")

        wind_speed = float(query.get('wind_speed', ['35'])[0])
        wind_direction = float(query.get('wind_direction', ['270'])[0])
        grounded = query.get('grounded', [''])[0].split(',') if query.get('grounded', [''])[0] else []

        opt_alt = create_demo_scenario()
        opt_alt.set_scenario(
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            grounded_aircraft=grounded if grounded else None
        )
        alt_plan = opt_alt.optimize("scenario_alt")

        comparison = opt_alt.compare_scenarios(baseline, alt_plan)

        self._send_response({
            "baseline": baseline.to_dict(),
            "alternative": alt_plan.to_dict(),
            "comparison": comparison
        })

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def run_server(port=8080):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, WildfireAPIHandler)
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║     🔥 WILDFIRE OPS ALLOCATION ENGINE                        ║
║     Chubut / Los Alerces Region                              ║
╠══════════════════════════════════════════════════════════════╣
║  Server running at: http://localhost:{port}                    ║
║                                                              ║
║  API Endpoints:                                              ║
║    GET /api/fires     - Active fires (demo data)             ║
║    GET /api/firms     - NASA FIRMS data (?api_key=...)       ║
║    GET /api/resources - Available resources                  ║
║    GET /api/protected - Protected assets                     ║
║    GET /api/optimize  - Run allocation optimization          ║
║    GET /api/scenarios - Compare scenarios                    ║
║                                                              ║
║  Scenario parameters for /api/optimize:                      ║
║    ?wind_speed=35&wind_direction=270                         ║
║    ?grounded=AC001,AC002                                     ║
║    ?scenario=wind_shift                                      ║
║                                                              ║
║  Press Ctrl+C to stop                                        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    httpd.serve_forever()


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
