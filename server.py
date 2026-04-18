"""
DataProtect Senegal - Serveur Backend
FastAPI + SQLite + Chatbot IA (Groq gratuit)
Henry Pierre Diouf, DPO M2
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3, hashlib, secrets, pathlib, urllib.request, urllib.error, urllib.parse, json, re as re2
from collections import defaultdict
from datetime import datetime, timedelta

# ============================================================
# CONFIGURATION
# ============================================================
import os as _os
COHERE_API_KEY = _os.environ.get("COHERE_API_KEY", "METS_CLE_COHERE_ICI")
ADMIN_PASSWORD_CLAIR = "dataprotect2025"

# ============================================================

BASE_DIR = pathlib.Path(__file__).parent.resolve()
# Sur Render : utilise /data pour persistance, sinon dossier local
import os as _os2
_data_dir = "/data" if _os2.path.exists("/data") else str(BASE_DIR)
DB_PATH = _os2.path.join(_data_dir, "database.db")
ADMIN_PASSWORD = hashlib.sha256(ADMIN_PASSWORD_CLAIR.encode()).hexdigest()
tokens = set()

# Rate limiting : max 30 requetes par minute par IP
_rate_limit = defaultdict(list)

def check_rate_limit(ip: str, max_req: int = 30, window: int = 60) -> bool:
    now = datetime.now()
    cutoff = now - timedelta(seconds=window)
    _rate_limit[ip] = [t for t in _rate_limit[ip] if t > cutoff]
    if len(_rate_limit[ip]) >= max_req:
        return False
    _rate_limit[ip].append(now)
    return True

app = FastAPI(title="DataProtect SN API")

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
ALLOWED_ORIGINS = [
    "https://dataprotect-sn.onrender.com",
    "http://localhost:8080",
    "http://localhost:10000",
]
app.add_middleware(CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "HEAD"],
    allow_headers=["Content-Type", "X-Admin-Token"])

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def rows_to_list(rows):
    return [dict(r) for r in rows]

def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL, email TEXT NOT NULL,
        organisation TEXT, type_besoin TEXT, message TEXT NOT NULL,
        date_envoi TEXT DEFAULT (datetime('now')), lu INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS abonnes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prenom TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        date_inscription TEXT DEFAULT (datetime('now')), actif INTEGER DEFAULT 1)""")
    c.execute("""CREATE TABLE IF NOT EXISTS articles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titre TEXT NOT NULL, extrait TEXT, contenu TEXT,
        categorie TEXT, badge TEXT,
        date_publication TEXT DEFAULT (datetime('now')),
        publie INTEGER DEFAULT 1, source TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        created_at TEXT DEFAULT (datetime('now')),
        expires_at TEXT
    )""")
    # Nettoyer les sessions expirees
    conn.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")
    c.execute("""CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prenom TEXT NOT NULL, nom TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL, mot_de_passe TEXT NOT NULL,
        role TEXT DEFAULT 'membre',
        date_inscription TEXT DEFAULT (datetime('now')), actif INTEGER DEFAULT 1)""")
    if conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO articles (titre,extrait,contenu,categorie,badge,date_publication,publie,source) VALUES (?,?,?,?,?,?,?,?)",
            [("T2 2025 : CDP traite 96 dossiers, Wave Digital Finance sanctionnee",
              "La CDP a traite 96 dossiers. Rejet partiel pour Wave Digital Finance.",
              "Contenu...", "CDP", "b-cdp", "2025-07-01", 1, "Seneweb"),
             ("RGPD 2025 : 1,15 milliard euros amendes - TikTok, Google, Shein",
              "Record : TikTok 530M, Google 325M, Shein 150M.",
              "Contenu...", "RGPD", "b-rgpd", "2026-01-15", 1, "RGPD Kit"),
             ("IA Act : la CNIL regule les systemes IA depuis aout 2025",
              "La CNIL est autorite de regulation de l'IA depuis aout 2025.",
              "Contenu...", "Tech", "b-tech", "2025-10-01", 1, "CNIL")])
    conn.commit()
    conn.close()
    print("Base de donnees OK : " + DB_PATH)

