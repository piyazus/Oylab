import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from dotenv import load_dotenv

from analyzer import analyze_pitch
from schemas import AnalyzeResponse, ApiError, AuthSignup, AuthLogin
from supabase_client import supabase

load_dotenv()

MAX_FILE_MB = int(os.getenv("MAX_FILE_MB", "16"))
MAX_CONTENT_LENGTH = MAX_FILE_MB * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
CORS(app, resources={r"/*": {"origins": os.getenv("ALLOWED_ORIGINS", "*").split(",")}})

def ok(data, status=200):
    return jsonify(data), status


# -------- Errors --------
@app.errorhandler(RequestEntityTooLarge)
def too_large(_):
    return ok(ApiError(error=f"File too large. Max {MAX_FILE_MB}MB").model_dump(), 413)


# -------- Health --------
@app.get("/health")
def health():
    return ok({"ok": True, "service": "oylab-ai", "version": "full-backend"})


# -------- Analyze (PDF/PPT) --------
@app.post("/analyze")
def analyze():
    if "file" not in request.files:
        return ok(ApiError(error="No file field").model_dump(), 400)
    f = request.files["file"]
    if not f.filename:
        return ok(ApiError(error="Empty filename").model_dump(), 400)

    name = f.filename.lower()
    if not (name.endswith(".pdf") or name.endswith(".ppt") or name.endswith(".pptx")):
        return ok(ApiError(error="Unsupported file type (PDF/PPT/PPTX)").model_dump(), 400)

    try:
        result = analyze_pitch(f)  # dict: score, breakdown, recommendations
        _maybe_persist_analysis(request, f.filename, result)
        return ok(AnalyzeResponse(**result).model_dump())
    except Exception as ex:
        return ok(ApiError(error=f"Analyzer error: {ex}").model_dump(), 500)


def _maybe_persist_analysis(req, filename: str, result: dict):
    """Сохраняем анализ в Supabase, если клиент и таблица настроены."""
    if not supabase:
        return
    try:
        user_id = _get_user_id_from_auth(req)
        table = os.getenv("SUPABASE_RESULTS_TABLE", "analytics_results")
        supabase.table(table).insert({
            "user_id": user_id,
            "file_name": filename,
            "score": result.get("score"),
            "breakdown": result.get("breakdown"),
            "notes": "\n".join(result.get("recommendations", []))
        }).execute()
    except Exception:
        pass


def _get_user_id_from_auth(req):
    """Парсим 'Authorization: Bearer <jwt>' и спрашиваем user у Supabase (если доступно)."""
    if not supabase:
        return None
    try:
        auth = req.headers.get("Authorization", "")
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            jwt = parts[1]
            user = supabase.auth.get_user(jwt)
            return getattr(user, "user", {}).get("id") if hasattr(user, "user") else user.id
    except Exception:
        return None
    return None


# -------- Partners (GET) --------
@app.get("/partners")
def partners():
    if supabase:
        try:
            table = os.getenv("SUPABASE_PARTNERS_TABLE", "partners")
            data = supabase.table(table).select("*").order("created_at", desc=True).execute().data
            return ok(data or [])
        except Exception as e:
            return ok({"error": str(e)}, 500)
    # fallback mock
    return ok([
        {"id": "mock-1", "name": "Partner One", "logo_url": None,
         "website": "https://example.com", "description": "Demo partner"},
    ])


# -------- Leaderboard (GET) --------
@app.get("/leaderboard")
def leaderboard():
    year  = request.args.get("year", type=int)
    event = request.args.get("event", type=str)

    if supabase:
        try:
            table = os.getenv("SUPABASE_TEAMS_TABLE", "teams")
            q = supabase.table(table).select("*").order("score", desc=True).limit(20)
            if year:
                q = q.eq("event_year", year)
            if event:
                q = q.ilike("event_name", f"%{event}%")
            data = q.execute().data
            return ok(data or [])
        except Exception as e:
            return ok({"error": str(e)}, 500)

    # fallback mock
    demo = [
        {"id": "t1", "name": "Roomance", "tag": "PropTech", "logo_url": None, "score": 82,
         "event_year": 2025, "event_name": "Almaty"},
        {"id": "t2", "name": "NomadAI",  "tag": "Logistics", "logo_url": None, "score": 79,
         "event_year": 2025, "event_name": "Astana"},
    ]
    if year:
        demo = [d for d in demo if d["event_year"] == year]
    if event:
        e = event.lower()
        demo = [d for d in demo if e in d["event_name"].lower()]
    return ok(demo)


# -------- Auth (signup / login / me) --------
@app.post("/auth/signup")
def auth_signup():
    if not supabase:
        return ok(ApiError(error="Supabase not configured").model_dump(), 500)
    try:
        payload = AuthSignup(**request.get_json(force=True))
        res = supabase.auth.sign_up({"email": payload.email, "password": payload.password})
        return ok({"user": getattr(res, "user", None) or getattr(res, "user", None)})
    except Exception as e:
        return ok(ApiError(error=f"signup failed: {e}").model_dump(), 400)

@app.post("/auth/login")
def auth_login():
    if not supabase:
        return ok(ApiError(error="Supabase not configured").model_dump(), 500)
    try:
        payload = AuthLogin(**request.get_json(force=True))
        res = supabase.auth.sign_in_with_password({"email": payload.email, "password": payload.password})
        # Возвращаем access_token для последующих запросов с Authorization: Bearer
        session = getattr(res, "session", None)
        if session:
            return ok({"access_token": session.access_token, "user": res.user})
        # возможные отличия структур между версиями клиента
        data = res.__dict__
        return ok({"data": data})
    except Exception as e:
        return ok(ApiError(error=f"login failed: {e}").model_dump(), 400)

@app.get("/auth/me")
def auth_me():
    if not supabase:
        return ok(ApiError(error="Supabase not configured").model_dump(), 500)
    try:
        auth = request.headers.get("Authorization", "")
        parts = auth.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return ok(ApiError(error="Missing Bearer token").model_dump(), 401)
        jwt = parts[1]
        user = supabase.auth.get_user(jwt)
        # У разных версий клиента форма ответа отличается — нормализуем
        if hasattr(user, "user") and user.user:
            return ok({"user": user.user})
        return ok({"user": user})
    except Exception as e:
        return ok(ApiError(error=f"me failed: {e}").model_dump(), 400)


# -------- Debug (опционально) --------
@app.get("/debug-supabase")
def debug_supabase():
    if not supabase:
        return ok({"error": "Supabase client not initialized. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env."})
    try:
        resp = supabase.table(os.getenv("SUPABASE_PARTNERS_TABLE", "partners")).select("*").limit(2).execute()
        return ok({"data": resp.data})
    except Exception as e:
        return ok({"error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
