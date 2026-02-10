"""
OptiSolve API — FastAPI Backend
Plataforma Inteligente de Investigación Operativa
"""
import os
import sys
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from solvers.lp_solver import solve_lp
from solvers.stock_solver import solve_stock
from solvers.queue_solver import solve_queue
from rag.indexer import RAGIndex, get_index
from conversational.engine import (
    detect_module, detect_subtype, extract_stock_params, extract_queue_params,
    get_missing_params, generate_confirmation
)
from models.problem_spec import (
    ModuleType, ProblemSpec, SolveRequest, ConversationRequest, ConversationMessage
)

# ─── APP ────────────────────────────────────────────────────
app = FastAPI(
    title="OptiSolve API",
    description="Plataforma Inteligente de Investigación Operativa",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── RAG INDEX ──────────────────────────────────────────────
PDF_DIR = os.environ.get("OPTISOLVE_PDF_DIR",
    "/sessions/nice-eloquent-cori/mnt/Investigacion Operativa")
INDEX_PATH = os.path.join(PDF_DIR, ".rag_index.pkl")

rag_index = get_index()

@app.on_event("startup")
async def startup():
    """Load or build RAG index on startup."""
    if os.path.exists(INDEX_PATH):
        try:
            rag_index.load(INDEX_PATH)
            print(f"RAG index loaded: {len(rag_index.chunks)} chunks")
        except Exception as e:
            print(f"Failed to load index: {e}. Rebuilding...")
            rag_index.index_pdfs(PDF_DIR)
            rag_index.save(INDEX_PATH)
    else:
        print("Building RAG index from PDFs...")
        rag_index.index_pdfs(PDF_DIR)
        rag_index.save(INDEX_PATH)


# ─── SESSIONS (in-memory for MVP) ──────────────────────────
sessions: Dict[str, Dict] = {}


def get_session(session_id: str = None) -> Dict:
    if session_id and session_id in sessions:
        return sessions[session_id]
    sid = session_id or str(uuid.uuid4())
    sessions[sid] = {
        "id": sid,
        "module": None,
        "subtype": None,
        "params": {},
        "assumptions": [],
        "stage": "detect_module",  # detect_module -> collect_params -> confirm -> solve
        "history": [],
        "problem_spec": None,
        "solution": None,
    }
    return sessions[sid]


# ─── API ROUTES ─────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "rag_indexed": rag_index.is_indexed,
        "rag_chunks": len(rag_index.chunks) if rag_index.is_indexed else 0,
    }


@app.post("/api/solve")
async def solve_direct(request: SolveRequest):
    """
    Direct solve endpoint. Receives structured params, returns solution.
    Used when the frontend has already collected all parameters.
    """
    module = request.module.value
    params = request.params

    try:
        if module == "LP":
            result = solve_lp(params)
        elif module == "STOCK":
            subtype = request.subtype or detect_subtype("STOCK", "", params)
            spec = {"subtype": subtype, "model_spec": params}
            result = solve_stock(spec)
        elif module == "QUEUE":
            subtype = request.subtype or detect_subtype("QUEUE", "", params)
            spec = {"subtype": subtype, "model_spec": params}
            result = solve_queue(spec)
        else:
            raise HTTPException(400, f"Módulo no soportado: {module}")

        # Enrich with RAG citations
        if rag_index.is_indexed:
            book_filter = {
                "LP": "programacion_lineal",
                "STOCK": "stocks",
                "QUEUE": "teoria_colas",
            }.get(module)
            citations = rag_index.search(
                request.user_input or f"modelo {subtype}",
                top_k=3,
                book_filter=book_filter,
            )
            result["rag_citations"] = citations

        return result

    except Exception as e:
        raise HTTPException(500, f"Error al resolver: {str(e)}")