class ContactForm(BaseModel):
    nom: str; email: str
    organisation: Optional[str] = ""
    type_besoin: Optional[str] = ""
    message: str

class NewsletterForm(BaseModel):
    prenom: str; email: str

class ChatRequest(BaseModel):
    messages: list

class ArticleCreate(BaseModel):
    titre: str; extrait: Optional[str] = ""; contenu: Optional[str] = ""
    categorie: Optional[str] = "Actualite"; badge: Optional[str] = "b-cdp"
    source: Optional[str] = ""; publie: Optional[int] = 1

class UserRegister(BaseModel):
    prenom: str; nom: str; email: str; mot_de_passe: str

class UserLogin(BaseModel):
    email: str; mot_de_passe: str

class AdminLogin(BaseModel):
    mot_de_passe: str

@app.head("/")
async def home_head():
    from fastapi.responses import Response
    return Response(status_code=200)

# Lire index.html depuis le disque (ou embarqué en fallback)
def _get_index_html():
    f = BASE_DIR / "index.html"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return "<h1>index.html introuvable</h1>"

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(_get_index_html())

@app.get("/admin.html", response_class=HTMLResponse)
async def admin_page():
    f = BASE_DIR / "admin.html"
    if not f.exists():
        return HTMLResponse("Erreur : admin.html introuvable", status_code=404)
    return HTMLResponse(f.read_text(encoding="utf-8"))

@app.get("/docs/{filename}")
async def serve_doc(filename: str):
    from fastapi.responses import FileResponse
    import re
    # Securite : nom de fichier alphanumérique seulement
    if not re.match(r'^[\w\-]+\.html$', filename):
        raise HTTPException(status_code=404, detail="Document introuvable")
    f = BASE_DIR / "docs" / filename
    if not f.exists():
        raise HTTPException(status_code=404, detail="Document introuvable")
    return FileResponse(str(f), media_type="text/html")


# ── DOCUMENTS RESSOURCES ──
DOCS_FILES = {
    "guide-citoyen-droits": "docs/guide-citoyen-droits.html",
    "registre-traitements": "docs/registre-traitements.html",
    "checklist-loi-2008-12": "docs/checklist-loi-2008-12.html",
    "checklist-rgpd-entreprises-sn": "docs/checklist-rgpd-entreprises-sn.html",
    "modele-politique-confidentialite": "docs/modele-politique-confidentialite.html",
}

@app.get("/docs/{filename}")
async def serve_doc(filename: str):
    name = filename.replace(".html", "")
    if name not in DOCS_FILES:
        raise HTTPException(status_code=404, detail="Document introuvable")
    f = BASE_DIR / DOCS_FILES[name]
    if not f.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=f.read_text(encoding="utf-8"))

@app.get("/app.js")
async def serve_js():
    f = BASE_DIR / "app.js"
    if not f.exists():
        raise HTTPException(status_code=404, detail="app.js introuvable")
    from fastapi.responses import FileResponse
    return FileResponse(str(f), media_type="application/javascript")

@app.get("/favicon.ico")
async def favicon():
    return JSONResponse({})

@app.get("/api/articles")
async def get_articles():
    try:
        conn = db()
        rows = conn.execute("SELECT * FROM articles WHERE publie=1 ORDER BY date_publication DESC").fetchall()
        conn.close()
        return rows_to_list(rows)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/contact")
