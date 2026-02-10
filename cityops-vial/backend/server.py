"""
CityOps Vial - HTTP Server
API REST para gestión de incidentes viales
"""

import http.server
import json
import urllib.parse
from datetime import datetime, timedelta
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import IncidentStatus, AssignmentStatus, generate_id
from data_store import get_data_store
from jurisdiction_engine import get_jurisdiction_engine
from scoring_engine import get_scoring_engine, SLAUrgencyCalculator
from dispatch_optimizer import get_optimizer, create_assignment_from_recommendation


class CityOpsAPIHandler(http.server.BaseHTTPRequestHandler):
    """Handler para todas las rutas de la API"""

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, default=str).encode('utf-8'))

    def _send_file(self, filepath, content_type):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def _get_body(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length:
            return json.loads(self.rfile.read(content_length).decode('utf-8'))
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Frontend
        if path == '/' or path == '/index.html':
            self._send_file('../frontend/index.html', 'text/html')
            return

        # API Routes
        routes = {
            '/api/v1/incidents': self._handle_get_incidents,
            '/api/v1/crews': self._handle_get_crews,
            '/api/v1/jurisdictions': self._handle_get_jurisdictions,
            '/api/v1/authorities': self._handle_get_authorities,
            '/api/v1/assignments': self._handle_get_assignments,
            '/api/v1/analytics/kpis': self._handle_get_kpis,
            '/api/v1/jurisdictions/lookup': self._handle_jurisdiction_lookup,
        }

        # Check exact routes
        if path in routes:
            routes[path](query)
            return

        # Check parameterized routes
        if path.startswith('/api/v1/incidents/') and '/score' not in path:
            incident_id = path.split('/')[-1]
            self._handle_get_incident(incident_id)
            return

        if path.startswith('/api/v1/incidents/') and path.endswith('/score'):
            parts = path.split('/')
            incident_id = parts[-2]
            self._handle_get_incident_score(incident_id)
            return

        if path.startswith('/api/v1/crews/'):
            crew_id = path.split('/')[-1]
            self._handle_get_crew(crew_id)
            return

        self._send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._get_body()

        routes = {
            '/api/v1/incidents': self._handle_create_incident,
            '/api/v1/assignments/optimize': self._handle_optimize,
            '/api/v1/assignments': self._handle_create_assignment,
        }

        if path in routes:
            routes[path](body)
            return

        if path.startswith('/api/v1/crews/') and path.endswith('/location'):
            crew_id = path.split('/')[-2]
            self._handle_update_crew_location(crew_id, body)
            return

        self._send_json({'error': 'Not found'}, 404)

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self._get_body()

        if path.startswith('/api/v1/incidents/'):
            incident_id = path.split('/')[-1]
            self._handle_update_incident(incident_id, body)
            return

        if path.startswith('/api/v1/assignments/'):
            assignment_id = path.split('/')[-1]
            self._handle_update_assignment(assignment_id, body)
            return

        if path.startswith('/api/v1/crews/'):
            crew_id = path.split('/')[-1]
            self._handle_update_crew(crew_id, body)
            return

        self._send_json({'error': 'Not found'}, 404)

    # =============================================
    # INCIDENTS
    # =============================================

    def _handle_get_incidents(self, query):
        store = get_data_store()

        status = query.get('status', [])
        if status and isinstance(status[0], str) and ',' in status[0]:
            status = status[0].split(',')

        jurisdiction_id = query.get('jurisdiction_id', [None])[0]
        authority_id = query.get('authority_id', [None])[0]
        severity = query.get('severity', [])
        if severity and isinstance(severity[0], str) and ',' in severity[0]:
            severity = severity[0].split(',')

        min_risk = query.get('min_risk_score', [None])[0]
        min_risk = float(min_risk) if min_risk else None

        bbox = query.get('bbox', [None])[0]
        if bbox:
            bbox = tuple(map(float, bbox.split(',')))

        limit = int(query.get('limit', ['100'])[0])

        incidents = store.get_incidents(
            status=status or None,
            jurisdiction_id=jurisdiction_id,
            authority_id=authority_id,
            severity=severity or None,
            min_risk_score=min_risk,
            bbox=bbox,
            limit=limit
        )

        # Enrich with jurisdiction/authority names
        jur_engine = get_jurisdiction_engine()
        result = []
        for inc in incidents:
            d = inc.to_dict()
            if inc.jurisdiction_id:
                jur = jur_engine.get_jurisdiction_by_id(inc.jurisdiction_id)
                d['jurisdiction_name'] = jur.name if jur else None
            if inc.authority_id:
                auth = jur_engine.get_authority_by_id(inc.authority_id)
                d['authority_name'] = auth.name if auth else None
            result.append(d)

        self._send_json({
            'data': result,
            'count': len(result),
            'total': len(store.incidents)
        })

    def _handle_get_incident(self, incident_id):
        store = get_data_store()
        incident = store.get_incident(incident_id)

        if not incident:
            self._send_json({'error': 'Incident not found'}, 404)
            return

        jur_engine = get_jurisdiction_engine()
        d = incident.to_dict()

        if incident.jurisdiction_id:
            jur = jur_engine.get_jurisdiction_by_id(incident.jurisdiction_id)
            d['jurisdiction'] = jur.to_dict() if jur else None

        if incident.authority_id:
            auth = jur_engine.get_authority_by_id(incident.authority_id)
            d['authority'] = auth.to_dict() if auth else None

        if incident.current_assignment_id:
            assignment = store.get_assignment(incident.current_assignment_id)
            if assignment:
                d['current_assignment'] = assignment.to_dict()
                crew = store.get_crew(assignment.crew_id)
                if crew:
                    d['current_assignment']['crew'] = crew.to_dict()

        # SLA details
        d['sla_details'] = SLAUrgencyCalculator.get_sla_status_details(incident)

        # Audit log
        audit = store.get_audit_log(entity_type='incident', entity_id=incident_id, limit=20)
        d['audit_trail'] = [e.to_dict() for e in audit]

        self._send_json(d)

    def _handle_get_incident_score(self, incident_id):
        store = get_data_store()
        scoring_engine = get_scoring_engine()
        jur_engine = get_jurisdiction_engine()

        incident = store.get_incident(incident_id)
        if not incident:
            self._send_json({'error': 'Incident not found'}, 404)
            return

        segment = None
        if incident.road_segment_id:
            segment = next((s for s in jur_engine.road_segments if s.id == incident.road_segment_id), None)

        score_details = scoring_engine.compute_risk_score(incident, segment)
        self._send_json(score_details)

    def _handle_create_incident(self, body):
        store = get_data_store()

        required = ['location']
        for field in required:
            if field not in body:
                self._send_json({'error': f'Missing required field: {field}'}, 400)
                return

        if 'lat' not in body['location'] or 'lon' not in body['location']:
            self._send_json({'error': 'Location must have lat and lon'}, 400)
            return

        incident = store.create_incident(body)

        self._send_json({
            'id': incident.id,
            'status': incident.status.value,
            'tracking_code': f"INC-{datetime.now().year}-{incident.id[:8].upper()}",
            'message': 'Reporte recibido. Gracias por contribuir a mejorar nuestras calles.',
            'jurisdiction': incident.jurisdiction_id,
            'authority': incident.authority_id,
            'risk_score': incident.risk_score,
            'sla_deadline': incident.sla_deadline.isoformat() if incident.sla_deadline else None
        }, 201)

    def _handle_update_incident(self, incident_id, body):
        store = get_data_store()
        incident = store.update_incident(incident_id, body)

        if not incident:
            self._send_json({'error': 'Incident not found'}, 404)
            return

        self._send_json(incident.to_dict())

    # =============================================
    # CREWS
    # =============================================

    def _handle_get_crews(self, query):
        store = get_data_store()
        jur_engine = get_jurisdiction_engine()

        authority_id = query.get('authority_id', [None])[0]
        status = query.get('status', [])
        if status and isinstance(status[0], str) and ',' in status[0]:
            status = status[0].split(',')
        available_only = query.get('available_only', ['false'])[0].lower() == 'true'

        crews = store.get_crews(
            authority_id=authority_id,
            status=status or None,
            available_only=available_only
        )

        result = []
        for crew in crews:
            d = crew.to_dict()
            auth = jur_engine.get_authority_by_id(crew.authority_id)
            d['authority_name'] = auth.name if auth else None
            result.append(d)

        self._send_json({'data': result, 'count': len(result)})

    def _handle_get_crew(self, crew_id):
        store = get_data_store()
        crew = store.get_crew(crew_id)

        if not crew:
            self._send_json({'error': 'Crew not found'}, 404)
            return

        jur_engine = get_jurisdiction_engine()
        d = crew.to_dict()
        auth = jur_engine.get_authority_by_id(crew.authority_id)
        d['authority'] = auth.to_dict() if auth else None

        # Active assignments
        assignments = store.get_assignments(crew_id=crew_id, status=['pending', 'en_route', 'on_site'])
        d['active_assignments'] = [a.to_dict() for a in assignments]

        self._send_json(d)

    def _handle_update_crew_location(self, crew_id, body):
        store = get_data_store()

        if 'lat' not in body or 'lon' not in body:
            self._send_json({'error': 'lat and lon required'}, 400)
            return

        crew = store.update_crew_location(crew_id, body['lat'], body['lon'])

        if not crew:
            self._send_json({'error': 'Crew not found'}, 404)
            return

        self._send_json({'received': True, 'processed_at': datetime.now().isoformat()})

    def _handle_update_crew(self, crew_id, body):
        store = get_data_store()

        if 'status' in body:
            crew = store.update_crew_status(crew_id, body['status'])
            if not crew:
                self._send_json({'error': 'Crew not found'}, 404)
                return
            self._send_json(crew.to_dict())
        else:
            self._send_json({'error': 'No updates provided'}, 400)

    # =============================================
    # ASSIGNMENTS
    # =============================================

    def _handle_get_assignments(self, query):
        store = get_data_store()

        incident_id = query.get('incident_id', [None])[0]
        crew_id = query.get('crew_id', [None])[0]
        status = query.get('status', [])
        if status and isinstance(status[0], str) and ',' in status[0]:
            status = status[0].split(',')

        assignments = store.get_assignments(
            incident_id=incident_id,
            crew_id=crew_id,
            status=status or None
        )

        result = []
        for a in assignments:
            d = a.to_dict()
            incident = store.get_incident(a.incident_id)
            crew = store.get_crew(a.crew_id)
            d['incident_address'] = incident.address_text if incident else None
            d['crew_name'] = crew.name if crew else None
            result.append(d)

        self._send_json({'data': result, 'count': len(result)})

    def _handle_optimize(self, body):
        store = get_data_store()
        optimizer = get_optimizer()

        authority_id = body.get('authority_id')
        time_horizon = body.get('time_horizon_hours', 8)
        prioritize_critical = body.get('prioritize_critical', True)

        incidents = list(store.incidents.values())
        crews = list(store.crews.values())

        plan = optimizer.optimize(
            incidents=incidents,
            crews=crews,
            authority_id=authority_id,
            time_horizon_hours=time_horizon,
            prioritize_critical=prioritize_critical
        )

        self._send_json(plan.to_dict())

    def _handle_create_assignment(self, body):
        store = get_data_store()

        if 'incident_id' not in body or 'crew_id' not in body:
            self._send_json({'error': 'incident_id and crew_id required'}, 400)
            return

        assignment = store.create_assignment(
            incident_id=body['incident_id'],
            crew_id=body['crew_id'],
            optimizer_data=body.get('optimizer_data')
        )

        if not assignment:
            self._send_json({'error': 'Invalid incident_id or crew_id'}, 400)
            return

        self._send_json(assignment.to_dict(), 201)

    def _handle_update_assignment(self, assignment_id, body):
        store = get_data_store()
        assignment = store.update_assignment(assignment_id, body)

        if not assignment:
            self._send_json({'error': 'Assignment not found'}, 404)
            return

        self._send_json(assignment.to_dict())

    # =============================================
    # JURISDICTIONS
    # =============================================

    def _handle_get_jurisdictions(self, query):
        jur_engine = get_jurisdiction_engine()
        level = query.get('level', [None])[0]

        jurisdictions = jur_engine.jurisdictions
        if level:
            jurisdictions = [j for j in jurisdictions if j.level.value == level]

        self._send_json({'data': [j.to_dict() for j in jurisdictions]})

    def _handle_get_authorities(self, query):
        jur_engine = get_jurisdiction_engine()
        jurisdiction_id = query.get('jurisdiction_id', [None])[0]

        authorities = jur_engine.authorities
        if jurisdiction_id:
            authorities = [a for a in authorities if a.jurisdiction_id == jurisdiction_id]

        self._send_json({'data': [a.to_dict() for a in authorities]})

    def _handle_jurisdiction_lookup(self, query):
        jur_engine = get_jurisdiction_engine()

        lat = query.get('lat', [None])[0]
        lon = query.get('lon', [None])[0]

        if not lat or not lon:
            self._send_json({'error': 'lat and lon required'}, 400)
            return

        from models import Location
        location = Location(float(lat), float(lon))

        jur, auth, segment = jur_engine.determine_responsibility(location)

        response = {
            'location': location.to_dict(),
            'jurisdiction': jur.to_dict() if jur else None,
            'authority': auth.to_dict() if auth else None,
            'road_segment': segment.to_dict() if segment else None
        }

        if jur:
            response_h, resolution_h = jur_engine.get_sla_for_incident(type('obj', (object,), {'severity_estimate': type('obj', (object,), {'value': 'medium'})(), 'jurisdiction_id': jur.id})())
            response['applicable_sla'] = {
                'response_hours': response_h,
                'resolution_hours': resolution_h
            }

        self._send_json(response)

    # =============================================
    # ANALYTICS
    # =============================================

    def _handle_get_kpis(self, query):
        store = get_data_store()

        from_date = query.get('from_date', [None])[0]
        to_date = query.get('to_date', [None])[0]

        if from_date:
            from_date = datetime.fromisoformat(from_date.replace('Z', ''))
        if to_date:
            to_date = datetime.fromisoformat(to_date.replace('Z', ''))

        kpis = store.compute_kpis(from_date, to_date)
        self._send_json(kpis.to_dict())

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def run_server(port=8080):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = http.server.HTTPServer(('', port), CityOpsAPIHandler)

    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║     🛣️  CITYOPS VIAL - Sistema de Gestión de Incidentes Viales       ║
║     CABA + GBA | Argentina                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Servidor: http://localhost:{port}                                     ║
║                                                                      ║
║  API Endpoints:                                                      ║
║    GET  /api/v1/incidents         - Listar incidentes                ║
║    POST /api/v1/incidents         - Crear incidente                  ║
║    GET  /api/v1/incidents/:id     - Detalle de incidente             ║
║    PATCH /api/v1/incidents/:id    - Actualizar incidente             ║
║                                                                      ║
║    GET  /api/v1/crews             - Listar cuadrillas                ║
║    GET  /api/v1/crews/:id         - Detalle de cuadrilla             ║
║    POST /api/v1/crews/:id/location - Actualizar ubicación            ║
║                                                                      ║
║    POST /api/v1/assignments/optimize - Ejecutar optimizador          ║
║    POST /api/v1/assignments       - Crear asignación                 ║
║    PATCH /api/v1/assignments/:id  - Actualizar asignación            ║
║                                                                      ║
║    GET  /api/v1/jurisdictions     - Listar jurisdicciones            ║
║    GET  /api/v1/jurisdictions/lookup?lat=&lon= - Buscar jurisdicción ║
║    GET  /api/v1/authorities       - Listar autoridades               ║
║                                                                      ║
║    GET  /api/v1/analytics/kpis    - Dashboard KPIs                   ║
║                                                                      ║
║  Press Ctrl+C to stop                                                ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    server.serve_forever()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)