@app.post("/api/chat")
async def chat(request: ConversationRequest):
    """
    Conversational endpoint. Guides the user through problem definition.
    Returns: {response, session_id, stage, data}
    """
    session = get_session(request.session_id)
    user_msg = request.message.strip()

    session["history"].append({"role": "user", "content": user_msg})

    response_data = {}

    # ─── Stage: Detect Module ───────────────────────────────
    if session["stage"] == "detect_module":
        module, confidence = detect_module(user_msg)

        if module and confidence >= 0.3:
            session["module"] = module
            session["stage"] = "collect_params"

            # Try to extract params from initial message
            if module == "STOCK":
                params = extract_stock_params(user_msg)
                session["params"].update(params)
            elif module == "QUEUE":
                params = extract_queue_params(user_msg)
                session["params"].update(params)

            # Check what's missing
            missing = get_missing_params(module, session["params"])

            if not missing:
                # All params detected! Move to confirm
                session["stage"] = "confirm"
                subtype = detect_subtype(module, user_msg, session["params"])
                session["subtype"] = subtype
                confirmation = generate_confirmation(module, subtype, session["params"], session["assumptions"])
                response = confirmation
                response_data = {"params": session["params"], "module": module, "subtype": subtype}
            else:
                # Ask first missing question
                q = missing[0]
                module_names = {"LP": "Programación Lineal", "STOCK": "Inventarios", "QUEUE": "Teoría de Colas"}
                response = (
                    f"Perfecto, detecto que es un problema de **{module_names.get(module, module)}**. "
                    f"Voy a necesitar algunos datos.\n\n"
                    f"**{q['question']}**\n\n"
                    f"_({q['why']})_"
                )
                if "options" in q:
                    response += "\n\nOpciones:\n" + "\n".join(f"- {o}" for o in q["options"])

                response_data = {"missing_params": [m["key"] for m in missing], "module": module}

        else:
            response = (
                "No pude identificar claramente el tipo de problema. ¿Podrías indicarme cuál de estos se acerca más?\n\n"
                "1. **Programación Lineal**: Decidir cuánto producir/asignar con recursos limitados.\n"
                "2. **Inventarios/Stocks**: Decidir cuánto pedir y cada cuánto para minimizar costos.\n"
                "3. **Teoría de Colas**: Analizar tiempos de espera y decidir cuántos servidores necesitás.\n\n"
                "Podés elegir un número o describir tu problema con más detalle."
            )
            # Check if user selected by number
            if user_msg.strip() in ["1", "2", "3"]:
                module_map = {"1": "LP", "2": "STOCK", "3": "QUEUE"}
                session["module"] = module_map[user_msg.strip()]
                session["stage"] = "collect_params"
                response = f"Entendido. Describí tu problema y voy a extraer los datos necesarios."

    # ─── Stage: Collect Params ──────────────────────────────
    elif session["stage"] == "collect_params":
        module = session["module"]

        # Extract params from this message
        if module == "STOCK":
            new_params = extract_stock_params(user_msg)
        elif module == "QUEUE":
            new_params = extract_queue_params(user_msg)
        else:
            new_params = {}

        # Also try to parse direct number answers
        numbers = []
        try:
            numbers = [float(user_msg.replace(",", ".").replace("$", "").strip())]
        except:
            pass

        session["params"].update(new_params)

        # Handle yes/no for shortage/capacity questions
        lower = user_msg.lower()
        if any(w in lower for w in ["nunca", "no falt", "siempre tener", "no puede"]):
            session["params"]["shortage_cost_c2"] = None
            session["assumptions"].append("No se admiten faltantes de stock.")
        if any(w in lower for w in ["sí faltante", "a veces", "puedo quedarme"]):
            session["assumptions"].append("Se admiten faltantes con costo c2.")
        if any(w in lower for w in ["sin límite", "puede crecer", "no hay límite"]):
            session["params"]["system_capacity_N"] = None
            session["assumptions"].append("Capacidad del sistema infinita (sin límite de espera).")
        if any(w in lower for w in ["colchón", "seguridad", "sí.*protección"]):
            if "safety_stock_Sp" not in session["params"]:
                # Default: 3 days of demand
                D = session["params"].get("demand_D", 0)
                if D > 0:
                    Sp = round(3 * D / 365)
                    session["params"]["safety_stock_Sp"] = Sp
                    session["assumptions"].append(f"Stock de protección = {Sp} unidades (≈ 3 días de demanda).")
        if any(w in lower for w in ["no.*seguridad", "no.*colchón", "confío"]):
            session["params"]["safety_stock_Sp"] = 0

        # Check what's still missing
        missing = get_missing_params(module, session["params"])

        if not missing:
            session["stage"] = "confirm"
            subtype = detect_subtype(module, " ".join(h["content"] for h in session["history"]), session["params"])
            session["subtype"] = subtype

            # Add default assumptions
            if module == "STOCK" and "shortage_cost_c2" not in session["params"]:
                session["params"]["shortage_cost_c2"] = None
                session["assumptions"].append("No se admiten faltantes.")
            if module == "STOCK":
                session["assumptions"].append("Demanda constante e independiente.")
                session["assumptions"].append("Reposición instantánea.")
                session["params"].setdefault("planning_horizon_T", 1.0)
                session["params"].setdefault("safety_stock_Sp", 0)
            if module == "QUEUE":
                session["assumptions"].append("Llegadas Poisson, tiempos de servicio exponenciales.")
                session["assumptions"].append("Disciplina FIFO.")

            confirmation = generate_confirmation(module, subtype, session["params"], session["assumptions"])
            response = confirmation
            response_data = {"params": session["params"], "module": module, "subtype": subtype}
        else:
            q = missing[0]
            response = f"**{q['question']}**\n\n_({q['why']})_"
            if "options" in q:
                response += "\n\nOpciones:\n" + "\n".join(f"- {o}" for o in q["options"])
            response_data = {"missing_params": [m["key"] for m in missing]}

    # ─── Stage: Confirm ─────────────────────────────────────
    elif session["stage"] == "confirm":
        lower = user_msg.lower()
        if any(w in lower for w in ["sí", "si", "correcto", "dale", "ok", "resolver", "adelante", "confirm"]):
            session["stage"] = "solving"
            # Solve!
            result = _do_solve(session)
            session["solution"] = result
            session["stage"] = "solved"

            response = _format_solution(session["module"], session["subtype"], result)
            response_data = {"solution": result, "module": session["module"]}
        else:
            response = "Entendido. ¿Qué dato querés ajustar? Decime el nuevo valor."
            session["stage"] = "collect_params"

    # ─── Stage: Solved ──────────────────────────────────────
    elif session["stage"] == "solved":
        lower = user_msg.lower()
        if any(w in lower for w in ["sensibilidad", "qué pasa si", "cambiar", "variar"]):
            result = session.get("solution", {})
            sens = result.get("sensitivity", {})
            if sens:
                response = _format_sensitivity(session["module"], sens)
            else:
                response = "No hay análisis de sensibilidad disponible para este resultado."
            response_data = {"sensitivity": sens}
        elif any(w in lower for w in ["nuevo", "otro problema", "empezar"]):
            old_sid = session["id"]
            sessions.pop(old_sid, None)
            session = get_session()
            response = "Perfecto, empezamos de nuevo. Describí tu nuevo problema."
            response_data = {"session_id": session["id"]}
        else:
            response = (
                "El problema ya está resuelto. Podés:\n"
                "- Preguntarme sobre **sensibilidad** (¿qué pasa si cambian los datos?)\n"
                "- Pedirme un **nuevo problema**\n"
                "- Preguntarme detalles sobre el resultado"
            )

    else:
        response = "Describí tu problema operativo y voy a ayudarte a resolverlo."

    session["history"].append({"role": "assistant", "content": response})

    return {
        "response": response,
        "session_id": session["id"],
        "stage": session["stage"],
        "module": session.get("module"),
        "data": response_data,
    }