async def submit_contact(form: ContactForm, request: Request):
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip, max_req=5, window=60):
        raise HTTPException(status_code=429, detail="Trop de requetes. Reessayez dans 1 minute.")
    try:
        conn = db()
        conn.execute("INSERT INTO contacts (nom,email,organisation,type_besoin,message) VALUES (?,?,?,?,?)",
            (form.nom, form.email, form.organisation, form.type_besoin, form.message))
        conn.commit(); conn.close()
        return {"success": True, "message": "Message enregistre."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/newsletter")
async def subscribe(form: NewsletterForm):
    try:
        conn = db()
        conn.execute("INSERT INTO abonnes (prenom,email) VALUES (?,?)", (form.prenom, form.email))
        conn.commit(); conn.close()
        return {"success": True, "message": "Inscription confirmee !"}
    except sqlite3.IntegrityError:
        return {"success": False, "message": "Email deja inscrit."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inscription")
async def register(user: UserRegister):
    try:
        mdp = hashlib.sha256(user.mot_de_passe.encode()).hexdigest()
        conn = db()
        conn.execute("INSERT INTO utilisateurs (prenom,nom,email,mot_de_passe) VALUES (?,?,?,?)",
            (user.prenom, user.nom, user.email, mdp))
        conn.commit(); conn.close()
        return {"success": True}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Email deja utilise.")

@app.post("/api/connexion")
async def login(creds: UserLogin):
    mdp = hashlib.sha256(creds.mot_de_passe.encode()).hexdigest()
    conn = db()
    row = conn.execute("SELECT * FROM utilisateurs WHERE email=? AND mot_de_passe=? AND actif=1",
        (creds.email, mdp)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")
    token = secrets.token_hex(32)
    tokens.add(token)
    return {"success": True, "token": token,
            "user": {"prenom": row["prenom"], "nom": row["nom"], "email": row["email"]}}

@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip, max_req=10, window=60):
        raise HTTPException(status_code=429, detail="Trop de requetes. Attendez 1 minute.")
    if not COHERE_API_KEY or COHERE_API_KEY == "METS_CLE_COHERE_ICI":
        return {"reply": "Chatbot non configure."}
    SYSTEM = "Tu es l assistant IA expert de DataProtect Senegal, fonde par Henry Pierre Diouf, DPO M2 de La Plateforme Numerique Marseille. Reponds TOUJOURS en francais (4-6 phrases). Cite les articles de loi : Loi senegalaise 2008-12, RGPD. Contact : henrypierrediouf@gmail.com"
    try:
        messages = []
        for m in req.messages[:-1]:
            messages.append({"role": "USER" if m["role"] == "user" else "CHATBOT", "message": m["content"]})
        question = req.messages[-1]["content"] if req.messages else ""
        payload = json.dumps({"model": "command-r-plus-08-2024", "preamble": SYSTEM, "chat_history": messages, "message": question, "max_tokens": 600, "temperature": 0.3}).encode("utf-8")
        req_obj = urllib.request.Request("https://api.cohere.com/v1/chat", data=payload, headers={"Content-Type": "application/json", "Authorization": "Bearer " + COHERE_API_KEY, "X-Client-Name": "DataProtectSN"}, method="POST")
        with urllib.request.urlopen(req_obj, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            return {"reply": data["text"]}
    except urllib.error.HTTPError as e:
        err = e.read().decode()
        raise HTTPException(status_code=502, detail="Erreur Cohere: " + err[:300])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def check_admin(request: Request):
    token = request.headers.get("X-Admin-Token", "")
    if not token:
        raise HTTPException(status_code=403, detail="Acces refuse")
    # Verifier en memoire d'abord (rapide)
    if token in tokens:
        return
    # Puis en base (persistant apres redemarrage)
    conn = db()
    row = conn.execute(
        "SELECT token FROM sessions WHERE token=? AND expires_at > datetime('now')",
        (token,)
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=403, detail="Session expiree. Reconnectez-vous.")

@app.post("/api/admin/login")
async def admin_login(creds: AdminLogin, request: Request):
    ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(ip, max_req=5, window=60):
        raise HTTPException(status_code=429, detail="Trop de tentatives. Attendez 1 minute.")
    if hashlib.sha256(creds.mot_de_passe.encode()).hexdigest() != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Mot de passe incorrect")
    token = secrets.token_hex(32)
    tokens.add(token)
    # Sauvegarder en base pour persistance (expire dans 24h)
    try:
        conn = db()
        conn.execute(
            "INSERT OR REPLACE INTO sessions (token, expires_at) VALUES (?, datetime('now', '+24 hours'))",
            (token,)
        )
        conn.commit()
        conn.close()
    except:
        pass
    return {"success": True, "token": token}

@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    check_admin(request)
    conn = db()
    stats = {
        "contacts": conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0],
        "non_lus":  conn.execute("SELECT COUNT(*) FROM contacts WHERE lu=0").fetchone()[0],
        "abonnes":  conn.execute("SELECT COUNT(*) FROM abonnes WHERE actif=1").fetchone()[0],
        "articles": conn.execute("SELECT COUNT(*) FROM articles WHERE publie=1").fetchone()[0],
        "membres":  conn.execute("SELECT COUNT(*) FROM utilisateurs WHERE actif=1").fetchone()[0],
    }
    conn.close()
    return stats

@app.get("/api/admin/contacts")
async def admin_contacts(request: Request):
    check_admin(request)
    conn = db()
    rows = conn.execute("SELECT * FROM contacts ORDER BY date_envoi DESC").fetchall()
    conn.close()
    return rows_to_list(rows)

@app.patch("/api/admin/contacts/{cid}/lu")
async def mark_read(cid: int, request: Request):
    check_admin(request)
    conn = db()
    conn.execute("UPDATE contacts SET lu=1 WHERE id=?", (cid,))
    conn.commit(); conn.close()
    return {"success": True}

@app.get("/api/admin/abonnes")
async def admin_abonnes(request: Request):
    check_admin(request)
    conn = db()
    rows = conn.execute("SELECT * FROM abonnes ORDER BY date_inscription DESC").fetchall()
    conn.close()
    return rows_to_list(rows)

@app.post("/api/admin/articles")
async def admin_create_article(article: ArticleCreate, request: Request):
    check_admin(request)
    conn = db()
    conn.execute(
        "INSERT INTO articles (titre,extrait,contenu,categorie,badge,source,publie) VALUES (?,?,?,?,?,?,?)",
        (article.titre, article.extrait, article.contenu, article.categorie,
         article.badge, article.source, article.publie))
    conn.commit(); conn.close()
    return {"success": True}

@app.delete("/api/admin/contacts/{cid}")
async def admin_delete_contact(cid: int, request: Request):
    check_admin(request)
    conn = db()
    conn.execute("DELETE FROM contacts WHERE id=?", (cid,))
    conn.commit(); conn.close()
    return {"success": True}

@app.delete("/api/admin/abonnes/{aid}")
async def admin_delete_abonne(aid: int, request: Request):
    check_admin(request)
    conn = db()
    conn.execute("DELETE FROM abonnes WHERE id=?", (aid,))
    conn.commit(); conn.close()
    return {"success": True}

@app.delete("/api/admin/utilisateurs/{uid}")
async def admin_delete_user(uid: int, request: Request):
    check_admin(request)
    conn = db()
    conn.execute("DELETE FROM utilisateurs WHERE id=?", (uid,))
    conn.commit(); conn.close()
    return {"success": True}

@app.patch("/api/admin/abonnes/{aid}/desactiver")
async def admin_deactivate_abonne(aid: int, request: Request):
    check_admin(request)
    conn = db()
    conn.execute("UPDATE abonnes SET actif=0 WHERE id=?", (aid,))
    conn.commit(); conn.close()
    return {"success": True}

@app.delete("/api/admin/articles/{aid}")
async def admin_delete_article(aid: int, request: Request):
    check_admin(request)
    conn = db()
    conn.execute("DELETE FROM articles WHERE id=?", (aid,))
    conn.commit(); conn.close()
    return {"success": True}

@app.get("/api/admin/utilisateurs")
async def admin_users(request: Request):
    check_admin(request)
    conn = db()
    rows = conn.execute(
        "SELECT id,prenom,nom,email,role,date_inscription,actif FROM utilisateurs ORDER BY date_inscription DESC"
    ).fetchall()
    conn.close()
    return rows_to_list(rows)

if __name__ == "__main__":
    import uvicorn
    init_db()
    print("\n" + "="*50)
    print("  DataProtect Senegal - Serveur local")
    print("="*50)
    print("  Site    : http://localhost:8080")
    print("  Admin   : http://localhost:8080/admin.html")
    print("  Docs    : http://localhost:8080/docs")
    print("  Chatbot : ACTIF (Cohere)" if COHERE_API_KEY != "METS_CLE_COHERE_ICI" else "  Chatbot : non configure")
    print("="*50 + "\n")
    import os
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