def _do_solve(session: Dict) -> Dict:
    """Execute the solver based on session state."""
    module = session["module"]
    params = session["params"]
    subtype = session.get("subtype", "")

    if module == "LP":
        return solve_lp(params)
    elif module == "STOCK":
        spec = {"subtype": subtype, "model_spec": params}
        return solve_stock(spec)
    elif module == "QUEUE":
        spec = {"subtype": subtype, "model_spec": params}
        return solve_queue(spec)
    return {"status": "ERROR", "message": f"Módulo no soportado: {module}"}


def _format_solution(module: str, subtype: str, result: Dict) -> str:
    """Format solution as Markdown for chat display."""
    if result.get("status") in ("ERROR", "INFACTIBLE", "NO_ACOTADO", "INESTABLE"):
        return f"⚠️ **{result['status']}**: {result.get('message', 'Error desconocido')}"

    lines = [f"✅ **Solución encontrada** — Modelo: {result.get('model', subtype)}\n"]

    # Decision summary
    decision = result.get("decision", {})
    if decision:
        lines.append(f"**{decision.get('summary', '')}**\n")
        for action in decision.get("actions", []):
            lines.append(f"• {action}")

    # Key metrics
    results = result.get("results", {})
    if module == "STOCK":
        lines.append(f"\n**Resultados clave:**")
        if "qo" in results:
            lines.append(f"• Lote óptimo (qo): **{results['qo']:.0f} unidades**")
        if "to_days" in results:
            lines.append(f"• Intervalo entre pedidos: **{results['to_days']:.1f} días**")
        if "SR_reorder_point" in results:
            lines.append(f"• Punto de reorden: **{results['SR_reorder_point']:.0f} unidades**")
        if "CTE" in results:
            lines.append(f"• Costo total anual: **${results['CTE']:,.2f}**")

    elif module == "QUEUE":
        lines.append(f"\n**Métricas del sistema:**")
        if "rho" in results or "rho_per_server" in results:
            rho = results.get("rho_per_server", results.get("rho", 0))
            lines.append(f"• Utilización (ρ): **{rho*100:.1f}%**")
        if "Wc_minutes" in results:
            lines.append(f"• Espera promedio en cola: **{results['Wc_minutes']:.1f} minutos**")
        if "Lc" in results:
            lines.append(f"• Clientes en cola promedio: **{results['Lc']:.2f}**")
        if "L" in results:
            lines.append(f"• Clientes en sistema: **{results['L']:.2f}**")
        if "prob_wait" in results:
            lines.append(f"• Probabilidad de esperar: **{results['prob_wait']*100:.1f}%**")

    elif module == "LP":
        lines.append(f"\n**Resultados:**")
        if "objective_value" in result:
            lines.append(f"• Valor óptimo Z: **${result['objective_value']:,.2f}**")
        for var, val in result.get("variable_values", {}).items():
            lines.append(f"• {var} = **{val}**")

    # Economic analysis (queues)
    econ = result.get("economic_analysis")
    if econ and econ.get("comparisons"):
        lines.append(f"\n**Análisis económico:**")
        for comp in econ["comparisons"]:
            if comp.get("status") == "ESTABLE":
                marker = " ← ÓPTIMO" if comp.get("is_optimal") else ""
                lines.append(
                    f"• M={comp['M']}: espera {comp['Wc_minutes']:.1f}min, "
                    f"costo ${comp['cost_total_per_hour']:.0f}/hr{marker}"
                )

    # Warnings
    for w in result.get("warnings", []):
        lines.append(f"\n⚠️ {w}")

    lines.append("\n---\n_Podés preguntarme sobre el análisis de sensibilidad o plantear un nuevo problema._")

    return "\n".join(lines)


def _format_sensitivity(module: str, sensitivity: Dict) -> str:
    """Format sensitivity analysis as Markdown."""
    lines = ["📊 **Análisis de Sensibilidad**\n"]

    if module == "STOCK":
        table = sensitivity.get("sensitivity_table", [])
        if table:
            lines.append("| α (q/qo) | q | λ | Error (ε) | CTE variable |")
            lines.append("|----------|---|---|-----------|-------------|")
            for row in table:
                lines.append(
                    f"| {row['alpha']:.2f} | {row['q']:.0f} | {row['lambda']:.4f} | "
                    f"{row['epsilon_pct']:.2f}% | ${row['cte_variable']:,.0f} |"
                )
        interp = sensitivity.get("interpretation", "")
        if interp:
            lines.append(f"\n{interp}")

    elif module == "QUEUE":
        lam_sens = sensitivity.get("lambda_sensitivity", [])
        if lam_sens:
            lines.append("| Factor λ | λ | ρ | L | Wc (min) | Estado |")
            lines.append("|----------|---|---|---|----------|--------|")
            for row in lam_sens:
                if row["status"] == "ESTABLE":
                    lines.append(
                        f"| {row['lambda_factor']:.1f} | {row['lambda']:.1f} | {row['rho']:.3f} | "
                        f"{row.get('L', '-')} | {row.get('Wc_minutes', '-')} | ✅ |"
                    )
                else:
                    lines.append(
                        f"| {row['lambda_factor']:.1f} | {row['lambda']:.1f} | {row['rho']:.3f} | "
                        f"∞ | ∞ | ❌ INESTABLE |"
                    )

    elif module == "LP":
        for name, info in sensitivity.get("rhs_ranges", {}).items():
            if info.get("binding"):
                lines.append(f"• **{name}** (saturado): precio sombra = ${info.get('shadow_price', '?')}")
            else:
                lines.append(f"• **{name}**: holgura de {info.get('slack', '?')} unidades")

        for interp in sensitivity.get("interpretation", []):
            lines.append(f"\n{interp}")

    return "\n".join(lines)


@app.get("/api/rag/search")
async def rag_search(query: str, book: str = None, top_k: int = 5):
    """Search the RAG index directly."""
    if not rag_index.is_indexed:
        raise HTTPException(503, "RAG index not ready")
    results = rag_index.search(query, top_k=top_k, book_filter=book)
    return {"results": results}


@app.get("/api/sessions/{session_id}")
async def get_session_info(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    s = sessions[session_id]
    return {
        "id": s["id"],
        "module": s["module"],
        "subtype": s["subtype"],
        "stage": s["stage"],
        "params": s["params"],
        "assumptions": s["assumptions"],
    }


# ─── SERVE FRONTEND ────────────────────────────────────────
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
async def serve_frontend():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "OptiSolve API running. Frontend not found."}

# Mount static files if frontend exists
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
