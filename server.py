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

# HTML principal embarque dans le code
_INDEX_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DataProtect Sénégal — Protection des Données Personnelles</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;0,9..144,700;1,9..144,400&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --green:#1a6b3a;--green-dark:#0d3d20;--green-light:#e8f5ee;--green-mid:#2d8a52;
  --gold:#c8960e;--gold-light:#fef9e5;--gold-bright:#f5d060;
  --red:#b91c1c;--red-light:#fde8e8;
  --blue:#185ea5;--blue-light:#e8f0fe;
  --text:#111;--text-secondary:#2c3e50;
  --muted:#555;--muted2:#888;
  --bg:#f6f3ee;--bg2:#f0ede8;--white:#fff;
  --border:#e0dbd0;--border2:#ccc;
  --shadow-sm:0 1px 3px rgba(0,0,0,.06);
  --shadow:0 4px 16px rgba(0,0,0,.08);
  --shadow-lg:0 12px 40px rgba(0,0,0,.12);
  --radius:14px;--radius-sm:8px
}
html{scroll-behavior:smooth}
body{font-family:'DM Sans',sans-serif;background:var(--bg);color:var(--text);font-size:16px;line-height:1.7;overflow-x:hidden}

/* ===== NAV ===== */
nav{position:sticky;top:0;z-index:200;background:var(--white);border-bottom:1px solid var(--border);padding:0 1.5rem;display:flex;align-items:center;justify-content:space-between;height:60px}
.nav-logo{font-family:'Fraunces',serif;font-size:1.15rem;font-weight:700;color:var(--green);text-decoration:none;display:flex;align-items:center;gap:8px;white-space:nowrap;cursor:pointer}
.logo-accent{color:var(--gold)}
.nav-links{display:flex;align-items:center;gap:1.5rem;list-style:none}
.nav-links a{text-decoration:none;color:var(--muted);font-size:.85rem;font-weight:500;transition:color .2s;white-space:nowrap}
.nav-links a:hover,.nav-links a.active{color:var(--green)}
.nav-cta{background:var(--green)!important;color:var(--white)!important;padding:.35rem 1rem;border-radius:100px;font-size:.82rem!important}
.nav-cta:hover{opacity:.85}
.hamburger{display:none;flex-direction:column;gap:5px;cursor:pointer;padding:4px}
.hamburger span{width:22px;height:2px;background:var(--text);border-radius:2px;transition:.3s}
.hamburger.open span:nth-child(1){transform:rotate(45deg) translate(5px,5px)}
.hamburger.open span:nth-child(2){opacity:0}
.hamburger.open span:nth-child(3){transform:rotate(-45deg) translate(5px,-5px)}
.mobile-menu{display:none;position:fixed;top:60px;left:0;right:0;background:var(--white);border-bottom:1px solid var(--border);padding:1.5rem;z-index:199;flex-direction:column;gap:1rem}
.mobile-menu.open{display:flex}
.mobile-menu a{text-decoration:none;color:var(--text);font-size:1rem;font-weight:500;padding:.5rem 0;border-bottom:1px solid var(--border)}
.mobile-menu a:last-child{border-bottom:none}

/* ===== PAGES ===== */
.page{display:none}
.page.active{display:block}

/* ===== HERO ===== */
.hero{background:var(--green);color:var(--white);padding:4rem 1.5rem 5rem;position:relative;overflow:hidden}
.hero-inner{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:1fr 1fr;gap:3rem;align-items:center}
.hero-tag{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.12);color:rgba(255,255,255,.85);font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;padding:.3rem .85rem;border-radius:100px;border:1px solid rgba(255,255,255,.2);margin-bottom:1.25rem;width:fit-content}
.hero h1{font-family:'Fraunces',serif;font-size:clamp(2.2rem,4.5vw,3.6rem);font-weight:700;line-height:1.08;margin-bottom:1.25rem;letter-spacing:-.025em}
.hero h1 em{font-style:italic;color:var(--gold-bright)}
.hero-sub{font-size:.98rem;line-height:1.7;color:var(--muted);max-width:420px;margin-bottom:2rem}
.hero-btns{display:flex;gap:.75rem;flex-wrap:wrap}
.btn-gold{background:var(--gold-bright);color:#111;padding:.65rem 1.5rem;border-radius:100px;text-decoration:none;font-weight:500;font-size:.88rem;transition:transform .2s,opacity .2s;cursor:pointer;border:none;font-family:'DM Sans',sans-serif}
.btn-gold:hover{transform:translateY(-1px);opacity:.9}
.btn-ghost-w{background:transparent;color:rgba(255,255,255,.85);border:1px solid rgba(255,255,255,.3);padding:.65rem 1.5rem;border-radius:100px;text-decoration:none;font-size:.88rem;transition:background .2s;cursor:pointer;font-family:'DM Sans',sans-serif}
.btn-ghost-w:hover{background:rgba(255,255,255,.1)}
.hero-cards{display:flex;flex-direction:column;gap:.85rem}
.hero-stat-card{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.15);border-radius:14px;padding:1rem 1.25rem;display:flex;align-items:flex-start;gap:1rem}
.hsc-num{font-family:'Fraunces',serif;font-size:1.5rem;font-weight:700;color:var(--gold-bright);min-width:80px;line-height:1}
.hsc-label{font-size:.82rem;color:rgba(255,255,255,.72);line-height:1.4;padding-top:2px}
.hero-bg{position:absolute;top:-100px;right:-100px;width:500px;height:500px;border-radius:50%;border:1px solid rgba(255,255,255,.05);pointer-events:none}

/* ===== CONTAINER / SECTION ===== */
.container{max-width:1100px;margin:0 auto;padding:0 1.5rem}
section{padding:4rem 1.5rem}
.section-label{font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;color:var(--green);font-weight:500;margin-bottom:.6rem}
.section-title{font-family:'Fraunces',serif;font-size:clamp(1.7rem,3vw,2.5rem);font-weight:700;line-height:1.15;letter-spacing:-.02em;margin-bottom:.9rem}
.section-intro{color:var(--muted);max-width:560px;font-size:.95rem;margin-bottom:2.5rem}

/* ===== STATS BAR ===== */
.stats-bar{background:var(--green-dark);color:var(--white);padding:1.5rem}
.stats-inner{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;text-align:center}
.stat-item-num{font-family:'Fraunces',serif;font-size:1.6rem;font-weight:700;color:var(--gold-bright);line-height:1}
.stat-item-label{font-size:.76rem;color:rgba(255,255,255,.6);margin-top:.3rem;line-height:1.3}

/* ===== PILLARS ===== */
.pillars-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1.25rem}
.pillar-card{background:var(--white);border:1px solid var(--border);border-radius:16px;padding:1.75rem;transition:transform .25s,box-shadow .25s;cursor:pointer}
.pillar-card:hover{transform:translateY(-4px);box-shadow:0 12px 40px rgba(0,0,0,.07)}
.pillar-icon{width:44px;height:44px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:20px;margin-bottom:1.1rem}
.pi-green{background:var(--green-light)}
.pi-gold{background:var(--gold-light)}
.pi-red{background:var(--red-light)}
.pi-blue{background:var(--blue-light)}
.pillar-card h3{font-family:'Fraunces',serif;font-size:1.1rem;font-weight:600;margin-bottom:.5rem;letter-spacing:-.01em}
.pillar-card p{font-size:.87rem;color:var(--muted);line-height:1.6}
.pillar-link{display:inline-block;margin-top:1rem;font-size:.8rem;color:var(--green);font-weight:500;text-decoration:none;cursor:pointer}
.pillar-link:hover{text-decoration:underline}

/* ===== BLOG ===== */
.blog-layout{display:grid;grid-template-columns:1fr 360px;gap:2.5rem;align-items:start}
.blog-list{display:flex;flex-direction:column;gap:1.25rem}
.article-card{background:var(--white);border:1px solid var(--border);border-radius:14px;padding:1.5rem;cursor:pointer;transition:border-color .2s,box-shadow .2s}
.article-card:hover{border-color:var(--green);box-shadow:0 4px 20px rgba(0,0,0,.06)}
.article-top{display:flex;align-items:center;gap:.6rem;margin-bottom:.75rem;flex-wrap:wrap}
.badge{font-size:.68rem;font-weight:500;padding:.22rem .6rem;border-radius:6px;text-transform:uppercase;letter-spacing:.05em;white-space:nowrap}
.b-cdp{background:var(--green-light);color:var(--green)}
.b-loi{background:#e6f1ff;color:#1247a5}
.b-rgpd{background:var(--gold-light);color:#7a5800}
.b-tech{background:#f0e8ff;color:#6b21a8}
.b-afrique{background:#e8fff0;color:#166534}
.b-new{background:var(--red-light);color:var(--red);font-size:.65rem}
.article-title{font-weight:500;font-size:.95rem;margin-bottom:.5rem;line-height:1.4}
.article-excerpt{font-size:.84rem;color:var(--muted);line-height:1.6;margin-bottom:.75rem}
.article-meta{display:flex;align-items:center;gap:.75rem;font-size:.77rem;color:var(--muted2)}
.article-meta span{display:flex;align-items:center;gap:3px}
.read-more{font-size:.8rem;color:var(--green);font-weight:500;cursor:pointer;text-decoration:none}
.read-more:hover{text-decoration:underline}

/* SIDEBAR */
.sidebar{display:flex;flex-direction:column;gap:1.25rem;position:sticky;top:80px}
.sidebar-box{background:var(--white);border:1px solid var(--border);border-radius:14px;padding:1.5rem}
.sidebar-box h4{font-family:'Fraunces',serif;font-size:1.05rem;font-weight:600;margin-bottom:1rem}
.newsletter-box{background:var(--green);color:var(--white);border-radius:14px;padding:1.5rem}
.newsletter-box h4{font-family:'Fraunces',serif;font-size:1.1rem;font-weight:600;color:var(--white);margin-bottom:.5rem}
.newsletter-box p{font-size:.82rem;color:rgba(255,255,255,.72);margin-bottom:1rem}
.nl-input{width:100%;padding:.6rem .9rem;border:none;border-radius:8px;font-size:.85rem;margin-bottom:.6rem;font-family:'DM Sans',sans-serif;outline:none}
.nl-input:last-of-type{margin-bottom:.75rem}
.nl-btn{width:100%;padding:.65rem;background:var(--gold-bright);color:#111;border:none;border-radius:8px;font-size:.88rem;font-weight:500;cursor:pointer;font-family:'DM Sans',sans-serif;transition:opacity .2s}
.nl-btn:hover{opacity:.88}
.nl-note{font-size:.7rem;color:rgba(255,255,255,.5);margin-top:.6rem}
.quick-links{display:flex;flex-direction:column;gap:.5rem}
.quick-link{display:flex;align-items:center;justify-content:space-between;text-decoration:none;color:var(--text);font-size:.85rem;padding:.5rem 0;border-bottom:1px solid var(--border)}
.quick-link:last-child{border-bottom:none}
.quick-link:hover{color:var(--green)}
.ql-arrow{color:var(--green);font-size:.9rem}
.tag-cloud{display:flex;flex-wrap:wrap;gap:.4rem}
.tag-pill{padding:.28rem .7rem;border-radius:20px;font-size:.75rem;background:var(--bg);border:1px solid var(--border);color:var(--muted);cursor:pointer;transition:.15s}
.tag-pill:hover{background:var(--green-light);border-color:var(--green);color:var(--green)}

/* ===== ARTICLE PAGE ===== */
.article-page{max-width:800px;margin:0 auto}
.article-back{display:inline-flex;align-items:center;gap:6px;color:var(--green);font-size:.85rem;cursor:pointer;margin-bottom:1.5rem;text-decoration:none;font-weight:500}
.article-back:hover{text-decoration:underline}
.article-header{margin-bottom:2rem}
.article-header .article-top{margin-bottom:1rem}
.article-header h1{font-family:'Fraunces',serif;font-size:clamp(1.6rem,3vw,2.2rem);font-weight:700;line-height:1.2;margin-bottom:.75rem;letter-spacing:-.02em}
.article-header .article-meta{font-size:.82rem;color:var(--muted2)}
.article-intro{font-size:1.05rem;color:var(--muted);line-height:1.75;margin-bottom:2rem;padding-bottom:2rem;border-bottom:1px solid var(--border)}
.article-body h2{font-family:'Fraunces',serif;font-size:1.35rem;font-weight:600;margin:2rem 0 .75rem;letter-spacing:-.01em}
.article-body h3{font-size:1.05rem;font-weight:500;margin:1.5rem 0 .5rem}
.article-body p{margin-bottom:1rem;color:#222;font-size:.95rem;line-height:1.75}
.article-body ul{margin:0 0 1rem 1.25rem}
.article-body li{margin-bottom:.4rem;font-size:.95rem;color:#222}
.callout{background:var(--green-light);border-left:3px solid var(--green);border-radius:0 10px 10px 0;padding:1rem 1.25rem;margin:1.5rem 0}
.callout p{margin:0;font-size:.9rem;color:var(--green-dark)}
.callout strong{color:var(--green)}
.article-table{width:100%;border-collapse:collapse;margin:1.5rem 0;font-size:.88rem}
.article-table th{background:var(--green);color:var(--white);padding:.7rem 1rem;text-align:left;font-weight:500}
.article-table td{padding:.65rem 1rem;border-bottom:1px solid var(--border)}
.article-table tr:nth-child(even) td{background:#fafaf8}
.source-box{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:1rem 1.25rem;margin-top:2rem;font-size:.8rem;color:var(--muted2)}
.source-box strong{color:var(--muted)}

/* ===== RESSOURCES ===== */
.ressources-filters{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:2rem}
.filter-btn{padding:.35rem .9rem;border-radius:20px;font-size:.8rem;border:1px solid var(--border);background:var(--white);cursor:pointer;transition:.15s;font-family:'DM Sans',sans-serif;color:var(--muted)}
.filter-btn:hover,.filter-btn.active{background:var(--green);color:var(--white);border-color:var(--green)}
.ressources-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1.25rem}
.res-card{background:var(--white);border:1px solid var(--border);border-radius:14px;padding:1.5rem;cursor:pointer;transition:transform .2s,box-shadow .2s;position:relative}
.res-card:hover{transform:translateY(-3px);box-shadow:0 8px 28px rgba(0,0,0,.07)}
.res-icon{font-size:1.75rem;margin-bottom:.9rem}
.res-card h4{font-weight:500;font-size:.95rem;margin-bottom:.4rem;line-height:1.35}
.res-card p{font-size:.82rem;color:var(--muted);line-height:1.5;margin-bottom:.9rem}
.res-meta{display:flex;align-items:center;justify-content:space-between}
.res-type{font-size:.72rem;background:var(--bg);border:1px solid var(--border);padding:.2rem .55rem;border-radius:6px;color:var(--muted2)}
.res-dl{font-size:.8rem;color:var(--green);font-weight:500}
.res-badge-new{position:absolute;top:12px;right:12px;background:var(--red);color:var(--white);font-size:.65rem;padding:.2rem .5rem;border-radius:6px;font-weight:500}

/* ===== GUIDE PAGE ===== */
.guide-steps{display:flex;flex-direction:column;gap:1rem;margin-bottom:2rem}
.guide-step{background:var(--white);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.step-header{display:flex;align-items:center;gap:1rem;padding:1.25rem 1.5rem;cursor:pointer}
.step-num{width:34px;height:34px;border-radius:50%;background:var(--green);color:var(--white);font-family:'Fraunces',serif;font-size:1rem;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.step-title{font-weight:500;font-size:.95rem;flex:1}
.step-chevron{color:var(--muted2);font-size:.9rem;transition:transform .2s}
.guide-step.open .step-chevron{transform:rotate(180deg)}
.step-body{display:none;padding:0 1.5rem 1.25rem 4rem;font-size:.88rem;color:var(--muted);line-height:1.65}
.guide-step.open .step-body{display:block}

/* ===== QUIZ ===== */
.quiz-container{max-width:680px;margin:0 auto}
.quiz-progress{height:4px;background:var(--border);border-radius:2px;margin-bottom:2rem;overflow:hidden}
.quiz-bar{height:100%;background:var(--green);border-radius:2px;transition:width .4s}
.quiz-card{background:var(--white);border:1px solid var(--border);border-radius:16px;padding:2rem}
.quiz-q{font-family:'Fraunces',serif;font-size:1.15rem;font-weight:600;margin-bottom:1.5rem;line-height:1.4}
.quiz-options{display:flex;flex-direction:column;gap:.75rem}
.quiz-option{padding:1rem 1.25rem;border:1.5px solid var(--border);border-radius:10px;cursor:pointer;font-size:.92rem;transition:.15s;text-align:left;background:var(--white);font-family:'DM Sans',sans-serif}
.quiz-option:hover{border-color:var(--green);background:var(--green-light)}
.quiz-option.correct{border-color:var(--green);background:var(--green-light);color:var(--green-dark)}
.quiz-option.wrong{border-color:var(--red);background:var(--red-light);color:var(--red)}
.quiz-explanation{margin-top:1.25rem;padding:1rem;background:var(--bg);border-radius:10px;font-size:.85rem;color:var(--muted);line-height:1.6}
.quiz-nav{display:flex;justify-content:flex-end;margin-top:1.5rem}
.quiz-result{text-align:center;padding:2rem}
.quiz-score{font-family:'Fraunces',serif;font-size:3rem;font-weight:700;color:var(--green);line-height:1;margin-bottom:.5rem}
.quiz-result-msg{font-size:1rem;color:var(--muted);margin-bottom:1.5rem}

/* ===== COMPARATIF ===== */
.compare-grid{display:grid;grid-template-columns:1fr 1fr;gap:1.5rem}
.compare-card{background:var(--white);border:1px solid var(--border);border-radius:14px;overflow:hidden}
.compare-header{padding:1.25rem 1.5rem;border-bottom:1px solid var(--border)}
.compare-header h3{font-family:'Fraunces',serif;font-size:1.15rem;font-weight:600}
.compare-header p{font-size:.8rem;color:var(--muted);margin-top:.2rem}
.compare-body{padding:1.25rem 1.5rem}
.compare-row{display:flex;gap:.75rem;margin-bottom:.75rem;font-size:.87rem;line-height:1.5}
.compare-row:last-child{margin-bottom:0}
.cr-label{color:var(--muted2);min-width:100px;flex-shrink:0}
.cr-val{color:var(--text);font-weight:500}
.compare-match{background:var(--green-light);border:1px solid #b2d9bf;border-radius:10px;padding:1rem 1.25rem;margin-top:1.5rem;font-size:.85rem;color:var(--green-dark);grid-column:1/-1}

/* ===== ABOUT ===== */
.about-layout{display:grid;grid-template-columns:1fr 1.4fr;gap:3rem;align-items:start}
.about-visual{background:var(--green-light);border-radius:18px;padding:2.5rem 2rem;text-align:center}
.avatar{width:72px;height:72px;border-radius:50%;background:var(--green);color:var(--white);display:flex;align-items:center;justify-content:center;font-family:'Fraunces',serif;font-size:1.5rem;font-weight:700;margin:0 auto 1.25rem}
.cred-card{background:var(--white);border:1px solid var(--border);border-radius:10px;padding:.85rem 1.1rem;font-size:.85rem;color:var(--text);margin-bottom:.7rem;text-align:left}
.cred-card strong{color:var(--green);display:block;font-size:.72rem;letter-spacing:.04em;margin-bottom:2px}
.tags-wrap{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:1.5rem}
.tag-g{padding:.28rem .75rem;border-radius:8px;font-size:.78rem;font-weight:500;background:var(--green-light);color:var(--green);border:1px solid #c3e0cc}

/* ===== CONTACT ===== */
.contact-layout{display:grid;grid-template-columns:1fr 1fr;gap:2.5rem;align-items:start}
.contact-form{background:var(--white);border:1px solid var(--border);border-radius:16px;padding:2rem}
.contact-form h3{font-family:'Fraunces',serif;font-size:1.25rem;font-weight:600;margin-bottom:1.5rem}
.form-group{margin-bottom:1rem}
.form-group label{display:block;font-size:.82rem;font-weight:500;margin-bottom:.35rem;color:var(--muted)}
.form-input{width:100%;padding:.65rem .9rem;border:1px solid var(--border2);border-radius:8px;font-size:.9rem;font-family:'DM Sans',sans-serif;outline:none;transition:border-color .2s}
.form-input:focus{border-color:var(--green)}
.form-select{width:100%;padding:.65rem .9rem;border:1px solid var(--border2);border-radius:8px;font-size:.9rem;font-family:'DM Sans',sans-serif;outline:none;background:var(--white);cursor:pointer}
textarea.form-input{min-height:110px;resize:vertical}
.form-submit{width:100%;padding:.75rem;background:var(--green);color:var(--white);border:none;border-radius:10px;font-size:.92rem;font-weight:500;cursor:pointer;font-family:'DM Sans',sans-serif;transition:opacity .2s;margin-top:.25rem}
.form-submit:hover{opacity:.88}
.contact-info{display:flex;flex-direction:column;gap:1.25rem}
.info-card{background:var(--white);border:1px solid var(--border);border-radius:14px;padding:1.5rem}
.info-card h4{font-weight:500;font-size:.95rem;margin-bottom:.35rem}
.info-card p{font-size:.85rem;color:var(--muted);line-height:1.6}
.info-icon{font-size:1.25rem;margin-bottom:.6rem}
.tarif-item{display:flex;justify-content:space-between;align-items:center;padding:.6rem 0;border-bottom:1px solid var(--border);font-size:.85rem}
.tarif-item:last-child{border-bottom:none}
.tarif-price{font-weight:500;color:var(--green)}

/* ===== FOOTER ===== */
footer{background:var(--green-dark);color:rgba(255,255,255,.55);padding:2.5rem 1.5rem}
.footer-inner{max-width:1100px;margin:0 auto;display:grid;grid-template-columns:2fr 1fr 1fr;gap:2.5rem}
.footer-brand{font-family:'Fraunces',serif;font-size:1.1rem;font-weight:700;color:rgba(255,255,255,.9);margin-bottom:.5rem}
.footer-tagline{font-size:.82rem;line-height:1.6;margin-bottom:1rem}
.footer-legal{font-size:.72rem;color:rgba(255,255,255,.35);border-top:1px solid rgba(255,255,255,.1);padding-top:1.5rem;margin-top:1.5rem;max-width:1100px;margin-left:auto;margin-right:auto}
.footer-col h5{font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.45);margin-bottom:.85rem}
.footer-col a{display:block;color:rgba(255,255,255,.6);font-size:.83rem;text-decoration:none;margin-bottom:.4rem;cursor:pointer}
.footer-col a:hover{color:rgba(255,255,255,.9)}

/* ===== MOBILE ===== */
@media(max-width:768px){
  .nav-links{display:none}
  .hamburger{display:flex}
  .hero-inner{grid-template-columns:1fr}
  .hero-cards{display:none}
  .stats-inner{grid-template-columns:repeat(2,1fr)}
  .blog-layout{grid-template-columns:1fr}
  .sidebar{position:static}
  .about-layout{grid-template-columns:1fr}
  .about-visual{display:none}
  .compare-grid{grid-template-columns:1fr}
  .contact-layout{grid-template-columns:1fr}
  .footer-inner{grid-template-columns:1fr}
  .hero{padding:3rem 1.25rem 3.5rem}
}
@media(max-width:480px){
  .stats-inner{grid-template-columns:1fr 1fr}
  .ressources-grid{grid-template-columns:1fr}
}
[data-nav],[data-article],[data-reg],[data-filter],[data-accordion],[data-faq],[data-letter]{cursor:pointer}
.nav-links a,.footer-col a{cursor:pointer}
.dark-toggle{background:none;border:1px solid var(--border);border-radius:20px;padding:.28rem .7rem;cursor:pointer;font-size:.8rem;color:var(--text);font-family:'DM Sans',sans-serif;transition:.2s}
.dark-toggle:hover{background:var(--bg)}
#cookie-banner{position:fixed;bottom:0;left:0;right:0;background:var(--white);border-top:2px solid var(--green);padding:1rem 1.5rem;z-index:9999;display:none;box-shadow:0 -4px 20px rgba(0,0,0,.1)}
#cookie-banner.show{display:block}
.ck-inner{max-width:1100px;margin:0 auto;display:flex;align-items:center;gap:1.25rem;flex-wrap:wrap}
.ck-text{flex:1;min-width:240px}
.ck-text h4{font-size:.92rem;font-weight:600;color:var(--green);margin-bottom:.2rem}
.ck-text p{font-size:.78rem;color:var(--muted);line-height:1.5}
.ck-btns{display:flex;gap:.45rem;flex-wrap:wrap;flex-shrink:0}
.btn-ck-ok{background:var(--green);color:#fff;border:none;padding:.48rem 1rem;border-radius:100px;font-size:.82rem;font-weight:500;cursor:pointer}
.btn-ck-no{background:var(--white);color:var(--muted);border:1px solid var(--border);padding:.48rem 1rem;border-radius:100px;font-size:.82rem;cursor:pointer}
.btn-ck-set{background:none;border:none;color:var(--green);font-size:.78rem;cursor:pointer;text-decoration:underline}
#cookie-modal{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:10000;align-items:center;justify-content:center}
#cookie-modal.show{display:flex}
.cm-box{background:var(--white);border-radius:16px;padding:1.75rem;max-width:480px;width:90%;max-height:85vh;overflow-y:auto}
.cm-box h3{font-size:1.05rem;font-weight:700;color:var(--green);margin-bottom:.6rem}
.cm-cat{border:1px solid var(--border);border-radius:10px;padding:.8rem 1rem;margin-bottom:.5rem}
.cm-cat-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:.25rem}
.cm-cat-title{font-size:.86rem;font-weight:500}
.cm-cat-desc{font-size:.75rem;color:var(--muted);line-height:1.5}
.tgl{position:relative;width:40px;height:21px;flex-shrink:0}
.tgl input{opacity:0;width:0;height:0;position:absolute}
.tgl-s{position:absolute;inset:0;background:#ccc;border-radius:21px;cursor:pointer;transition:.25s}
.tgl-s:before{position:absolute;content:'';height:15px;width:15px;left:3px;bottom:3px;background:#fff;border-radius:50%;transition:.25s}
.tgl input:checked+.tgl-s{background:var(--green)}
.tgl input:checked+.tgl-s:before{transform:translateX(19px)}
.tgl input:disabled+.tgl-s{opacity:.6;cursor:not-allowed}
.cm-btns{display:flex;gap:.5rem;margin-top:.9rem;flex-wrap:wrap}
@media(max-width:600px){.ck-inner{flex-direction:column}}
#chatbot-bubble{position:fixed;bottom:1.5rem;right:1.5rem;z-index:500;display:flex;flex-direction:column;align-items:flex-end;gap:.75rem}
#chatbot-btn{width:58px;height:58px;border-radius:50%;background:var(--green);border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:0 4px 20px rgba(26,107,58,.4);padding:0}
#chatbot-window{width:340px;height:480px;background:var(--white);border:1px solid var(--border);border-radius:18px;display:none;flex-direction:column;overflow:hidden;box-shadow:0 12px 50px rgba(0,0,0,.15)}
#chatbot-window.open{display:flex}
.chat-header{background:var(--green);color:#fff;padding:.9rem 1.1rem;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.chat-name{font-weight:500;font-size:.9rem}
.chat-status{font-size:.7rem;color:rgba(255,255,255,.7)}
.chat-close{background:none;border:none;color:rgba(255,255,255,.8);cursor:pointer;font-size:1.1rem}
.chat-messages{flex:1;overflow-y:auto;padding:.9rem;display:flex;flex-direction:column;gap:.6rem}
.chat-msg{max-width:85%;padding:.6rem .85rem;border-radius:12px;font-size:.85rem;line-height:1.5}
.chat-msg.bot{background:var(--bg);color:var(--text);align-self:flex-start}
.chat-msg.user{background:var(--green);color:#fff;align-self:flex-end}
.chat-msg.typing{background:var(--bg);padding:.7rem .9rem;align-self:flex-start}
.typing-dots{display:flex;gap:4px}
.typing-dots span{width:6px;height:6px;border-radius:50%;background:var(--muted2);animation:dot 1.2s ease infinite}
.typing-dots span:nth-child(2){animation-delay:.2s}
.typing-dots span:nth-child(3){animation-delay:.4s}
@keyframes dot{0%,80%,100%{transform:scale(.8);opacity:.5}40%{transform:scale(1);opacity:1}}
.chat-sugs{display:flex;flex-wrap:wrap;gap:.35rem;padding:.4rem .9rem 0}
.chat-sug{background:var(--green-light);color:var(--green);border:1px solid #b2d9bf;border-radius:20px;padding:.25rem .65rem;font-size:.75rem;cursor:pointer}
.chat-input-wrap{display:flex;gap:.45rem;padding:.65rem .9rem;border-top:1px solid var(--border);flex-shrink:0}
.chat-input{flex:1;border:1px solid var(--border);border-radius:20px;padding:.45rem .85rem;font-size:.85rem;outline:none;background:var(--bg);color:var(--text)}
.chat-input:focus{border-color:var(--green)}
.chat-send{background:var(--green);color:#fff;border:none;border-radius:50%;width:32px;height:32px;cursor:pointer;font-size:.9rem;flex-shrink:0}
@media(max-width:768px){#chatbot-window{width:calc(100vw - 2rem)}}


/* === TLS CONTACT STYLE === */
*{font-family:-apple-system,"Segoe UI",Helvetica,Arial,sans-serif}
body{background:#fff;color:var(--text)}
.navbar{background:#fff;border-bottom:1px solid var(--border);padding:.9rem 0;box-shadow:none}
.navbar .logo{font-size:1.15rem;font-weight:700;color:var(--green-dark);letter-spacing:-.02em}
.navbar .logo span{color:var(--green)}
.nav-links a{color:var(--text-secondary);font-size:.88rem;font-weight:400;letter-spacing:.01em}
.nav-links a:hover,.nav-links a.active{color:var(--green-dark);font-weight:500}
.hero{background:#fff !important;padding:5rem 0 !important;border-bottom:1px solid var(--border)}
.btn-primary{background:var(--green);color:#fff;border-radius:2px;font-weight:500;font-size:.88rem;letter-spacing:.02em;padding:.7rem 1.5rem;box-shadow:none;transition:background .2s,transform .1s}
.btn-primary:hover{background:#c5520a;transform:none;box-shadow:none}
.section-title{font-size:clamp(1.4rem,3vw,2rem);font-weight:700;color:var(--green-dark);letter-spacing:-.03em}
.section-label{background:transparent;color:var(--green);font-size:.72rem;font-weight:600;letter-spacing:.1em;text-transform:uppercase;padding:0}
.blog-card{background:#fff;border:1px solid var(--border);border-radius:var(--radius-lg);box-shadow:none;transition:box-shadow .2s,transform .2s}
.blog-card:hover{box-shadow:0 8px 30px rgba(0,0,0,.1);transform:translateY(-2px);border-color:var(--border2)}
.res-card{background:#fff;border:1px solid var(--border);border-radius:var(--radius-lg);box-shadow:none;transition:box-shadow .2s}
.res-card:hover{box-shadow:0 6px 24px rgba(0,0,0,.1);border-color:var(--green)}
.stat-card{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-lg);box-shadow:none}
.stat-card:hover{transform:none;box-shadow:none;background:var(--bg3)}
.badge.b-cdp{background:#eef3ff;color:#1a2744;border:1px solid #c7d5f0}
.badge.b-rgpd{background:#fff3ec;color:#c5520a;border:1px solid #fad4b5}
.badge.b-tech{background:#f0f4ff;color:#1a2744;border:1px solid #c7d5f0}
.badge.b-loi{background:#fff3ec;color:#c5520a;border:1px solid #fad4b5}
.badge.b-afrique{background:#eef3ff;color:#1a2744;border:1px solid #c7d5f0}
.badge.b-new{background:var(--green);color:#fff;border:none}
.form-input{border:1px solid var(--border2);border-radius:var(--radius);background:#fff;font-size:.9rem;transition:border-color .2s}
.form-input:focus{border-color:var(--green-dark);box-shadow:none;outline:none}
footer{background:var(--green-dark)}
.footer-brand{color:#fff;font-size:1.05rem;font-weight:700}
.footer-col h5{color:var(--green);font-size:.72rem;letter-spacing:.1em;text-transform:uppercase}
.footer-col a{color:rgba(255,255,255,.55);font-size:.85rem}
.footer-col a:hover{color:#fff}
.footer-legal{color:rgba(255,255,255,.3);border-top:1px solid rgba(255,255,255,.1);font-size:.78rem}
#chatbot-btn{background:var(--green);box-shadow:0 4px 20px rgba(232,98,10,.35)}
.chat-header{background:var(--green-dark)}
.chat-msg.user{background:var(--green-dark)}
.chat-send{background:var(--green)}
.chat-input:focus{border-color:var(--green)}
.chat-sug{background:#fff3ec;color:var(--green);border-color:#fad4b5}
.btn-ck-ok{background:var(--green)}
.tgl input:checked+.tgl-s{background:var(--green)}
.quiz-option{border:1px solid var(--border);border-radius:var(--radius);background:#fff}
.quiz-option:hover{border-color:var(--green);background:#fff3ec}
.dark-toggle{border-color:var(--border2);font-size:.78rem}
[data-theme="dark"] body{background:var(--green-dark)}
[data-theme="dark"] .navbar{background:var(--green-dark);border-color:var(--border)}
[data-theme="dark"] .blog-card,[data-theme="dark"] .res-card{background:var(--bg2);border-color:var(--border)}
[data-theme="dark"] .btn-primary:hover{background:#c5520a}
</style>
</head>
<body>

<!-- NAV -->
<nav>
  <a class="nav-logo" data-nav="home">
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="10" fill="#1a6b3a"/><path d="M6 7h8M6 10h6M6 13h4" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>
    DataProtect<span class="logo-accent">SN</span>
  </a>
  <ul class="nav-links">
    <li><a data-nav="home" id="nav-home" class="active">Accueil</a></li>
    <li><a data-nav="blog" id="nav-blog">Veille juridique</a></li>
    <li><a data-nav="guide" id="nav-guide">Guide citoyen</a></li>
    <li><a data-nav="ressources" id="nav-ressources">Ressources</a></li>
    <li><a data-nav="comparatif" id="nav-comparatif">RGPD vs Loi SN</a></li>
    <li><a data-nav="about" id="nav-about">À propos</a></li>
    <li><a data-nav="contact" id="nav-contact" class="nav-cta">Contact</a></li>
  </ul>
  <div class="hamburger" id="hamburger" data-toggle-menu="1">
    <span></span><span></span><span></span>
  </div>
</nav>

<div class="mobile-menu" id="mobileMenu">
  <a data-nav="home">🏠 Accueil</a>
  <a data-nav="blog">📰 Veille juridique</a>
  <a data-nav="guide">📖 Guide citoyen</a>
  <a data-nav="ressources">📂 Ressources</a>
  <a data-nav="comparatif">⚖️ RGPD vs Loi SN</a>
  <a data-nav="about">👤 À propos</a>
  <a data-nav="contact">✉️ Contact</a>
</div>

<!-- =================== PAGE ACCUEIL =================== -->
<div class="page active" id="page-home">

  <div class="hero" style="background:linear-gradient(160deg,#0d3d20 0%,#1a6b3a 50%,#185ea5 100%);min-height:86vh;display:flex;align-items:center;position:relative;overflow:hidden">
  <div style="position:absolute;inset:0;opacity:.05;background-image:radial-gradient(circle at 20% 30%,#fff 1px,transparent 1px),radial-gradient(circle at 80% 70%,#fff 1px,transparent 1px);background-size:48px 48px;pointer-events:none"></div>
  <div style="position:absolute;top:-120px;right:-80px;width:500px;height:500px;background:radial-gradient(circle,rgba(232,196,68,.1) 0%,transparent 65%);pointer-events:none"></div>
  <div class="hero-inner container" style="position:relative;z-index:1;padding:5rem 1.5rem">
    <div style="max-width:680px">
      <div class="hero-tag" style="background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);color:rgba(255,255,255,.88)"><span style="width:7px;height:7px;border-radius:50%;background:#4ade80;display:inline-block"></span> Plateforme de reference &mdash; Senegal</div>
      <h1 style="font-size:clamp(2rem,5vw,3.2rem);font-weight:700;color:var(--green-dark);line-height:1.08;margin:.75rem 0 1.25rem;letter-spacing:-.04em">Vos donnees,<br><span style="background:linear-gradient(135deg,#f0b429,#ffd166);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text">vos droits.</span><br>Proteges.</h1>
      <p class="hero-sub" style="color:rgba(255,255,255,.78);font-size:1.1rem;line-height:1.75;max-width:540px">La premiere plateforme senegalaise de sensibilisation a la protection des donnees personnelles. Loi 2008-12, RGPD, IA Act &mdash; expliques simplement, pour tous.</p>
      <div class="hero-actions" style="margin-top:2rem">
        <button data-nav="guide" class="btn-primary" style="background:var(--green);color:#fff;font-size:.92rem;padding:.75rem 1.75rem;font-weight:500">Decouvrir mes droits</button>
        <button data-nav="contact" class="btn-primary" style="background:transparent;border:1px solid var(--green-dark);color:var(--green-dark);font-size:.88rem;padding:.72rem 1.65rem">Demander un audit &rarr;</button>
      </div>
      <div style="display:flex;gap:2.5rem;margin-top:3.5rem;flex-wrap:wrap;padding-top:2rem;border-top:1px solid rgba(255,255,255,.15)">
        <div style="color:var(--muted);font-size:.82rem"><span style="color:var(--green-dark);font-weight:700;font-size:1.4rem;display:block;line-height:1.1;letter-spacing:-.03em">2008</span>Loi fondatrice</div>
        <div style="color:var(--muted);font-size:.82rem"><span style="color:var(--green-dark);font-weight:700;font-size:1.4rem;display:block;line-height:1.1;letter-spacing:-.03em">39/55</span>Pays africains</div>
        <div style="color:var(--muted);font-size:.82rem"><span style="color:var(--green-dark);font-weight:700;font-size:1.4rem;display:block;line-height:1.1;letter-spacing:-.03em">RGPD</span>Compatible</div>
        <div style="color:var(--muted);font-size:.82rem"><span style="color:var(--green-dark);font-weight:700;font-size:1.4rem;display:block;line-height:1.1;letter-spacing:-.03em">IA Act</span>2025</div>
      </div>
    </div>
  </div>
</div>
  <section style="background:#fff;padding:3rem 0">
    <div class="container">
      <div class="section-label">Nos missions</div>
      <h2 class="section-title">Tout ce que couvre <br>notre plateforme</h2>
      <p class="section-intro">Un espace de référence sur la protection des données personnelles, adapté au contexte sénégalais et aux enjeux africains.</p>
      <div class="pillars-grid">
        <div class="pillar-card" data-nav="guide">
          <div class="pillar-icon pi-green">🛡️</div>
          <h3>Guide citoyen</h3>
          <p>Vos droits d'accès, de rectification, d'opposition et d'effacement expliqués simplement. Quiz interactif inclus.</p>
          <span class="pillar-link">Accéder au guide →</span>
        </div>
        <div class="pillar-card" data-nav="blog">
          <div class="pillar-icon pi-gold">⚖️</div>
          <h3>Veille juridique & tech</h3>
          <p>Décisions de la CDP, évolutions législatives africaines, RGPD et IA Act — sourcées et vérifiées régulièrement.</p>
          <span class="pillar-link">Lire la veille →</span>
        </div>
        <div class="pillar-card" data-nav="comparatif">
          <div class="pillar-icon pi-red">🇪🇺</div>
          <h3>RGPD vs Loi sénégalaise</h3>
          <p>Comparatif détaillé entre le règlement européen et la Loi 2008-12. Indispensable pour les entreprises qui exportent vers l'UE.</p>
          <span class="pillar-link">Voir le comparatif →</span>
        </div>
        <div class="pillar-card" data-nav="contact">
          <div class="pillar-icon pi-blue">📋</div>
          <h3>Accompagnement DPO</h3>
          <p>Mise en conformité, registre des traitements, AIPD, politique de confidentialité. Expert DPO certifié M2.</p>
          <span class="pillar-link">Me contacter →</span>
        </div>
      </div>
    </div>
  </section>

  <section>
    <div class="container">
      <div class="section-label">Actualités récentes</div>
      <h2 class="section-title">Dernières nouvelles vérifiées</h2>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1.25rem;margin-bottom:2rem">
        <div class="article-card" data-article="a1">
          <div class="article-top"><span class="badge b-cdp">CDP</span><span class="badge b-new">Nouveau</span></div>
          <div class="article-title">T2 2025 — Wave Digital Finance sanctionnée, Yassir Sénégal contrôlé sur site</div>
          <div class="article-meta"><span>Juillet 2025</span><span>5 min</span></div>
        </div>
        <div class="article-card" data-article="a2">
          <div class="article-top"><span class="badge b-rgpd">RGPD</span></div>
          <div class="article-title">Bilan RGPD 2025 : 1,15 milliard d'€ d'amendes — TikTok, Google, Shein dans le viseur</div>
          <div class="article-meta"><span>Jan. 2026</span><span>7 min</span></div>
        </div>
        <div class="article-card" data-article="a3">
          <div class="article-top"><span class="badge b-tech">IA Act</span></div>
          <div class="article-title">IA Act : la CNIL devient autorité de régulation de l'IA depuis août 2025. Impacts pour le Sénégal.</div>
          <div class="article-meta"><span>Oct. 2025</span><span>6 min</span></div>
        </div>
      </div>
      <button class="btn-gold" data-nav="blog">Voir toute la veille →</button>
    </div>
  </section>

</div>

<!-- =================== PAGE BLOG =================== -->

<div class="page" id="page-home">

<!-- HERO VERT FONCE -->
<div style="background:linear-gradient(135deg,#0a2e1a 0%,#1a6b3a 60%,#0d3d20 100%);padding:4rem 0 5rem;position:relative;overflow:hidden">
  <div style="position:absolute;inset:0;opacity:.04;background-image:radial-gradient(circle,#fff 1px,transparent 1px);background-size:32px 32px"></div>
  <div class="container" style="position:relative;z-index:1">
    <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:3rem;align-items:center">
      <div>
        <div style="display:inline-flex;align-items:center;gap:.5rem;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.2);border-radius:100px;padding:.35rem 1rem;font-size:.75rem;color:rgba(255,255,255,.9);font-weight:600;margin-bottom:1.5rem;letter-spacing:.05em">
          <span style="width:7px;height:7px;background:#4ade80;border-radius:50%;display:inline-block"></span>
          PLATEFORME DE REFERENCE &mdash; SENEGAL
        </div>
        <h1 style="font-size:clamp(2rem,4.5vw,3rem);font-weight:800;color:#fff;line-height:1.1;margin:0 0 1.25rem;letter-spacing:-.03em">
          Protection des donnees<br>personnelles au Senegal
        </h1>
        <p style="font-size:1rem;color:rgba(255,255,255,.78);line-height:1.8;margin:0 0 2rem;max-width:500px">
          Loi 2008-12, RGPD, IA Act &mdash; tout ce qu'il faut savoir sur vos droits et obligations. Gratuit, source, pour tous.
        </p>
        <div style="display:flex;gap:.85rem;flex-wrap:wrap;margin-bottom:2.5rem">
          <button data-nav="guide" style="background:#fff;color:var(--green);padding:.72rem 1.6rem;border-radius:100px;font-weight:700;font-size:.9rem;border:none;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25)">Decouvrir mes droits</button>
          <button data-nav="contact" style="background:transparent;border:2px solid rgba(255,255,255,.45);color:#fff;padding:.68rem 1.5rem;border-radius:100px;font-weight:600;font-size:.88rem;cursor:pointer">Demander un audit &rarr;</button>
        </div>
        <!-- Chiffres inline -->
        <div style="display:flex;gap:2rem;flex-wrap:wrap;padding-top:1.75rem;border-top:1px solid rgba(255,255,255,.15)">
          <div><div style="font-size:1.6rem;font-weight:800;color:#4ade80;line-height:1">112</div><div style="font-size:.74rem;color:rgba(255,255,255,.6);margin-top:.2rem">Dossiers CDP Q1 2026</div></div>
          <div><div style="font-size:1.6rem;font-weight:800;color:#f5d060;line-height:1">39/55</div><div style="font-size:.74rem;color:rgba(255,255,255,.6);margin-top:.2rem">Pays africains</div></div>
          <div><div style="font-size:1.6rem;font-weight:800;color:#60a5fa;line-height:1">1,2Md&euro;</div><div style="font-size:.74rem;color:rgba(255,255,255,.6);margin-top:.2rem">Amendes RGPD 2026</div></div>
          <div><div style="font-size:1.6rem;font-weight:800;color:#f5d060;line-height:1">50M</div><div style="font-size:.74rem;color:rgba(255,255,255,.6);margin-top:.2rem">FCFA sanction max</div></div>
        </div>
      </div>
      <!-- Carte droite -->
      <div style="display:flex;flex-direction:column;gap:.85rem">
        <div style="background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:16px;padding:1.25rem">
          <div style="font-size:.7rem;color:rgba(255,255,255,.55);font-weight:700;letter-spacing:.08em;margin-bottom:.6rem">LOI FONDATRICE</div>
          <div style="font-size:1.5rem;font-weight:800;color:#fff">Loi n&deg;2008-12</div>
          <div style="font-size:.82rem;color:rgba(255,255,255,.65);margin-top:.25rem">25 janvier 2008 &mdash; Protection des donnees personnelles au Senegal</div>
        </div>
        <div style="background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:16px;padding:1.25rem">
          <div style="font-size:.7rem;color:rgba(255,255,255,.55);font-weight:700;letter-spacing:.08em;margin-bottom:.6rem">REFORME EN COURS</div>
          <div style="font-size:1.1rem;font-weight:700;color:#fff">Projet de loi 2026</div>
          <div style="font-size:.82rem;color:rgba(255,255,255,.65);margin-top:.25rem">Portabilite + DPO obligatoire + sanctions 50M FCFA</div>
        </div>
        <div style="background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.18);border-radius:16px;padding:1.25rem">
          <div style="font-size:.7rem;color:rgba(255,255,255,.55);font-weight:700;letter-spacing:.08em;margin-bottom:.6rem">IA ACT EUROPEEN</div>
          <div style="font-size:1.1rem;font-weight:700;color:#fff">En vigueur depuis 2026</div>
          <div style="font-size:.82rem;color:rgba(255,255,255,.65);margin-top:.25rem">S'applique aux entreprises senegalaises exportant vers UE</div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- BANDE SERVICES VERTS -->
<div style="background:var(--green);padding:1.5rem 0">
  <div class="container">
    <div style="display:grid;grid-template-columns:repeat(5,1fr);gap:.5rem;text-align:center">
      <div data-nav="guide" style="cursor:pointer;padding:.5rem;border-right:1px solid rgba(255,255,255,.2)">
        <div style="font-size:1.2rem">&#128737;</div>
        <div style="font-size:.78rem;font-weight:600;color:#fff;margin-top:.3rem">Guide citoyen</div>
      </div>
      <div data-nav="blog" style="cursor:pointer;padding:.5rem;border-right:1px solid rgba(255,255,255,.2)">
        <div style="font-size:1.2rem">&#9878;</div>
        <div style="font-size:.78rem;font-weight:600;color:#fff;margin-top:.3rem">Veille juridique</div>
      </div>
      <div data-nav="ressources" style="cursor:pointer;padding:.5rem;border-right:1px solid rgba(255,255,255,.2)">
        <div style="font-size:1.2rem">&#128196;</div>
        <div style="font-size:.78rem;font-weight:600;color:#fff;margin-top:.3rem">Ressources</div>
      </div>
      <div data-nav="comparatif" style="cursor:pointer;padding:.5rem;border-right:1px solid rgba(255,255,255,.2)">
        <div style="font-size:1.2rem">&#127482;</div>
        <div style="font-size:.78rem;font-weight:600;color:#fff;margin-top:.3rem">RGPD vs Loi SN</div>
      </div>
      <div data-nav="contact" style="cursor:pointer;padding:.5rem">
        <div style="font-size:1.2rem">&#128203;</div>
        <div style="font-size:.78rem;font-weight:600;color:#fff;margin-top:.3rem">Audit DPO</div>
      </div>
    </div>
  </div>
</div>

<!-- CONTENU PRINCIPAL -->
<div style="background:var(--bg)">
<div class="container" style="padding:2.5rem 1.5rem">
<div class="blog-layout">

  <!-- COLONNE PRINCIPALE -->
  <div>

    <!-- ACTUALITES -->
    <div style="background:var(--white);border:1px solid var(--border);border-radius:16px;overflow:hidden;margin-bottom:1.5rem">
      <div style="background:var(--green-dark);padding:1rem 1.5rem;display:flex;align-items:center;justify-content:space-between">
        <div style="font-weight:700;color:#fff;font-size:.92rem">Actualites recentes</div>
        <button data-nav="blog" style="background:rgba(255,255,255,.15);border:none;color:#fff;padding:.3rem .85rem;border-radius:100px;font-size:.75rem;cursor:pointer">Voir tout &rarr;</button>
      </div>
      <div style="padding:1.25rem">
        <div data-article="a1" style="padding:.9rem 0;border-bottom:1px solid var(--border);cursor:pointer">
          <div style="display:flex;gap:.4rem;margin-bottom:.4rem"><span class="badge b-cdp">CDP</span><span class="badge b-new">Avr. 2026</span></div>
          <div style="font-size:.9rem;font-weight:600;color:var(--text);line-height:1.45;margin-bottom:.3rem">Bilan Q1 2026 : la CDP renforce les controles sur les fintechs</div>
          <div style="font-size:.78rem;color:var(--muted)">112 dossiers, 3 mises en demeure — Wave, Orange Money, Free Money dans le viseur</div>
          <span style="font-size:.78rem;color:var(--green);font-weight:600;margin-top:.4rem;display:inline-block">Lire l'article &rarr;</span>
        </div>
        <div data-article="a2" style="padding:.9rem 0;border-bottom:1px solid var(--border);cursor:pointer">
          <div style="display:flex;gap:.4rem;margin-bottom:.4rem"><span class="badge b-rgpd">RGPD</span><span class="badge b-new">Mars 2026</span></div>
          <div style="font-size:.9rem;font-weight:600;color:var(--text);line-height:1.45;margin-bottom:.3rem">Meta condamne a 1,2 milliard euros : nouveau record mondial</div>
          <div style="font-size:.78rem;color:var(--muted)">Impact direct pour les entreprises senegalaises exportant vers UE</div>
          <span style="font-size:.78rem;color:var(--green);font-weight:600;margin-top:.4rem;display:inline-block">Lire l'article &rarr;</span>
        </div>
        <div data-article="a3" style="padding:.9rem 0;border-bottom:1px solid var(--border);cursor:pointer">
          <div style="display:flex;gap:.4rem;margin-bottom:.4rem"><span class="badge b-tech">IA Act</span><span class="badge b-new">Fev. 2026</span></div>
          <div style="font-size:.9rem;font-weight:600;color:var(--text);line-height:1.45;margin-bottom:.3rem">IA Act : premieres interdictions en vigueur depuis fevrier 2026</div>
          <div style="font-size:.78rem;color:var(--muted)">Scoring social, manipulation comportementale bannis en Europe</div>
          <span style="font-size:.78rem;color:var(--green);font-weight:600;margin-top:.4rem;display:inline-block">Lire l'article &rarr;</span>
        </div>
        <div data-article="a4" style="padding:.9rem 0;cursor:pointer">
          <div style="display:flex;gap:.4rem;margin-bottom:.4rem"><span class="badge b-loi">Reforme</span><span class="badge b-new">Jan. 2026</span></div>
          <div style="font-size:.9rem;font-weight:600;color:var(--text);line-height:1.45;margin-bottom:.3rem">Reforme Loi 2008-12 deposee a l'Assemblee nationale</div>
          <div style="font-size:.78rem;color:var(--muted)">Portabilite, DPO obligatoire, sanctions 50M FCFA — vote prevu 2026</div>
          <span style="font-size:.78rem;color:var(--green);font-weight:600;margin-top:.4rem;display:inline-block">Lire l'article &rarr;</span>
        </div>
      </div>
    </div>

    <!-- NOS SERVICES -->
    <div style="background:var(--white);border:1px solid var(--border);border-radius:16px;overflow:hidden;margin-bottom:1.5rem">
      <div style="background:var(--green-dark);padding:1rem 1.5rem">
        <div style="font-weight:700;color:#fff;font-size:.92rem">Nos services</div>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0">
        <div data-nav="guide" style="padding:1.25rem;border-right:1px solid var(--border);border-bottom:1px solid var(--border);cursor:pointer">
          <div style="width:40px;height:40px;background:var(--green-light);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;margin-bottom:.75rem">&#128737;</div>
          <div style="font-size:.88rem;font-weight:700;color:var(--text);margin-bottom:.35rem">Guide citoyen</div>
          <div style="font-size:.78rem;color:var(--muted);line-height:1.5">Vos 10 droits sur vos donnees personnelles expliques simplement</div>
        </div>
        <div data-nav="blog" style="padding:1.25rem;border-bottom:1px solid var(--border);cursor:pointer">
          <div style="width:40px;height:40px;background:#fef9e5;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;margin-bottom:.75rem">&#9878;</div>
          <div style="font-size:.88rem;font-weight:700;color:var(--text);margin-bottom:.35rem">Veille juridique</div>
          <div style="font-size:.78rem;color:var(--muted);line-height:1.5">CDP, RGPD, IA Act — actualites sources et verifiees</div>
        </div>
        <div data-nav="ressources" style="padding:1.25rem;border-right:1px solid var(--border);cursor:pointer">
          <div style="width:40px;height:40px;background:#e8f0fe;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;margin-bottom:.75rem">&#128196;</div>
          <div style="font-size:.88rem;font-weight:700;color:var(--text);margin-bottom:.35rem">Ressources gratuites</div>
          <div style="font-size:.78rem;color:var(--muted);line-height:1.5">Registre, checklists, modeles de documents conformes</div>
        </div>
        <div data-nav="contact" style="padding:1.25rem;cursor:pointer">
          <div style="width:40px;height:40px;background:var(--green-light);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;margin-bottom:.75rem">&#128203;</div>
          <div style="font-size:.88rem;font-weight:700;color:var(--text);margin-bottom:.35rem">Accompagnement DPO</div>
          <div style="font-size:.78rem;color:var(--muted);line-height:1.5">Audit, mise en conformite, DPO externe certifie M2</div>
        </div>
      </div>
    </div>

    <!-- TEMOIGNAGES -->
    <div style="background:var(--white);border:1px solid var(--border);border-radius:16px;overflow:hidden">
      <div style="background:var(--green-dark);padding:1rem 1.5rem">
        <div style="font-weight:700;color:#fff;font-size:.92rem">Ils nous font confiance</div>
      </div>
      <div style="padding:1.25rem;display:grid;grid-template-columns:1fr 1fr;gap:1rem">
        <div style="background:var(--bg);border-radius:12px;padding:1rem">
          <div style="color:#f5d060;font-size:.85rem;margin-bottom:.5rem">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
          <p style="font-size:.8rem;color:var(--text);line-height:1.65;margin:0 0 .75rem;font-style:italic">"Le guide citoyen est tres clair. J'ai enfin compris mes droits face a mon operateur telecom."</p>
          <div style="display:flex;align-items:center;gap:.5rem">
            <div style="width:30px;height:30px;background:var(--green);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:700;color:#fff">AF</div>
            <div><div style="font-size:.78rem;font-weight:600;color:var(--text)">Aminata Faye</div><div style="font-size:.72rem;color:var(--muted)">Citoyenne, Dakar</div></div>
          </div>
        </div>
        <div style="background:var(--bg);border-radius:12px;padding:1rem">
          <div style="color:#f5d060;font-size:.85rem;margin-bottom:.5rem">&#9733;&#9733;&#9733;&#9733;&#9733;</div>
          <p style="font-size:.8rem;color:var(--text);line-height:1.65;margin:0 0 .75rem;font-style:italic">"Le comparatif RGPD vs Loi 2008-12 nous a ete tres utile pour notre dossier d'exportation vers UE."</p>
          <div style="display:flex;align-items:center;gap:.5rem">
            <div style="width:30px;height:30px;background:var(--green);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.7rem;font-weight:700;color:#fff">MD</div>
            <div><div style="font-size:.78rem;font-weight:600;color:var(--text)">Moussa Diallo</div><div style="font-size:.72rem;color:var(--muted)">Directeur IT, Dakar</div></div>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- SIDEBAR DROITE -->
  <div style="display:flex;flex-direction:column;gap:1.25rem">

    <!-- EXPERT DPO -->
    <div style="background:var(--white);border:1px solid var(--border);border-radius:14px;overflow:hidden">
      <div style="background:var(--green-dark);padding:.85rem 1.25rem">
        <div style="font-size:.78rem;font-weight:700;color:rgba(255,255,255,.75);text-transform:uppercase;letter-spacing:.07em">Votre expert DPO</div>
      </div>
      <div style="padding:1.25rem">
        <div style="display:flex;align-items:center;gap:.85rem;margin-bottom:.85rem">
          <div style="width:50px;height:50px;background:var(--green);border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:800;color:#fff;font-size:.92rem;flex-shrink:0">HPD</div>
          <div>
            <div style="font-weight:700;color:var(--text);font-size:.92rem">Henry Pierre Diouf</div>
            <div style="font-size:.76rem;color:var(--muted)">DPO certifie Master 2</div>
            <div style="font-size:.73rem;color:var(--muted2)">La Plateforme Numerique, Marseille</div>
          </div>
        </div>
        <p style="font-size:.8rem;color:var(--muted);line-height:1.65;margin:0 0 .85rem">Expert Loi 2008-12 &amp; RGPD. Accompagnement des entreprises senegalaises et africaines dans leur mise en conformite.</p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;margin-bottom:.85rem;font-size:.75rem">
          <div style="background:var(--green-light);border-radius:7px;padding:.5rem;color:var(--green);font-weight:500;text-align:center">&#10003; Loi 2008-12</div>
          <div style="background:var(--green-light);border-radius:7px;padding:.5rem;color:var(--green);font-weight:500;text-align:center">&#10003; RGPD</div>
          <div style="background:var(--green-light);border-radius:7px;padding:.5rem;color:var(--green);font-weight:500;text-align:center">&#10003; IA Act</div>
          <div style="background:var(--green-light);border-radius:7px;padding:.5rem;color:var(--green);font-weight:500;text-align:center">&#10003; DPO Externe</div>
        </div>
        <button data-nav="contact" style="width:100%;background:var(--green);color:#fff;padding:.6rem;border-radius:8px;font-size:.83rem;font-weight:600;border:none;cursor:pointer">Me contacter</button>
      </div>
    </div>

    <!-- LIENS OFFICIELS -->
    <div style="background:var(--white);border:1px solid var(--border);border-radius:14px;overflow:hidden">
      <div style="background:var(--green-dark);padding:.85rem 1.25rem">
        <div style="font-size:.78rem;font-weight:700;color:rgba(255,255,255,.75);text-transform:uppercase;letter-spacing:.07em">Autorites officielles</div>
      </div>
      <div style="padding:1rem">
        <a href="https://www.cdp.sn" target="_blank" style="display:flex;align-items:center;gap:.65rem;padding:.6rem .5rem;border-bottom:1px solid var(--border);text-decoration:none">
          <div style="width:32px;height:32px;background:var(--green-light);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:.68rem;font-weight:800;color:var(--green);flex-shrink:0">CDP</div>
          <div><div style="font-size:.82rem;font-weight:600;color:var(--text)">CDP Senegal</div><div style="font-size:.73rem;color:var(--muted)">cdp.sn</div></div>
        </a>
        <a href="https://www.cnil.fr" target="_blank" style="display:flex;align-items:center;gap:.65rem;padding:.6rem .5rem;border-bottom:1px solid var(--border);text-decoration:none">
          <div style="width:32px;height:32px;background:#e8f0fe;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:.65rem;font-weight:800;color:#185ea5;flex-shrink:0">CNIL</div>
          <div><div style="font-size:.82rem;font-weight:600;color:var(--text)">CNIL France</div><div style="font-size:.73rem;color:var(--muted)">cnil.fr</div></div>
        </a>
        <a href="https://edpb.europa.eu" target="_blank" style="display:flex;align-items:center;gap:.65rem;padding:.6rem .5rem;text-decoration:none">
          <div style="width:32px;height:32px;background:#fde8e8;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:.62rem;font-weight:800;color:#b91c1c;flex-shrink:0">CEPD</div>
          <div><div style="font-size:.82rem;font-weight:600;color:var(--text)">CEPD Europe</div><div style="font-size:.73rem;color:var(--muted)">edpb.europa.eu</div></div>
        </a>
      </div>
    </div>

    <!-- QUIZ -->
    <div style="background:var(--white);border:1px solid var(--border);border-radius:14px;overflow:hidden">
      <div style="background:var(--green-dark);padding:.85rem 1.25rem">
        <div style="font-size:.78rem;font-weight:700;color:rgba(255,255,255,.75);text-transform:uppercase;letter-spacing:.07em">Testez vos connaissances</div>
      </div>
      <div style="padding:1.25rem;text-align:center">
        <div style="font-size:2rem;margin-bottom:.6rem">&#128172;</div>
        <div style="font-size:.88rem;font-weight:700;color:var(--text);margin-bottom:.4rem">Quiz Loi 2008-12 &amp; RGPD</div>
        <div style="font-size:.78rem;color:var(--muted);line-height:1.6;margin-bottom:.85rem">10 questions pour tester vos connaissances sur la protection des donnees</div>
        <button data-nav="guide" style="width:100%;background:var(--green-light);color:var(--green);padding:.6rem;border-radius:8px;font-size:.82rem;font-weight:700;border:none;cursor:pointer">Faire le quiz &rarr;</button>
      </div>
    </div>

    <!-- NEWSLETTER -->
    <div style="background:var(--green);border-radius:14px;padding:1.25rem">
      <div style="font-size:.85rem;font-weight:700;color:#fff;margin-bottom:.35rem">Newsletter DataProtect SN</div>
      <p style="font-size:.77rem;color:rgba(255,255,255,.78);line-height:1.6;margin:0 0 .85rem">CDP, RGPD, IA Act &mdash; l'essentiel chaque semaine. Gratuit, sans spam.</p>
      <input type="text" id="nl-prenom" placeholder="Votre prenom" style="width:100%;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;border-radius:7px;padding:.5rem .75rem;font-size:.8rem;margin-bottom:.45rem;outline:none;box-sizing:border-box">
      <input type="email" id="nl-email" placeholder="votre@email.com" style="width:100%;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;border-radius:7px;padding:.5rem .75rem;font-size:.8rem;margin-bottom:.7rem;outline:none;box-sizing:border-box">
      <button data-nl-btn="1" style="width:100%;background:#fff;color:var(--green);padding:.6rem;border-radius:7px;font-size:.82rem;font-weight:700;border:none;cursor:pointer">S'abonner gratuitement</button>
    </div>

  </div>
</div>
</div>
</div>

<!-- CTA FINAL -->
<div style="background:var(--green-dark);padding:3.5rem 0">
  <div class="container" style="text-align:center">
    <div style="font-size:.75rem;font-weight:700;color:rgba(255,255,255,.6);letter-spacing:.1em;margin-bottom:.75rem;text-transform:uppercase">Passez a l'action</div>
    <h2 style="font-size:clamp(1.5rem,3.5vw,2.2rem);font-weight:800;color:#fff;margin:0 0 .85rem;letter-spacing:-.02em">Votre organisation est-elle conforme a la Loi 2008-12 ?</h2>
    <p style="font-size:.93rem;color:rgba(255,255,255,.7);line-height:1.75;max-width:540px;margin:0 auto 2rem">Faites evaluer votre conformite par Henry Pierre Diouf, DPO certifie Master 2. Reponse sous 48h.</p>
    <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap;margin-bottom:1.5rem">
      <button data-nav="contact" style="background:#fff;color:var(--green);padding:.8rem 1.85rem;border-radius:100px;font-weight:700;font-size:.92rem;border:none;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.2)">Demander un audit gratuit</button>
      <button data-nav="ressources" style="background:transparent;border:2px solid rgba(255,255,255,.4);color:#fff;padding:.78rem 1.75rem;border-radius:100px;font-weight:600;font-size:.9rem;cursor:pointer">Voir les ressources</button>
    </div>
    <div style="display:flex;gap:2rem;justify-content:center;flex-wrap:wrap">
      <span style="font-size:.8rem;color:rgba(255,255,255,.6)"><span style="color:#4ade80">&#10003;</span> Reponse sous 48h</span>
      <span style="font-size:.8rem;color:rgba(255,255,255,.6)"><span style="color:#4ade80">&#10003;</span> DPO certifie Master 2</span>
      <span style="font-size:.8rem;color:rgba(255,255,255,.6)"><span style="color:#4ade80">&#10003;</span> Conforme Loi 2008-12 &amp; RGPD</span>
      <span style="font-size:.8rem;color:rgba(255,255,255,.6)"><span style="color:#4ade80">&#10003;</span> Gratuit et sans engagement</span>
    </div>
  </div>
</div>

</div>
<div class="page" id="page-blog">
<div style="background:var(--green-dark);padding:3rem 0 3.5rem;margin-bottom:-1.5rem">
  <div class="container">
    <div class="section-label" style="color:rgba(255,255,255,.7);background:rgba(255,255,255,.12);display:inline-block;padding:.3rem .8rem;border-radius:100px;margin-bottom:.75rem"> Veille juridique & tech</div>
    <h2 style="font-size:clamp(1.6rem,4vw,2.4rem);font-weight:800;color:#fff;margin:0;letter-spacing:-.03em">Toutes les actualites juridiques</h2>
  </div>
</div>
<section>
<div class="container">
  <div class="section-label">Veille juridique & technologique</div>
  <h2 class="section-title">Toutes les actualités</h2>
  <div class="blog-layout">
    <div>
      <div class="blog-list">

        <div class="article-card" data-article="a1">
          <div class="article-top"><span class="badge b-cdp">CDP · Officiel</span><span class="badge b-new">Récent</span></div>
          <div class="article-title">T2 2025 — La CDP traite 96 dossiers : Wave Digital Finance rejetée, Yassir Sénégal contrôlé</div>
          <div class="article-excerpt">Au 2e trimestre 2025, la CDP a enregistré 5 plaintes, 4 signalements et mené 6 missions de contrôle sur site. La fintech Wave Digital Finance a fait l'objet d'un rejet partiel concernant un partage de données avec l'ARTP.</div>
          <div class="article-meta"><span>📅 Juillet 2025</span><span>⏱ 5 min</span><span>Source : Seneweb / CDP</span></div>
          <span class="read-more">Lire l'article →</span>
        </div>

        <div class="article-card" data-article="a4">
          <div class="article-top"><span class="badge b-cdp">CDP · Officiel</span></div>
          <div class="article-title">T1 2025 — 105 dossiers traités, focus sur la protection de l'enfance numérique et la santé</div>
          <div class="article-excerpt">Au premier trimestre 2025, la CDP a traité 83 déclarations, 19 demandes d'autorisation et 3 réinscriptions. Une tendance à la hausse de la conformité qui s'accélère dans les secteurs de la santé et des télécoms.</div>
          <div class="article-meta"><span>📅 Avril 2025</span><span>⏱ 4 min</span><span>Source : Dakar Actu / CDP</span></div>
          <span class="read-more">Lire l'article →</span>
        </div>

        <div class="article-card" data-article="a5">
          <div class="article-top"><span class="badge b-afrique">Afrique</span></div>
          <div class="article-title">La CDP signe un accord avec Paradigm Initiative lors du RAPDP à Abuja</div>
          <div class="article-excerpt">En marge de l'Assemblée générale du Réseau Africain des Autorités de Protection des Données (RAPDP), la CDP du Sénégal a signé un protocole de coopération avec l'ONG panafricaine Paradigm Initiative pour renforcer l'éducation numérique.</div>
          <div class="article-meta"><span>📅 Mai 2025</span><span>⏱ 3 min</span><span>Source : WeAreTech Africa</span></div>
          <span class="read-more">Lire l'article →</span>
        </div>

        <div class="article-card" data-article="a2">
          <div class="article-top"><span class="badge b-rgpd">RGPD · Europe</span></div>
          <div class="article-title">Bilan RGPD 2025 : 1,15 milliard d'euros d'amendes — TikTok (530M€), Google (325M€), Shein (150M€)</div>
          <div class="article-excerpt">L'année 2025 marque un record absolu pour les sanctions RGPD. Les trois géants numériques cumulent à eux seuls plus d'un milliard d'euros. Ce bilan traduit une posture des autorités de plus en plus offensive face aux manquements organisationnels.</div>
          <div class="article-meta"><span>📅 Jan. 2026</span><span>⏱ 7 min</span><span>Source : RGPD Kit / Digitemis</span></div>
          <span class="read-more">Lire l'article →</span>
        </div>

        <div class="article-card" data-article="a3">
          <div class="article-top"><span class="badge b-tech">IA Act</span></div>
          <div class="article-title">IA Act : la CNIL régule désormais les systèmes d'IA à haut risque depuis août 2025</div>
          <div class="article-excerpt">Depuis août 2025, la CNIL est officiellement l'autorité nationale de régulation de l'intelligence artificielle en France, au titre de l'IA Act européen. Ce changement a des implications directes pour les entreprises sénégalaises exportant vers l'UE.</div>
          <div class="article-meta"><span>📅 Oct. 2025</span><span>⏱ 6 min</span><span>Source : FD Conseil / CNIL</span></div>
          <span class="read-more">Lire l'article →</span>
        </div>

        <div class="article-card" data-article="a6">
          <div class="article-top"><span class="badge b-loi">Législation SN</span></div>
          <div class="article-title">Réforme de la Loi 2008-12 : ce que prévoit le projet en discussion depuis 2022</div>
          <div class="article-excerpt">Un projet de loi est en discussion depuis 2022 pour mettre à jour la Loi 2008-12 : consentement explicite, droit à l'oubli, portabilité des données et amendes pouvant atteindre 2% du chiffre d'affaires pour les violations graves.</div>
          <div class="article-meta"><span>📅 Déc. 2025</span><span>⏱ 8 min</span><span>Source : Move-On-Up / Analyse</span></div>
          <span class="read-more">Lire l'article →</span>
        </div>

      </div>
    </div>
    <div class="sidebar">
      <div class="newsletter-box">
        <h4>📬 Recevoir la veille</h4>
        <p>Actualités CDP, RGPD et droit numérique africain chaque semaine.</p>
        <input class="nl-input" type="text" id="nl-prenom" placeholder="Votre prenom">
        <input class="nl-input" type="email" id="nl-email" placeholder="votre@email.com">
        <button class="nl-btn" data-nl-btn="1">S'abonner gratuitement</button>
        <p class="nl-note">🔒 Vos données ne seront jamais cédées. Loi 2008-12 respectée.</p>
      </div>
      <div class="sidebar-box">
        <h4>Liens officiels</h4>
        <div class="quick-links">
          <a class="quick-link" href="https://www.cdp.sn" target="_blank">🏛️ CDP Sénégal — site officiel<span class="ql-arrow">↗</span></a>
          <a class="quick-link" href="https://www.cnil.fr" target="_blank">🇫🇷 CNIL — autorité française<span class="ql-arrow">↗</span></a>
          <a class="quick-link" href="https://edpb.europa.eu" target="_blank">🇪🇺 CEPD — autorité européenne<span class="ql-arrow">↗</span></a>
          <a class="quick-link" href="https://www.juriafrica.com/lex/loi-2008-12-25-janvier-2008-27575.htm" target="_blank">📄 Texte intégral Loi 2008-12<span class="ql-arrow">↗</span></a>
        </div>
      </div>
      <div class="sidebar-box">
        <h4>Thématiques</h4>
        <div class="tag-cloud">
          <span class="tag-pill">CDP Sénégal</span>
          <span class="tag-pill">Loi 2008-12</span>
          <span class="tag-pill">RGPD</span>
          <span class="tag-pill">IA Act</span>
          <span class="tag-pill">Données biométriques</span>
          <span class="tag-pill">Fintech</span>
          <span class="tag-pill">Santé</span>
          <span class="tag-pill">Enfance numérique</span>
          <span class="tag-pill">RAPDP</span>
          <span class="tag-pill">DPO</span>
        </div>
      </div>
    </div>
  </div>
</div>
</section>
</div>

<!-- =================== PAGE ARTICLE =================== -->
<div class="page" id="page-article">
<div id="article-content" style="min-height:60vh">
  <div style="text-align:center;padding:4rem 2rem;color:var(--muted)">
    <div style="font-size:2rem;margin-bottom:.75rem">📰</div>
    <p>Selectionnez un article dans la veille juridique</p>
  </div>
</div>
</div>
<div class="page" id="page-guide">
<div style="background:var(--green-dark);padding:3rem 0 3.5rem;margin-bottom:-1.5rem">
  <div class="container">
    <div class="section-label" style="color:rgba(255,255,255,.7);background:rgba(255,255,255,.12);display:inline-block;padding:.3rem .8rem;border-radius:100px;margin-bottom:.75rem"> Guide citoyen</div>
    <h2 style="font-size:clamp(1.6rem,4vw,2.4rem);font-weight:800;color:#fff;margin:0;letter-spacing:-.03em">Vos droits sur vos donnees</h2>
  </div>
</div>
<section style="background:var(--white)">
<div class="container">
  <div class="section-label">Guide pratique</div>
  <h2 class="section-title">Vos droits sur vos données personnelles</h2>
  <p class="section-intro">La Loi n°2008-12 du 25 janvier 2008 vous garantit des droits fondamentaux sur toutes les données vous concernant. Voici comment les exercer concrètement au Sénégal.</p>

  <div class="callout" style="margin-bottom:2rem">
    <p><strong>Qu'est-ce qu'une donnée à caractère personnel ?</strong> Toute information permettant d'identifier une personne, directement ou indirectement : nom, prénom, numéro de téléphone, email, photo, adresse IP, numéro CNI, données de santé, etc.</p>
  </div>

  <div class="guide-steps">
    <div class="guide-step open">
      <div class="step-header" data-accordion="1">
        <div class="step-num">1</div>
        <div class="step-title">Le droit d'accès — Savoir ce qu'on détient sur vous</div>
        <div class="step-chevron">▼</div>
      </div>
      <div class="step-body">
        <p>Vous avez le droit de demander à toute organisation (banque, opérateur télécom, employeur, hôpital…) si elle détient des données vous concernant et d'en obtenir une copie.</p>
        <p><strong>Comment exercer ce droit ?</strong> Envoyez une demande écrite, signée et datée, au responsable de traitement ou à son représentant au Sénégal, accompagnée d'une copie de votre pièce d'identité. La réponse doit vous parvenir dans un délai raisonnable. <em>(Art. 48 du Décret d'application)</em></p>
      </div>
    </div>
    <div class="guide-step">
      <div class="step-header" data-accordion="1">
        <div class="step-num">2</div>
        <div class="step-title">Le droit de rectification — Corriger des données inexactes</div>
        <div class="step-chevron">▼</div>
      </div>
      <div class="step-body">
        <p>Si des données vous concernant sont inexactes, incomplètes ou périmées, vous pouvez exiger leur correction ou mise à jour. Ce droit est garanti par la Loi 2008-12.</p>
        <p><strong>Exemples :</strong> adresse incorrecte dans un fichier client, état civil erroné chez un opérateur, informations obsolètes dans un dossier médical.</p>
      </div>
    </div>
    <div class="guide-step">
      <div class="step-header" data-accordion="1">
        <div class="step-num">3</div>
        <div class="step-title">Le droit d'opposition — Refuser certains traitements</div>
        <div class="step-chevron">▼</div>
      </div>
      <div class="step-body">
        <p>Vous pouvez vous opposer, pour des motifs légitimes, au traitement de vos données à caractère personnel — notamment lorsque ce traitement est utilisé à des fins de prospection commerciale ou de marketing direct.</p>
        <p><strong>Comment l'exercer ?</strong> Même procédure que le droit d'accès : demande écrite adressée au responsable de traitement. En cas de refus injustifié, vous pouvez saisir la CDP.</p>
      </div>
    </div>
    <div class="guide-step">
      <div class="step-header" data-accordion="1">
        <div class="step-num">4</div>
        <div class="step-title">Comment saisir la CDP en cas de violation ?</div>
        <div class="step-chevron">▼</div>
      </div>
      <div class="step-body">
        <p>Si vous estimez que vos droits ont été violés, vous pouvez déposer une plainte auprès de la CDP. La Commission peut prononcer des avertissements, des mises en demeure, des sanctions pécuniaires jusqu'à 10 millions de FCFA, ou suspendre un traitement.</p>
        <p><strong>Recours :</strong> Les décisions de la CDP peuvent faire l'objet d'un recours devant la Cour d'appel de Dakar dans un délai de deux mois. <em>(Source : Loi 2008-12, Art. 39)</em></p>
        <p>Site de la CDP : <a href="https://www.cdp.sn" target="_blank" style="color:var(--green)">www.cdp.sn</a></p>
      </div>
    </div>
    <div class="guide-step">
      <div class="step-header" data-accordion="1">
        <div class="step-num">5</div>
        <div class="step-title">Les obligations des entreprises envers vous</div>
        <div class="step-chevron">▼</div>
      </div>
      <div class="step-body">
        <p>Toute organisation qui collecte vos données doit respecter plusieurs principes fondamentaux issus de la Loi 2008-12 :</p>
        <ul>
          <li>Vous informer clairement de la finalité du traitement</li>
          <li>Obtenir votre consentement pour les traitements sensibles</li>
          <li>Conserver vos données uniquement le temps nécessaire</li>
          <li>Sécuriser vos données contre tout accès non autorisé</li>
          <li>Déclarer les traitements à la CDP avant leur mise en œuvre</li>
          <li>Vous notifier en cas de violation de vos données</li>
        </ul>
      </div>
    </div>
  </div>

  <div style="margin-top:3rem">
    <div class="section-label">Quiz interactif</div>
    <h3 class="section-title" style="font-size:1.6rem">Testez vos connaissances</h3>
    <div class="quiz-container">
      <div class="quiz-progress"><div class="quiz-bar" id="quizBar" style="width:0%"></div></div>
      <div class="quiz-card" id="quizCard"></div>
    </div>
  </div>
</div>
</section>
</div>

<!-- =================== PAGE RESSOURCES =================== -->
<div class="page" id="page-ressources">
<div style="background:var(--green-dark);padding:3rem 0 3.5rem;margin-bottom:-1.5rem">
  <div class="container">
    <div class="section-label" style="color:rgba(255,255,255,.7);background:rgba(255,255,255,.12);display:inline-block;padding:.3rem .8rem;border-radius:100px;margin-bottom:.75rem"> Centre de ressources</div>
    <h2 style="font-size:clamp(1.6rem,4vw,2.4rem);font-weight:800;color:#fff;margin:0;letter-spacing:-.03em">Documents & outils pratiques</h2>
  </div>
</div>
<section>
<div class="container">
  <div class="section-label">Centre de ressources</div>
  <h2 class="section-title">Documents & outils pratiques</h2>
  <p class="section-intro">Guides, modèles et checklists pour vous aider à comprendre vos droits ou mettre votre organisation en conformité avec la Loi 2008-12 et le RGPD.</p>

  <div class="ressources-filters">
    <button class="filter-btn active" data-filter="all">Tous</button>
    <button class="filter-btn" data-filter="guide">Guides</button>
    <button class="filter-btn" data-filter="modele">Modèles</button>
    <button class="filter-btn" data-filter="checklist">Checklists</button>
    <button class="filter-btn" data-filter="loi">Textes de loi</button>
  </div>

  <div class="ressources-grid">
    <div class="res-card" data-cat="guide">
      <div class="res-badge-new">Nouveau</div>
      <div class="res-icon">📖</div>
      <h4>Guide citoyen — Vos droits en 10 points</h4>
      <p>Comprendre la Loi 2008-12 simplement : droits d'accès, rectification, opposition, recours auprès de la CDP.</p>
      <div class="res-meta"><span class="res-type">PDF · Gratuit</span><a class="res-dl" style="cursor:pointer" href="/docs/guide-citoyen-droits.html" target="_blank">Accéder →</a></div>
    </div>
    <div class="res-card" data-cat="modele">
      <div class="res-icon">🗂️</div>
      <h4>Modèle de registre des traitements</h4>
      <p>Tableau conforme à la réglementation sénégalaise. Colonnes : finalité, catégories de données, durée de conservation, destinataires, mesures de sécurité.</p>
      <div class="res-meta"><span class="res-type">XLSX · Gratuit</span><a class="res-dl" style="cursor:pointer" href="/docs/registre-traitements.html" target="_blank">Télécharger →</a></div>
    </div>
    <div class="res-card" data-cat="checklist">
      <div class="res-icon">✅</div>
      <h4>Checklist conformité Loi 2008-12</h4>
      <p>30 points de contrôle pour vérifier la conformité de votre organisation à la loi sénégalaise sur la protection des données personnelles.</p>
      <div class="res-meta"><span class="res-type">PDF · Gratuit</span><a class="res-dl" style="cursor:pointer" href="/docs/checklist-loi-2008-12.html" target="_blank">Télécharger →</a></div>
    </div>
    <div class="res-card" data-cat="checklist">
      <div class="res-icon">🇪🇺</div>
      <h4>Checklist RGPD pour entreprises sénégalaises</h4>
      <p>Spécialement conçue pour les entreprises qui exportent vers l'UE ou traitent des données de résidents européens.</p>
      <div class="res-meta"><span class="res-type">PDF · Gratuit</span><a class="res-dl" style="cursor:pointer" href="/docs/checklist-rgpd-entreprises-sn.html" target="_blank">Télécharger →</a></div>
    </div>
    <div class="res-card" data-cat="modele">
      <div class="res-icon">📜</div>
      <h4>Modèle de politique de confidentialité</h4>
      <p>Adapté au droit sénégalais et compatible RGPD. Personnalisable pour site web, application mobile ou service en ligne.</p>
      <div class="res-meta"><span class="res-type">DOCX · Gratuit</span><a class="res-dl" style="cursor:pointer" href="/docs/modele-politique-confidentialite.html" target="_blank">Télécharger →</a></div>
    </div>
    <div class="res-card" data-cat="modele">
      <div class="res-icon">⚠️</div>
      <h4>Modèle d'Analyse d'Impact (AIPD)</h4>
      <p>Méthode et modèle pour les traitements présentant un risque élevé pour les droits et libertés des personnes concernées.</p>
      <div class="res-meta"><span class="res-type">DOCX · Gratuit</span><a class="res-dl" style="cursor:pointer" href="/docs/guide-citoyen-droits.html" target="_blank">Télécharger →</a></div>
    </div>
    <div class="res-card" data-cat="loi">
      <div class="res-icon">📋</div>
      <h4>Texte intégral — Loi n°2008-12</h4>
      <p>La loi du 25 janvier 2008 sur la protection des données à caractère personnel au Sénégal, version complète et annotée.</p>
      <div class="res-meta"><span class="res-type">PDF · Officiel</span><a class="res-dl" style="cursor:pointer" href="https://www.afapdp.org/wp-content/uploads/2018/05/Senegal-texte-de-loi-2008.pdf" target="_blank">Télécharger →</a></div>
    </div>
    <div class="res-card" data-cat="guide">
      <div class="res-icon">🌍</div>
      <h4>Panorama africain des lois data</h4>
      <p>Comparatif Sénégal, Maroc, Rwanda, Kenya, Nigeria, Tunisie, Ghana — 39 des 55 pays africains disposent d'une loi en 2025.</p>
      <div class="res-meta"><span class="res-type">PDF · Gratuit</span><a class="res-dl" style="cursor:pointer" href="/docs/checklist-rgpd-entreprises-sn.html" target="_blank">Télécharger →</a></div>
    </div>
    <div class="res-card" data-cat="guide">
      <div class="res-icon">🤖</div>
      <h4>Guide IA & protection des données</h4>
      <p>Comment l'IA Act européen (en vigueur depuis 2025) affecte les entreprises sénégalaises qui utilisent ou exportent des systèmes d'IA vers l'UE.</p>
      <div class="res-meta"><span class="res-type">PDF · Gratuit</span><a class="res-dl" style="cursor:pointer" href="/docs/guide-citoyen-droits.html" target="_blank">Télécharger →</a></div>
    </div>
  </div>
</div>
</section>
</div>

<!-- =================== PAGE COMPARATIF =================== -->
<div class="page" id="page-comparatif">
<div style="background:var(--green-dark);padding:3rem 0 3.5rem;margin-bottom:-1.5rem">
  <div class="container">
    <div class="section-label" style="color:rgba(255,255,255,.7);background:rgba(255,255,255,.12);display:inline-block;padding:.3rem .8rem;border-radius:100px;margin-bottom:.75rem"> Analyse comparative</div>
    <h2 style="font-size:clamp(1.6rem,4vw,2.4rem);font-weight:800;color:#fff;margin:0;letter-spacing:-.03em">RGPD vs Loi 2008-12</h2>
  </div>
</div>
<section>
<div class="container">
  <div class="section-label">Analyse comparative</div>
  <h2 class="section-title">RGPD vs Loi 2008-12 du Sénégal</h2>
  <p class="section-intro">Un comparatif sourcé entre le règlement européen (RGPD) et la loi sénégalaise sur la protection des données personnelles. Essentiel pour toute entreprise sénégalaise opérant avec des partenaires européens.</p>

  <div class="compare-grid">
    <div class="compare-card">
      <div class="compare-header">
        <h3>🇸🇳 Loi n°2008-12 — Sénégal</h3>
        <p>Promulguée le 25 janvier 2008 · Autorité : CDP</p>
      </div>
      <div class="compare-body">
        <div class="compare-row"><span class="cr-label">Entrée en vigueur</span><span class="cr-val">25 janvier 2008 (CDP active depuis fév. 2013)</span></div>
        <div class="compare-row"><span class="cr-label">Autorité de contrôle</span><span class="cr-val">Commission des Données Personnelles (CDP) — Dakar</span></div>
        <div class="compare-row"><span class="cr-label">Amende maximale</span><span class="cr-val">10 millions FCFA (~15 200 €)</span></div>
        <div class="compare-row"><span class="cr-label">Sanction pénale</span><span class="cr-val">Oui — renvoi au Code pénal et loi sur la cybercriminalité</span></div>
        <div class="compare-row"><span class="cr-label">DPO obligatoire ?</span><span class="cr-val">Non — recommandé, pas obligatoire</span></div>
        <div class="compare-row"><span class="cr-label">Formalité préalable</span><span class="cr-val">Déclaration ou autorisation auprès de la CDP</span></div>
        <div class="compare-row"><span class="cr-label">Droit à l'oubli</span><span class="cr-val">Non prévu explicitement (projet de réforme en cours)</span></div>
        <div class="compare-row"><span class="cr-label">Portabilité</span><span class="cr-val">Non prévue (en discussion dans la réforme)</span></div>
        <div class="compare-row"><span class="cr-label">Inspiration</span><span class="cr-val">Convention 108 du Conseil de l'Europe + modèle CNIL</span></div>
      </div>
    </div>
    <div class="compare-card">
      <div class="compare-header">
        <h3>🇪🇺 RGPD — Règlement européen</h3>
        <p>En vigueur depuis le 25 mai 2018 · Autorité : CEPD + CNIL</p>
      </div>
      <div class="compare-body">
        <div class="compare-row"><span class="cr-label">Entrée en vigueur</span><span class="cr-val">25 mai 2018 (adopté en avril 2016)</span></div>
        <div class="compare-row"><span class="cr-label">Autorité de contrôle</span><span class="cr-val">CEPD (UE) + autorité nationale (ex : CNIL en France)</span></div>
        <div class="compare-row"><span class="cr-label">Amende maximale</span><span class="cr-val">20 M€ ou 4% du CA mondial (le plus élevé)</span></div>
        <div class="compare-row"><span class="cr-label">Sanction pénale</span><span class="cr-val">Selon les États membres — possible</span></div>
        <div class="compare-row"><span class="cr-label">DPO obligatoire ?</span><span class="cr-val">Oui, pour certaines catégories d'organisations</span></div>
        <div class="compare-row"><span class="cr-label">Formalité préalable</span><span class="cr-val">Pas de déclaration — accountability (responsabilité démontrée)</span></div>
        <div class="compare-row"><span class="cr-label">Droit à l'oubli</span><span class="cr-val">✅ Oui — Art. 17 du RGPD</span></div>
        <div class="compare-row"><span class="cr-label">Portabilité</span><span class="cr-val">✅ Oui — Art. 20 du RGPD</span></div>
        <div class="compare-row"><span class="cr-label">Champ d'application</span><span class="cr-val">Extra-territorial — s'applique à tout acteur traitant des données de résidents UE</span></div>
      </div>
    </div>
    <div class="compare-match">
      <strong>⚡ Point clé pour les entreprises sénégalaises :</strong> Le RGPD s'applique à vous dès que vous traitez des données de résidents européens — même si vous êtes basé à Dakar. Les amendes peuvent atteindre 4% de votre chiffre d'affaires mondial. La conformité à la Loi 2008-12 ne suffit pas. <a data-nav="contact" style="color:var(--green);font-weight:500;cursor:pointer">Contactez-nous pour un audit →</a>
    </div>
  </div>

  <div style="margin-top:3rem">
    <h3 class="section-title" style="font-size:1.5rem">Points communs essentiels</h3>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:1rem;margin-top:1.5rem">
      <div style="background:var(--white);border:1px solid var(--border);border-radius:12px;padding:1.25rem">
        <div style="font-size:1.3rem;margin-bottom:.6rem">🎯</div>
        <h4 style="font-size:.92rem;font-weight:500;margin-bottom:.3rem">Finalité déterminée</h4>
        <p style="font-size:.82rem;color:var(--muted)">Les données ne peuvent être collectées que pour une finalité précise, légitime et explicitement définie.</p>
      </div>
      <div style="background:var(--white);border:1px solid var(--border);border-radius:12px;padding:1.25rem">
        <div style="font-size:1.3rem;margin-bottom:.6rem">📏</div>
        <h4 style="font-size:.92rem;font-weight:500;margin-bottom:.3rem">Minimisation des données</h4>
        <p style="font-size:.82rem;color:var(--muted)">Seules les données strictement nécessaires à la finalité peuvent être collectées et traitées.</p>
      </div>
      <div style="background:var(--white);border:1px solid var(--border);border-radius:12px;padding:1.25rem">
        <div style="font-size:1.3rem;margin-bottom:.6rem">🔒</div>
        <h4 style="font-size:.92rem;font-weight:500;margin-bottom:.3rem">Sécurité obligatoire</h4>
        <p style="font-size:.82rem;color:var(--muted)">Des mesures techniques et organisationnelles appropriées doivent protéger les données contre toute atteinte.</p>
      </div>
      <div style="background:var(--white);border:1px solid var(--border);border-radius:12px;padding:1.25rem">
        <div style="font-size:1.3rem;margin-bottom:.6rem">👤</div>
        <h4 style="font-size:.92rem;font-weight:500;margin-bottom:.3rem">Droits des personnes</h4>
        <p style="font-size:.82rem;color:var(--muted)">Accès, rectification et opposition sont garantis par les deux textes. Le RGPD va plus loin avec l'effacement et la portabilité.</p>
      </div>
    </div>
  </div>
</div>
</section>
</div>

<!-- =================== PAGE ABOUT =================== -->
<div class="page" id="page-about">
<div style="background:var(--green-dark);padding:3rem 0 3.5rem;margin-bottom:-1.5rem"><div class="container"><div class="section-label" style="color:rgba(255,255,255,.7);background:rgba(255,255,255,.12);display:inline-block;padding:.3rem .8rem;border-radius:100px;margin-bottom:.75rem">A propos</div><h2 style="font-size:clamp(1.6rem,4vw,2.4rem);font-weight:800;color:#fff;margin:0;letter-spacing:-.03em">Henry Pierre Diouf</h2></div></div>
<section style="background:var(--white);padding:0 0 4rem">
<div class="container">

  <!-- Hero about -->
  <div style="background:linear-gradient(135deg,var(--green-dark) 0%,var(--navy-mid) 100%);border-radius:0 0 32px 32px;padding:4rem 2rem 5rem;margin-bottom:-3rem;color:#fff;text-align:center">
    <div style="width:90px;height:90px;background:rgba(255,255,255,.15);border:3px solid rgba(255,255,255,.4);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:2rem;font-weight:700;margin:0 auto 1.25rem;letter-spacing:-.02em">HPD</div>
    <h1 style="font-size:clamp(1.6rem,4vw,2.2rem);font-weight:700;margin:0 0 .5rem;letter-spacing:-.03em">Henry Pierre Diouf</h1>
    <p style="font-size:1.05rem;opacity:.88;margin:0 0 1.25rem">Delegue a la Protection des Donnees (DPO) &mdash; Master 2</p>
    <div style="display:flex;gap:.75rem;justify-content:center;flex-wrap:wrap">
      <span style="background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);border-radius:100px;padding:.35rem .9rem;font-size:.8rem;font-weight:500">La Plateforme Numerique &mdash; Marseille</span>
      <span style="background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);border-radius:100px;padding:.35rem .9rem;font-size:.8rem;font-weight:500">Expert Loi 2008-12 &amp; RGPD</span>
      <span style="background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);border-radius:100px;padding:.35rem .9rem;font-size:.8rem;font-weight:500">Consultant independant</span>
    </div>
  </div>

  <!-- Cards stats -->
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:1rem;margin:0 1rem 3rem;position:relative;z-index:2">
    <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:1.4rem;text-align:center;box-shadow:var(--shadow)">
      <div style="font-size:1.9rem;font-weight:800;color:var(--green);line-height:1">M2</div>
      <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem">Niveau de diplome</div>
    </div>
    <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:1.4rem;text-align:center;box-shadow:var(--shadow)">
      <div style="font-size:1.9rem;font-weight:800;color:var(--green);line-height:1">2</div>
      <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem">Legislations maitrisees</div>
    </div>
    <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:1.4rem;text-align:center;box-shadow:var(--shadow)">
      <div style="font-size:1.9rem;font-weight:800;color:var(--green);line-height:1">55+</div>
      <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem">Pays africains suivis</div>
    </div>
    <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:1.4rem;text-align:center;box-shadow:var(--shadow)">
      <div style="font-size:1.9rem;font-weight:800;color:var(--green);line-height:1">100%</div>
      <div style="font-size:.78rem;color:var(--muted);margin-top:.3rem">Independant &amp; neutre</div>
    </div>
  </div>

  <!-- Profil + expertise -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:2rem;margin-bottom:3rem">
    <div>
      <h2 style="font-size:1.35rem;font-weight:700;color:var(--text);margin:0 0 1rem;letter-spacing:-.02em">Qui suis-je ?</h2>
      <p style="color:var(--muted);line-height:1.85;font-size:.94rem">Passionne par l&rsquo;intersection du droit et du numerique, j&rsquo;ai cree DataProtect Senegal pour combler un vide : rendre accessible la reglementation sur la protection des donnees personnelles au Senegal et en Afrique.</p>
      <p style="color:var(--muted);line-height:1.85;font-size:.94rem;margin-top:.75rem">Issu d&rsquo;une formation Master 2 specialisee a La Plateforme Numerique de Marseille, j&rsquo;accompagne entreprises et organisations dans leur mise en conformite avec la Loi 2008-12 et le RGPD.</p>
      <p style="color:var(--muted);line-height:1.85;font-size:.94rem;margin-top:.75rem">Mon approche : pedagogie, rigueur juridique et solutions concretes adaptees au contexte africain.</p>
      <div style="display:flex;gap:.75rem;margin-top:1.5rem;flex-wrap:wrap">
        <a href="mailto:henrypierrediouf@gmail.com" style="background:var(--green);color:#fff;padding:.65rem 1.3rem;border-radius:100px;font-size:.88rem;font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:.4rem;box-shadow:0 2px 8px rgba(26,107,58,.2)">&#9993; Me contacter</a>
        <a data-nav="contact" style="cursor:pointer;border:2px solid var(--green);color:var(--green);padding:.62rem 1.3rem;border-radius:100px;font-size:.88rem;font-weight:600;text-decoration:none;display:inline-flex;align-items:center;gap:.4rem">Demander un audit</a>
      </div>
    </div>
    <div>
      <h2 style="font-size:1.35rem;font-weight:700;color:var(--text);margin:0 0 1rem;letter-spacing:-.02em">Domaines d&rsquo;expertise</h2>
      <div style="display:flex;flex-direction:column;gap:.6rem">
        <div style="background:var(--bg);border-radius:var(--radius-sm);padding:.85rem 1rem;display:flex;align-items:center;gap:.75rem;font-size:.88rem">
          <span style="width:36px;height:36px;background:var(--green-light);border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:1rem">&#128737;</span>
          <div><strong style="color:var(--text)">Conformite Loi 2008-12</strong><br><span style="color:var(--muted);font-size:.8rem">Declaration CDP, registre traitements, AIPD</span></div>
        </div>
        <div style="background:var(--bg);border-radius:var(--radius-sm);padding:.85rem 1rem;display:flex;align-items:center;gap:.75rem;font-size:.88rem">
          <span style="width:36px;height:36px;background:#e8f0fb;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:1rem">&#127482;</span>
          <div><strong style="color:var(--text)">Conformite RGPD</strong><br><span style="color:var(--muted);font-size:.8rem">Audit, DPA, transferts internationaux, droits</span></div>
        </div>
        <div style="background:var(--bg);border-radius:var(--radius-sm);padding:.85rem 1rem;display:flex;align-items:center;gap:.75rem;font-size:.88rem">
          <span style="width:36px;height:36px;background:#fdf6e3;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:1rem">&#129302;</span>
          <div><strong style="color:var(--text)">IA Act &amp; nouvelles technologies</strong><br><span style="color:var(--muted);font-size:.8rem">Classification risques IA, conformite systemes IA</span></div>
        </div>
        <div style="background:var(--bg);border-radius:var(--radius-sm);padding:.85rem 1rem;display:flex;align-items:center;gap:.75rem;font-size:.88rem">
          <span style="width:36px;height:36px;background:var(--green-light);border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:1rem">&#127757;</span>
          <div><strong style="color:var(--text)">Droit africain des donnees</strong><br><span style="color:var(--muted);font-size:.8rem">Panorama 55 pays, RAPDP, harmonisation</span></div>
        </div>
      </div>
    </div>
  </div>

  <!-- Formation + certifications -->
  <div style="background:var(--bg);border-radius:var(--radius);padding:2rem;margin-bottom:2rem">
    <h2 style="font-size:1.2rem;font-weight:700;color:var(--text);margin:0 0 1.5rem;letter-spacing:-.02em">Formation &amp; Parcours</h2>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem">
      <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius-sm);padding:1.1rem;position:relative;overflow:hidden">
        <div style="position:absolute;top:0;left:0;width:4px;height:100%;background:var(--green)"></div>
        <div style="padding-left:.75rem">
          <div style="font-size:.75rem;color:var(--muted);font-weight:600;letter-spacing:.05em;margin-bottom:.25rem">FORMATION INITIALE</div>
          <div style="font-weight:700;color:var(--text);font-size:.95rem">Master 2 &mdash; DPO</div>
          <div style="color:var(--muted);font-size:.83rem;margin-top:.2rem">La Plateforme Numerique, Marseille</div>
          <div style="color:var(--muted2);font-size:.78rem;margin-top:.15rem">Droit du Numerique &mdash; Protection des Donnees</div>
        </div>
      </div>
      <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius-sm);padding:1.1rem;position:relative;overflow:hidden">
        <div style="position:absolute;top:0;left:0;width:4px;height:100%;background:var(--blue)"></div>
        <div style="padding-left:.75rem">
          <div style="font-size:.75rem;color:var(--muted);font-weight:600;letter-spacing:.05em;margin-bottom:.25rem">SPECIALISATION</div>
          <div style="font-weight:700;color:var(--text);font-size:.95rem">RGPD &amp; Loi 2008-12</div>
          <div style="color:var(--muted);font-size:.83rem;margin-top:.2rem">Droit senegalais et europeen</div>
          <div style="color:var(--muted2);font-size:.78rem;margin-top:.15rem">Conformite, audit, AIPD, transferts</div>
        </div>
      </div>
      <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius-sm);padding:1.1rem;position:relative;overflow:hidden">
        <div style="position:absolute;top:0;left:0;width:4px;height:100%;background:var(--gold)"></div>
        <div style="padding-left:.75rem">
          <div style="font-size:.75rem;color:var(--muted);font-weight:600;letter-spacing:.05em;margin-bottom:.25rem">VEILLE CONTINUE</div>
          <div style="font-weight:700;color:var(--text);font-size:.95rem">Droit africain des donnees</div>
          <div style="color:var(--muted);font-size:.83rem;margin-top:.2rem">RAPDP, CDP, 55 legislations</div>
          <div style="color:var(--muted2);font-size:.78rem;margin-top:.15rem">Actualites juridiques et regulatoires</div>
        </div>
      </div>
      <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius-sm);padding:1.1rem;position:relative;overflow:hidden">
        <div style="position:absolute;top:0;left:0;width:4px;height:100%;background:#7c3aed"></div>
        <div style="padding-left:.75rem">
          <div style="font-size:.75rem;color:var(--muted);font-weight:600;letter-spacing:.05em;margin-bottom:.25rem">TECHNOLOGIES</div>
          <div style="font-weight:700;color:var(--text);font-size:.95rem">IA Act &amp; Numerique</div>
          <div style="color:var(--muted);font-size:.83rem;margin-top:.2rem">Intelligence artificielle, cybersecurite</div>
          <div style="color:var(--muted2);font-size:.78rem;margin-top:.15rem">Conformite systemes IA, Privacy by Design</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Services DPO externe -->
  <div style="background:var(--green-dark);border-radius:var(--radius);padding:2.5rem;color:#fff;text-align:center">
    <h2 style="font-size:1.4rem;font-weight:700;margin:0 0 .75rem;letter-spacing:-.02em">Vous avez besoin d&rsquo;un DPO externe ?</h2>
    <p style="opacity:.88;max-width:560px;margin:0 auto 1.75rem;line-height:1.7;font-size:.95rem">J&rsquo;accompagne entreprises, startups et institutions dans leur mise en conformite avec la Loi 2008-12 et le RGPD. Audit, registre, AIPD, formation, DPO a temps partage.</p>
    <div style="display:flex;gap:1rem;justify-content:center;flex-wrap:wrap">
      <a href="mailto:henrypierrediouf@gmail.com?subject=Demande DPO externe" style="background:#fff;color:var(--green);padding:.75rem 1.75rem;border-radius:100px;font-weight:700;text-decoration:none;font-size:.92rem;box-shadow:0 4px 16px rgba(0,0,0,.15)">Demander un devis</a>
      <a data-nav="contact" style="cursor:pointer;border:2px solid rgba(255,255,255,.6);color:#fff;padding:.72rem 1.65rem;border-radius:100px;font-weight:600;text-decoration:none;font-size:.92rem">En savoir plus</a>
    </div>
  </div>

</div>
</section>
</div>
<div class="page" id="page-contact">
<section><div class="container" style="max-width:900px">
  <div class="section-label">Parlons-nous</div>
  <h2 class="section-title">Contact</h2>
  <p class="section-intro">Une question sur la conformite, un audit a planifier, ou simplement echanger ? Reponse garantie sous 48h.</p>

  <div style="display:grid;grid-template-columns:1fr 1.6fr;gap:2.5rem;margin-top:2rem;align-items:start">

    <!-- Colonne gauche : infos -->
    <div style="display:flex;flex-direction:column;gap:1.25rem">
      <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:1.5rem;box-shadow:var(--shadow-sm)">
        <div style="width:44px;height:44px;background:#e8f5ee;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;margin-bottom:.85rem">&#9993;</div>
        <div style="font-weight:700;color:var(--text);margin-bottom:.25rem">Email</div>
        <a href="mailto:henrypierrediouf@gmail.com" style="color:var(--green);font-size:.9rem;text-decoration:none">henrypierrediouf@gmail.com</a>
        <div style="color:var(--muted2);font-size:.78rem;margin-top:.2rem">Reponse sous 48h ouvrables</div>
      </div>
      <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:1.5rem;box-shadow:var(--shadow-sm)">
        <div style="width:44px;height:44px;background:#e8f5ee;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;margin-bottom:.85rem">&#128222;</div>
        <div style="font-weight:700;color:var(--text);margin-bottom:.25rem">Telephone</div>
        <a href="tel:+33753656131" style="color:var(--green);font-size:.9rem;text-decoration:none">+33 7 53 65 61 31</a>
        <div style="color:var(--muted2);font-size:.78rem;margin-top:.2rem">Lun-Ven, 9h-18h</div>
      </div>
      <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:1.5rem;box-shadow:var(--shadow-sm)">
        <div style="width:44px;height:44px;background:#e8f5ee;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;margin-bottom:.85rem">&#127968;</div>
        <div style="font-weight:700;color:var(--text);margin-bottom:.25rem">Localisation</div>
        <div style="color:var(--muted);font-size:.9rem">Marseille, France</div>
        <div style="color:var(--muted2);font-size:.78rem;margin-top:.2rem">Interventions Senegal &amp; France</div>
      </div>
      <div style="background:var(--green-dark);border-radius:var(--radius);padding:1.5rem;color:#fff">
        <div style="font-weight:700;margin-bottom:.5rem;font-size:.95rem">Services disponibles</div>
        <div style="font-size:.83rem;opacity:.9;line-height:1.8">
          Audit de conformite Loi 2008-12<br>
          Mise en place registre traitements<br>
          Redaction politique confidentialite<br>
          Formation equipes &amp; sensibilisation<br>
          DPO externe a temps partage<br>
          Realisation AIPD
        </div>
      </div>
    </div>

    <!-- Colonne droite : formulaire -->
    <div style="background:var(--white);border:1px solid var(--border);border-radius:var(--radius);padding:2rem;box-shadow:var(--shadow)">
      <h3 style="font-size:1.1rem;font-weight:700;color:var(--text);margin:0 0 1.5rem;letter-spacing:-.02em">Envoyer un message</h3>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem">
        <div>
          <label style="display:block;font-size:.82rem;font-weight:600;color:var(--text);margin-bottom:.4rem">Nom complet <span style="color:var(--red)">*</span></label>
          <input class="form-input" type="text" id="c-nom" placeholder="Votre nom et prenom" style="width:100%;box-sizing:border-box">
        </div>
        <div>
          <label style="display:block;font-size:.82rem;font-weight:600;color:var(--text);margin-bottom:.4rem">Email <span style="color:var(--red)">*</span></label>
          <input class="form-input" type="email" id="c-email" placeholder="votre@email.com" style="width:100%;box-sizing:border-box">
        </div>
      </div>
      <div style="margin-bottom:1rem">
        <label style="display:block;font-size:.82rem;font-weight:600;color:var(--text);margin-bottom:.4rem">Organisation</label>
        <input class="form-input" type="text" id="c-org" placeholder="Votre entreprise ou institution" style="width:100%;box-sizing:border-box">
      </div>
      <div style="margin-bottom:1rem">
        <label style="display:block;font-size:.82rem;font-weight:600;color:var(--text);margin-bottom:.4rem">Type de besoin</label>
        <select class="form-select" id="c-besoin" style="width:100%;box-sizing:border-box">
          <option value="">Selectionnez votre besoin</option>
          <option>Audit de conformite Loi 2008-12</option>
          <option>Mise en conformite RGPD</option>
          <option>Redaction politique de confidentialite</option>
          <option>Formation / sensibilisation</option>
          <option>DPO externe</option>
          <option>Realisation AIPD</option>
          <option>Question generale</option>
          <option>Autre</option>
        </select>
      </div>
      <div style="margin-bottom:1.5rem">
        <label style="display:block;font-size:.82rem;font-weight:600;color:var(--text);margin-bottom:.4rem">Message <span style="color:var(--red)">*</span></label>
        <textarea class="form-input" id="c-message" placeholder="Decrivez votre besoin ou votre question en detail..." style="width:100%;box-sizing:border-box;min-height:130px;resize:vertical"></textarea>
      </div>
      <button class="btn-primary" data-contact-btn="1" style="width:100%;justify-content:center;padding:.85rem">Envoyer le message &rarr;</button>
      <p style="font-size:.75rem;color:var(--muted2);margin-top:.85rem;text-align:center;line-height:1.6">En soumettant ce formulaire, vous acceptez notre <a data-nav="politique-confidentialite" style="color:var(--green);cursor:pointer">politique de confidentialite</a>. Vos donnees ne seront jamais vendues.</p>
    </div>
  </div>

  


</div></section>
</div>
<div class="page" id="page-politique-confidentialite">
<section><div class="container" style="max-width:860px">
<a data-nav="home" style="cursor:pointer;color:var(--green);font-size:.88rem;display:inline-block;margin-bottom:1.5rem">&larr; Retour</a>
<div class="section-label">Protection des donnees</div>
<h2 class="section-title">Politique de confidentialite</h2>
<div style="background:var(--white);border:1px solid var(--border);border-radius:16px;padding:2.5rem;margin-top:1.5rem;line-height:1.9;font-size:.92rem">

<div style="background:var(--green-light);border-left:4px solid var(--green);border-radius:0 10px 10px 0;padding:1rem 1.25rem;margin-bottom:2rem;font-size:.85rem">
<strong>Version 2.0 &mdash; Avril 2026</strong><br>
Conforme a la <strong>Loi n&deg;2008-12 du 25 janvier 2008</strong> sur la protection des donnees personnelles au Senegal et au <strong>Reglement (UE) 2016/679 (RGPD)</strong>.
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">1. Identite du responsable du traitement</h3>
<div style="background:var(--bg);border-radius:10px;padding:1.1rem 1.25rem;font-size:.88rem">
<strong>Henry Pierre Diouf</strong><br>
Qualification : Delegue a la Protection des Donnees (DPO) &mdash; Master 2<br>
Structure : La Plateforme Numerique, Marseille, France<br>
Email : henrypierrediouf@gmail.com<br>
Tel : +33 7 53 65 61 31
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">2. Donnees collectees, finalites et bases legales</h3>
<p>Nous appliquons strictement le principe de minimisation des donnees (Art. 5.1.c RGPD &mdash; Art. 18 Loi 2008-12). Seules les donnees strictement necessaires sont collectees.</p>
<div style="overflow-x:auto">
<table style="width:100%;border-collapse:collapse;font-size:.82rem;margin:.75rem 0">
<thead style="background:var(--green);color:#fff">
<tr><th style="padding:.6rem .75rem;text-align:left">Donnees</th><th style="padding:.6rem .75rem;text-align:left">Finalite</th><th style="padding:.6rem .75rem;text-align:left">Base legale</th><th style="padding:.6rem .75rem;text-align:left">Conservation</th></tr>
</thead>
<tbody>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:.6rem .75rem">Nom, email, organisation, message</td><td style="padding:.6rem .75rem">Traitement des demandes de contact</td><td style="padding:.6rem .75rem">Consentement (Art. 7 RGPD &mdash; Art. 18 Loi 2008-12)</td><td style="padding:.6rem .75rem">3 ans</td></tr>
<tr style="background:var(--bg);border-bottom:1px solid var(--border)"><td style="padding:.6rem .75rem">Prenom, email</td><td style="padding:.6rem .75rem">Newsletter DataProtect SN</td><td style="padding:.6rem .75rem">Consentement explicite et specifique</td><td style="padding:.6rem .75rem">Jusqu&rsquo;au desabonnement + 1 an</td></tr>
<tr style="border-bottom:1px solid var(--border)"><td style="padding:.6rem .75rem">Historique conversation chatbot</td><td style="padding:.6rem .75rem">Service d&rsquo;assistance IA</td><td style="padding:.6rem .75rem">Interet legitime &mdash; donnees non persistees</td><td style="padding:.6rem .75rem">Session uniquement</td></tr>
<tr style="background:var(--bg)"><td style="padding:.6rem .75rem">Cookies, donnees de navigation</td><td style="padding:.6rem .75rem">Fonctionnement, securite, preferences</td><td style="padding:.6rem .75rem">Consentement selon categorie</td><td style="padding:.6rem .75rem">13 mois max</td></tr>
</tbody>
</table>
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">3. Destinataires et sous-traitants</h3>
<p>Vos donnees ne sont jamais vendues ni cedees a des tiers commerciaux. Elles peuvent transiter par :</p>
<div style="background:var(--bg);border-radius:10px;padding:1rem 1.25rem;font-size:.85rem">
<strong>Render Services Inc.</strong> (hebergeur) &mdash; Covina, CA, USA &mdash; render.com/privacy<br><br>
<strong>Cohere Inc.</strong> (IA chatbot) &mdash; Toronto, Canada &mdash; les conversations ne sont pas utilisees pour l&rsquo;entrainement du modele dans le cadre de notre accord API.<br><br>
Ces sous-traitants sont lies par des engagements contractuels conformes au RGPD (clauses contractuelles types pour les transferts hors UE).
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">4. Transferts internationaux</h3>
<p>Le site est heberge aux Etats-Unis. Le Senegal n&rsquo;est pas reconnu comme pays adequat par la Commission europeenne. Pour les residents UE, les transferts sont encadres par des <strong>Clauses Contractuelles Types (CCT)</strong> approuvees par la Commission europeenne (Art. 46 RGPD &mdash; Art. 47 Loi 2008-12).</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">5. Mesures de securite</h3>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem;font-size:.83rem">
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>HTTPS / TLS 1.3</strong> &mdash; toutes les communications sont chiffrees</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Mots de passe haches</strong> &mdash; SHA-256, jamais stockes en clair</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Acces restreint</strong> &mdash; admin protege par token d&rsquo;authentification</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Rate limiting</strong> &mdash; protection contre la force brute</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Headers securite</strong> &mdash; X-Frame-Options, X-Content-Type-Options</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Sauvegardes</strong> &mdash; donnees sauvegardees quotidiennement</div>
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">6. Vos droits</h3>
<p>Conformement a l&rsquo;Art. 48 Loi 2008-12 et aux Art. 15-22 RGPD :</p>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem;font-size:.83rem">
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Acces (Art. 15 RGPD)</strong><br>Obtenir copie de vos donnees traitees</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Rectification (Art. 16 RGPD)</strong><br>Corriger des donnees inexactes</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Effacement (Art. 17 RGPD)</strong><br>Demander la suppression de vos donnees</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Opposition (Art. 21 RGPD)</strong><br>S&rsquo;opposer au traitement, notamment commercial</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Portabilite (Art. 20 RGPD)</strong><br>Recevoir vos donnees en format structure (residents UE)</div>
<div style="background:var(--bg);border-radius:8px;padding:.75rem"><strong>Retrait du consentement</strong><br>A tout moment, sans effet retroactif</div>
</div>
<div style="background:#e8f5ee;border-radius:10px;padding:1rem 1.25rem;margin:.75rem 0;font-size:.85rem">
<strong>Exercer vos droits :</strong> henrypierrediouf@gmail.com &mdash; Reponse garantie sous <strong>30 jours</strong> (Art. 12 RGPD).
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">7. Cookies</h3>
<p>Conformement a l&rsquo;Art. 82 LCEN et a la directive ePrivacy, votre consentement est requis avant tout cookie non essentiel.</p>
<div style="font-size:.85rem">
<div style="border:1px solid var(--border);border-radius:8px;padding:.75rem;margin-bottom:.5rem"><strong>Cookies necessaires</strong> &mdash; Base : interet legitime &mdash; Non refusables &mdash; Duree : session</div>
<div style="border:1px solid var(--border);border-radius:8px;padding:.75rem;margin-bottom:.5rem"><strong>Cookies analytiques</strong> &mdash; Base : consentement &mdash; Audience anonymisee &mdash; Duree : 13 mois</div>
<div style="border:1px solid var(--border);border-radius:8px;padding:.75rem"><strong>Cookies personnalisation</strong> &mdash; Base : consentement &mdash; Theme, preferences &mdash; Duree : 12 mois</div>
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">8. Violations de donnees</h3>
<p>En cas de violation, nous nous engageons a notifier la CDP Senegal dans un delai de <strong>72 heures</strong> (Art. 33 RGPD) et a informer les personnes concernees si le risque est eleve (Art. 34 RGPD).</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">9. Autorites de controle</h3>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:.75rem;font-size:.85rem">
<div style="background:var(--bg);border-radius:8px;padding:.85rem"><strong>CDP Senegal</strong><br>www.cdp.sn<br>Autorite creee par la Loi 2008-12</div>
<div style="background:var(--bg);border-radius:8px;padding:.85rem"><strong>CNIL France</strong><br>www.cnil.fr<br>Pour les residents de l&rsquo;UE</div>
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">10. Mise a jour</h3>
<p>Cette politique peut etre mise a jour. Toute modification substantielle sera notifiee par email aux abonnes et via une banniere sur le site. La version en vigueur est celle publiee sur ce site.</p>

</div></div></section></div>
<div class="page" id="page-mentions-legales">
<section><div class="container" style="max-width:860px">
<a data-nav="home" style="cursor:pointer;color:var(--green);font-size:.88rem;display:inline-block;margin-bottom:1.5rem">&larr; Retour</a>
<div class="section-label">Informations legales</div>
<h2 class="section-title">Mentions legales</h2>
<div style="background:var(--white);border:1px solid var(--border);border-radius:16px;padding:2.5rem;margin-top:1.5rem;line-height:1.9;font-size:.92rem">

<h3 style="color:var(--green);font-size:1.05rem;margin:0 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">1. Editeur du site</h3>
<div style="background:var(--bg);border-radius:10px;padding:1.1rem 1.25rem;font-size:.88rem">
<strong>Henry Pierre Diouf</strong><br>
Qualification : Delegue a la Protection des Donnees (DPO) &mdash; Master 2 Droit du Numerique<br>
Structure : La Plateforme Numerique, Marseille, France<br>
Email : henrypierrediouf@gmail.com | Tel : +33 7 53 65 61 31<br>
Nationalite : Senegalaise
</div>
<p style="margin-top:.75rem">Henry Pierre Diouf exerce comme consultant independant specialise en protection des donnees, conformite RGPD et Loi senegalaise 2008-12.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">2. Hebergement</h3>
<div style="background:var(--bg);border-radius:10px;padding:1.1rem 1.25rem;font-size:.88rem">
<strong>Render Services Inc.</strong><br>
440 N Barranca Ave #4133, Covina, CA 91723, Etats-Unis<br>
Site : render.com &mdash; Infrastructure : Google Cloud Platform (us-west1)
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">3. Propriete intellectuelle</h3>
<p>L&rsquo;ensemble du contenu &mdash; textes, analyses, articles, guides, code, design &mdash; est la propriete exclusive de Henry Pierre Diouf, sauf mention contraire.</p>
<p>Toute reproduction ou exploitation commerciale sans accord ecrit prealable est interdite. La reproduction a des fins strictement privees avec citation de la source est toleree.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">4. Limitation de responsabilite</h3>
<p>Les contenus de ce site ont une vocation <strong>exclusivement pedagogique et informative</strong>. Ils ne constituent pas un conseil juridique professionnel.</p>
<p>Henry Pierre Diouf decline toute responsabilite pour : les decisions prises sur la base des contenus publiees &mdash; les erreurs ou omissions eventuelles &mdash; l&rsquo;indisponibilite temporaire du site &mdash; les dommages lies a l&rsquo;utilisation de l&rsquo;assistant IA.</p>
<p>Pour toute situation specifique, consultez un professionnel qualifie ou la CDP Senegal (cdp.sn).</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">5. Assistant IA</h3>
<p>Le chatbot est alimente par <strong>Cohere command-r-plus-08-2024</strong> (Toronto, Canada). Ses reponses sont indicatives, peuvent contenir des inexactitudes et ne remplacent pas un DPO certifie.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">6. Liens externes</h3>
<p>Les liens vers des sites tiers (CDP, CNIL, RAPDP) sont fournis a titre informatif. L&rsquo;editeur n&rsquo;exerce aucun controle sur ces sites et decline toute responsabilite quant a leur contenu.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">7. Droit applicable et juridiction</h3>
<p>Ce site est soumis au droit senegalais (Loi 2008-12) et au droit francais. En cas de litige, et a defaut de resolution amiable, les tribunaux de <strong>Marseille, France</strong> sont seuls competents.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">8. Contact</h3>
<p>henrypierrediouf@gmail.com &mdash; +33 7 53 65 61 31 &mdash; Reponse sous 48h ouvrables.</p>

</div></div></section></div>
<div class="page" id="page-cgu">
<section><div class="container" style="max-width:860px">
<a data-nav="home" style="cursor:pointer;color:var(--green);font-size:.88rem;display:inline-block;margin-bottom:1.5rem">&larr; Retour</a>
<div class="section-label">Cadre contractuel</div>
<h2 class="section-title">Conditions Generales d&rsquo;Utilisation</h2>
<div style="background:var(--white);border:1px solid var(--border);border-radius:16px;padding:2.5rem;margin-top:1.5rem;line-height:1.9;font-size:.92rem">

<div style="background:var(--green-light);border-left:4px solid var(--green);border-radius:0 10px 10px 0;padding:1rem 1.25rem;margin-bottom:2rem;font-size:.85rem">
<strong>Version 1.2 &mdash; En vigueur depuis Avril 2026</strong><br>
L&rsquo;utilisation de ce site implique l&rsquo;acceptation pleine et entiere des presentes CGU.
</div>

<h3 style="color:var(--green);font-size:1.05rem;margin:0 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">1. Objet et champ d&rsquo;application</h3>
<p>Les presentes CGU regissent l&rsquo;acces et l&rsquo;utilisation du site <strong>DataProtect Senegal</strong>, plateforme de sensibilisation a la protection des donnees personnelles, editee par Henry Pierre Diouf, DPO diplome Master 2.</p>
<p>Ces CGU s&rsquo;appliquent a tous les utilisateurs, qu&rsquo;ils resident au Senegal, en France, dans l&rsquo;Union Europeenne ou dans tout autre pays.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">2. Services proposes</h3>
<p>Le site propose gratuitement : articles de veille juridique (Loi 2008-12, RGPD, IA Act) &mdash; guide citoyen sur les droits &mdash; outils pratiques (registre, checklists, modeles) &mdash; assistant IA specialise &mdash; quiz interactif &mdash; newsletter et contact.</p>
<p>L&rsquo;editeur se reserve le droit de modifier ou suspendre tout service a tout moment, sans preavis.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">3. Obligations de l&rsquo;utilisateur</h3>
<p>En utilisant ce site, l&rsquo;utilisateur s&rsquo;engage a : ne pas l&rsquo;utiliser a des fins illicites &mdash; ne pas tenter d&rsquo;acceder sans autorisation aux systemes &mdash; ne pas reproduire les contenus sans autorisation &mdash; fournir des informations exactes dans les formulaires &mdash; ne pas utiliser le chatbot comme unique source de conseil juridique.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">4. Propriete intellectuelle</h3>
<p>Tous les contenus sont proteges par le droit d&rsquo;auteur. La reproduction a des fins privees avec citation de la source est autorisee. Toute exploitation commerciale sans accord ecrit prealable est interdite.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">5. Assistant IA &mdash; Conditions specifiques</h3>
<p>L&rsquo;utilisateur reconnait que : les reponses de l&rsquo;IA sont informatives et non contraignantes &mdash; aucune relation consultant-client ne decoule du chatbot &mdash; les reponses peuvent contenir des erreurs &mdash; pour toute decision, la consultation d&rsquo;un DPO qualifie est recommandee &mdash; les conversations sont traitees par Cohere Inc. (Canada).</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">6. Donnees personnelles</h3>
<p>Le traitement des donnees est regi par notre <strong>Politique de confidentialite</strong>, conforme a la Loi 2008-12 et au RGPD. En soumettant un formulaire, vous consentez expressement au traitement de vos donnees pour les finalites indiquees.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">7. Disponibilite</h3>
<p>Le site est accessible 24h/24, 7j/7, sous reserve de maintenance. Note : heberge sur le plan gratuit de Render, il peut subir des latences au premier acces apres inactivite.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">8. Modification des CGU</h3>
<p>L&rsquo;editeur peut modifier ces CGU a tout moment. Les modifications entrent en vigueur a leur publication. La poursuite de l&rsquo;utilisation vaut acceptation des CGU modifiees.</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">9. Droit applicable et litiges</h3>
<p>CGU soumises au droit senegalais et francais. En cas de litige non resolu amiablement : tribunaux de Marseille, France. Residents UE : possibilite de mediation de la consommation (directive 2013/11/UE).</p>

<h3 style="color:var(--green);font-size:1.05rem;margin:1.5rem 0 .75rem;border-bottom:2px solid var(--green-light);padding-bottom:.4rem">10. Contact</h3>
<p>henrypierrediouf@gmail.com &mdash; +33 7 53 65 61 31 &mdash; Reponse sous 48h ouvrables.</p>

</div></div></section></div>
<!-- FOOTER -->
<footer>
  <div class="footer-inner">
    <div>
      <div class="footer-brand">🇸🇳 DataProtect<span style="color:var(--gold-bright)">SN</span></div>
      <p class="footer-tagline">Plateforme de référence sur la protection des données personnelles au Sénégal. Sensibilisation, veille juridique sourcée et conformité RGPD.</p>
    </div>
    <div class="footer-col">
      <h5>Navigation</h5>
      <a data-nav="home">Accueil</a>
      <a data-nav="blog">Veille juridique</a>
      <a data-nav="guide">Guide citoyen</a>
      <a data-nav="ressources">Ressources</a>
      <a data-nav="comparatif">RGPD vs Loi SN</a>
      <a data-nav="about">À propos</a>
    </div>
    <div class="footer-col">
      <h5>Liens officiels</h5>
      <a href="https://www.cdp.sn" target="_blank">CDP Senegal</a>
      <a href="https://www.cnil.fr" target="_blank">CNIL France</a>
      <a href="https://edpb.europa.eu" target="_blank">CEPD (UE)</a>
      <a href="https://www.juriafrica.com/lex/loi-2008-12-25-janvier-2008-27575.htm" target="_blank">Texte Loi 2008-12</a>
    </div>
    <div class="footer-col">
      <h5>Legal</h5>
      <a data-nav="politique-confidentialite">Politique de confidentialite</a>
      <a data-nav="mentions-legales">Mentions legales</a>
      <a data-nav="cgu">CGU</a>
    </div>
  </div>
  <div class="footer-legal">
    Ce site est fourni à titre informatif et éducatif. Il ne constitue pas un conseil juridique. Pour toute question spécifique, consultez un professionnel qualifié ou la CDP (www.cdp.sn). Les contenus de veille sont sourcés et vérifiés — voir les articles pour les sources originales.
    <div style="margin-top:.5rem"><button id="ck-manage-btn" style="background:none;border:none;color:rgba(255,255,255,.4);font-size:.7rem;cursor:pointer;text-decoration:underline">Gerer mes cookies</button></div>
</div>
</footer>
<div id="chatbot-bubble">
  <div id="chatbot-window">
    <div class="chat-header">
      <div><div class="chat-name">Assistant DataProtect SN</div><div class="chat-status">En ligne</div></div>
      <button class="chat-close" id="chatClose">X</button>
    </div>
    <div class="chat-messages" id="chatMessages">
      <div class="chat-msg bot">Bonjour ! Je suis votre assistant specialise en protection des donnees. Posez vos questions sur la Loi 2008-12, le RGPD, vos droits.</div>
    </div>
    <div class="chat-sugs" id="chatSugs">
      <button class="chat-sug" data-sug="Quels sont mes droits sur mes donnees ?">Mes droits</button>
      <button class="chat-sug" data-sug="Dois-je declarer mon entreprise a la CDP ?">Declaration CDP</button>
      <button class="chat-sug" data-sug="Qu'est-ce qu'un DPO ?">Le DPO</button>
    </div>
    <div class="chat-input-wrap">
      <input type="text" class="chat-input" id="chatInput" placeholder="Votre question...">
      <button class="chat-send" id="chatSend">OK</button>
    </div>
  </div>
  <button id="chatbot-btn" title="Assistant IA DataProtect"><svg width="32" height="32" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg"><line x1="32" y1="4" x2="32" y2="14" stroke="white" stroke-width="3" stroke-linecap="round"/><circle cx="32" cy="4" r="3" fill="white"/><rect x="14" y="14" width="36" height="26" rx="6" fill="rgba(255,255,255,0.15)" stroke="white" stroke-width="2.5"/><circle cx="24" cy="25" r="4" fill="white"/><circle cx="40" cy="25" r="4" fill="white"/><circle cx="25" cy="24" r="1.5" fill="#1a6b3a"/><circle cx="41" cy="24" r="1.5" fill="#1a6b3a"/><rect x="22" y="32" width="20" height="4" rx="2" fill="rgba(255,255,255,0.7)"/><rect x="25" y="33" width="3" height="2" rx="1" fill="#1a6b3a"/><rect x="30" y="33" width="3" height="2" rx="1" fill="#1a6b3a"/><rect x="35" y="33" width="3" height="2" rx="1" fill="#1a6b3a"/><rect x="20" y="42" width="24" height="16" rx="5" fill="rgba(255,255,255,0.15)" stroke="white" stroke-width="2"/><rect x="8" y="44" width="10" height="6" rx="3" fill="rgba(255,255,255,0.15)" stroke="white" stroke-width="2"/><rect x="46" y="44" width="10" height="6" rx="3" fill="rgba(255,255,255,0.15)" stroke="white" stroke-width="2"/><circle cx="32" cy="50" r="3" fill="rgba(255,255,255,0.6)"/></svg></button>
</div>

<div id="cookie-banner"><div class="ck-inner"><div class="ck-text"><h4>Ce site utilise des cookies</h4><p>Conformement a la <strong>Loi 2008-12</strong> et au <strong>RGPD Art. 7</strong>, votre consentement est requis avant toute utilisation de cookies non essentiels.</p></div><div class="ck-btns"><button class="btn-ck-set" id="ck-custom">Personnaliser</button><button class="btn-ck-no" id="ck-refuse">Refuser</button><button class="btn-ck-ok" id="ck-accept">Accepter</button></div></div></div>

<div id="cookie-modal"><div class="cm-box"><h3>Mes preferences cookies</h3><p style="font-size:.76rem;color:var(--muted);margin-bottom:.8rem">Art. 48 Loi 2008-12 et Art. 7 RGPD</p><div class="cm-cat"><div class="cm-cat-head"><span class="cm-cat-title">Necessaires</span><label class="tgl"><input type="checkbox" checked disabled><span class="tgl-s"></span></label></div><div class="cm-cat-desc">Indispensables au fonctionnement.</div></div><div class="cm-cat"><div class="cm-cat-head"><span class="cm-cat-title">Analytiques</span><label class="tgl"><input type="checkbox" id="ck-analytics"><span class="tgl-s"></span></label></div><div class="cm-cat-desc">Comprendre l'usage du site.</div></div><div class="cm-cat"><div class="cm-cat-head"><span class="cm-cat-title">Personnalisation</span><label class="tgl"><input type="checkbox" id="ck-perso"><span class="tgl-s"></span></label></div><div class="cm-cat-desc">Memoriser vos preferences.</div></div><div class="cm-btns"><button class="btn-ck-no" id="ck-modal-refuse">Refuser</button><button class="btn-ck-ok" id="ck-modal-save">Enregistrer</button><button class="btn-ck-ok" id="ck-modal-accept">Accepter tout</button></div></div></div>

<script src="/app.js"></script>
</body>
</html
<footer>
  <div class="footer-inner">
    <div>
      <div class="footer-brand">🇸🇳 DataProtect<span style="color:var(--gold-bright)">SN</span></div>
      <p class="footer-tagline">Plateforme de référence sur la protection des données personnelles au Sénégal. Sensibilisation, veille juridique sourcée et conformité RGPD.</p>
    </div>
    <div class="footer-col">
      <h5>Navigation</h5>
      <a data-nav="home">Accueil</a>
      <a data-nav="blog">Veille juridique</a>
      <a data-nav="guide">Guide citoyen</a>
      <a data-nav="ressources">Ressources</a>
      <a data-nav="comparatif">RGPD vs Loi SN</a>
      <a data-nav="about">À propos</a>
    </div>
    <div class="footer-col">
      <h5>Liens officiels</h5>
      <a href="https://www.cdp.sn" target="_blank">CDP Senegal</a>
      <a href="https://www.cnil.fr" target="_blank">CNIL France</a>
      <a href="https://edpb.europa.eu" target="_blank">CEPD (UE)</a>
      <a href="https://www.juriafrica.com/lex/loi-2008-12-25-janvier-2008-27575.htm" target="_blank">Texte Loi 2008-12</a>
    </div>
    <div class="footer-col">
      <h5>Legal</h5>
      <a data-nav="politique-confidentialite">Politique de confidentialite</a>
      <a data-nav="mentions-legales">Mentions legales</a>
      <a data-nav="cgu">CGU</a>
    </div>
  </div>
  <div class="footer-legal">
    Ce site est fourni à titre informatif et éducatif. Il ne constitue pas un conseil juridique. Pour toute question spécifique, consultez un professionnel qualifié ou la CDP (www.cdp.sn). Les contenus de veille sont sourcés et vérifiés — voir les articles pour les sources originales.
    <div style="margin-top:.5rem"><button id="ck-manage-btn" style="background:none;border:none;color:rgba(255,255,255,.4);font-size:.7rem;cursor:pointer;text-decoration:underline">Gerer mes cookies</button></div>
</div>
</footer>
<div id="chatbot-bubble">
  <div id="chatbot-window">
    <div class="chat-header">
      <div><div class="chat-name">Assistant DataProtect SN</div><div class="chat-status">En ligne</div></div>
      <button class="chat-close" id="chatClose">X</button>
    </div>
    <div class="chat-messages" id="chatMessages">
      <div class="chat-msg bot">Bonjour ! Je suis votre assistant specialise en protection des donnees. Posez vos questions sur la Loi 2008-12, le RGPD, vos droits.</div>
    </div>
    <div class="chat-sugs" id="chatSugs">
      <button class="chat-sug" data-sug="Quels sont mes droits sur mes donnees ?">Mes droits</button>
      <button class="chat-sug" data-sug="Dois-je declarer mon entreprise a la CDP ?">Declaration CDP</button>
      <button class="chat-sug" data-sug="Qu'est-ce qu'un DPO ?">Le DPO</button>
    </div>
    <div class="chat-input-wrap">
      <input type="text" class="chat-input" id="chatInput" placeholder="Votre question...">
      <button class="chat-send" id="chatSend">OK</button>
    </div>
  </div>
  <button id="chatbot-btn" title="Assistant IA DataProtect"><svg width="32" height="32" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg"><line x1="32" y1="4" x2="32" y2="14" stroke="white" stroke-width="3" stroke-linecap="round"/><circle cx="32" cy="4" r="3" fill="white"/><rect x="14" y="14" width="36" height="26" rx="6" fill="rgba(255,255,255,0.15)" stroke="white" stroke-width="2.5"/><circle cx="24" cy="25" r="4" fill="white"/><circle cx="40" cy="25" r="4" fill="white"/><circle cx="25" cy="24" r="1.5" fill="#1a6b3a"/><circle cx="41" cy="24" r="1.5" fill="#1a6b3a"/><rect x="22" y="32" width="20" height="4" rx="2" fill="rgba(255,255,255,0.7)"/><rect x="25" y="33" width="3" height="2" rx="1" fill="#1a6b3a"/><rect x="30" y="33" width="3" height="2" rx="1" fill="#1a6b3a"/><rect x="35" y="33" width="3" height="2" rx="1" fill="#1a6b3a"/><rect x="20" y="42" width="24" height="16" rx="5" fill="rgba(255,255,255,0.15)" stroke="white" stroke-width="2"/><rect x="8" y="44" width="10" height="6" rx="3" fill="rgba(255,255,255,0.15)" stroke="white" stroke-width="2"/><rect x="46" y="44" width="10" height="6" rx="3" fill="rgba(255,255,255,0.15)" stroke="white" stroke-width="2"/><circle cx="32" cy="50" r="3" fill="rgba(255,255,255,0.6)"/></svg></button>
</div>

<div id="cookie-banner"><div class="ck-inner"><div class="ck-text"><h4>Ce site utilise des cookies</h4><p>Conformement a la <strong>Loi 2008-12</strong> et au <strong>RGPD Art. 7</strong>, votre consentement est requis avant toute utilisation de cookies non essentiels.</p></div><div class="ck-btns"><button class="btn-ck-set" id="ck-custom">Personnaliser</button><button class="btn-ck-no" id="ck-refuse">Refuser</button><button class="btn-ck-ok" id="ck-accept">Accepter</button></div></div></div>

<div id="cookie-modal"><div class="cm-box"><h3>Mes preferences cookies</h3><p style="font-size:.76rem;color:var(--muted);margin-bottom:.8rem">Art. 48 Loi 2008-12 et Art. 7 RGPD</p><div class="cm-cat"><div class="cm-cat-head"><span class="cm-cat-title">Necessaires</span><label class="tgl"><input type="checkbox" checked disabled><span class="tgl-s"></span></label></div><div class="cm-cat-desc">Indispensables au fonctionnement.</div></div><div class="cm-cat"><div class="cm-cat-head"><span class="cm-cat-title">Analytiques</span><label class="tgl"><input type="checkbox" id="ck-analytics"><span class="tgl-s"></span></label></div><div class="cm-cat-desc">Comprendre l'usage du site.</div></div><div class="cm-cat"><div class="cm-cat-head"><span class="cm-cat-title">Personnalisation</span><label class="tgl"><input type="checkbox" id="ck-perso"><span class="tgl-s"></span></label></div><div class="cm-cat-desc">Memoriser vos preferences.</div></div><div class="cm-btns"><button class="btn-ck-no" id="ck-modal-refuse">Refuser</button><button class="btn-ck-ok" id="ck-modal-save">Enregistrer</button><button class="btn-ck-ok" id="ck-modal-accept">Accepter tout</button></div></div></div>

<script src="/app.js"></script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(_INDEX_HTML)

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


# ── DOCUMENTS RESSOURCES (integres directement) ──
DOCS = {
    "guide-citoyen-droits": """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Guide Citoyen - Vos Droits - DataProtect SN</title><style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',Arial,sans-serif;color:#1a1a2e;background:#fff}
  .doc-header{background:linear-gradient(135deg,#1a5c34,#1a4f8a);color:#fff;padding:2.5rem}
  .doc-header h1{font-size:1.6rem;font-weight:800;margin-bottom:.5rem}
  .doc-header p{opacity:.8;font-size:.9rem}
  .doc-meta{display:flex;gap:1.5rem;margin-top:1rem;font-size:.8rem;opacity:.75}
  .doc-body{max-width:900px;margin:0 auto;padding:2.5rem}
  h2{color:#1a5c34;font-size:1.1rem;margin:2rem 0 .75rem;padding-bottom:.4rem;border-bottom:2px solid #eaf5ef}
  h3{color:#2c3e50;font-size:.95rem;margin:1.25rem 0 .5rem}
  p{line-height:1.8;color:#374151;font-size:.92rem;margin-bottom:.75rem}
  table{width:100%;border-collapse:collapse;font-size:.85rem;margin:1rem 0}
  th{background:#1a5c34;color:#fff;padding:.65rem .85rem;text-align:left}
  td{padding:.6rem .85rem;border-bottom:1px solid #e5e7eb}
  tr:nth-child(even) td{background:#f8fffe}
  .check-item{display:flex;align-items:flex-start;gap:.75rem;padding:.65rem 0;border-bottom:1px solid #f0f0f0}
  .check-item input{margin-top:3px;accent-color:#1a5c34;flex-shrink:0}
  .highlight{background:#eaf5ef;border-left:4px solid #1a5c34;border-radius:0 8px 8px 0;padding:.85rem 1.1rem;margin:1rem 0;font-size:.88rem}
  .warning{background:#fdf6e3;border-left:4px solid #b8860b;border-radius:0 8px 8px 0;padding:.85rem 1.1rem;margin:1rem 0;font-size:.88rem}
  .danger{background:#fdecea;border-left:4px solid #c0392b;border-radius:0 8px 8px 0;padding:.85rem 1.1rem;margin:1rem 0;font-size:.88rem}
  .footer-doc{background:#f8f7f4;border-top:1px solid #e5e7eb;padding:1.5rem 2.5rem;font-size:.8rem;color:#6b7280;text-align:center;margin-top:3rem}
  .btn-print{background:#1a5c34;color:#fff;border:none;padding:.6rem 1.2rem;border-radius:6px;cursor:pointer;font-size:.85rem;margin-top:1rem}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin:.75rem 0}
  .card-sm{background:#f8fffe;border:1px solid #d1fae5;border-radius:8px;padding:.85rem}
  @media print{.no-print{display:none}}
</style></head>
<body>
<div class="doc-header">
  <h1>Guide Citoyen &mdash; Vos 10 Droits sur vos Donnees Personnelles</h1>
  <p>Comprendre et exercer vos droits selon la Loi 2008-12 du Senegal et le RGPD europeen</p>
  <div class="doc-meta"><span>DataProtect SN &mdash; Henry Pierre Diouf, DPO M2 &mdash; Avril 2026</span></div>
  <button class="btn-print no-print" onclick="window.print()">Imprimer / PDF</button>
</div>
<div class="doc-body">
<div class="highlight"><strong>Saviez-vous ?</strong> La Loi senegalaise n&deg;2008-12 vous accorde des droits sur toutes vos donnees personnelles : votre nom, email, telephone, photo, historique bancaire, donnees de sante... Ces droits s'appliquent envers toute entreprise, administration ou organisation qui detient des informations vous concernant.</div>

<h2>01. Droit d'acces</h2>
<p><strong>Ce que dit la loi :</strong> Art. 48 Loi 2008-12 / Art. 15 RGPD</p>
<p><strong>Concretement :</strong> Vous pouvez demander a toute organisation de vous confirmer si elle detient des donnees vous concernant et d'en obtenir une copie gratuite.</p>
<p><strong>Comment l'exercer :</strong> Envoyez un email ou courrier en precisant votre identite et en demandant l'acces a vos donnees. Reponse obligatoire sous 30 jours.</p>
<h2>02. Droit de rectification</h2>
<p><strong>Ce que dit la loi :</strong> Art. 49 Loi 2008-12 / Art. 16 RGPD</p>
<p><strong>Concretement :</strong> Vous pouvez demander la correction de toute information inexacte ou incomplete vous concernant (adresse erronee, nom mal orthographie, etc.).</p>
<p><strong>Comment l'exercer :</strong> Signalez l'erreur par ecrit avec la correction souhaitee. La rectification doit etre faite sans delai et vous etes informe de la mise a jour.</p>
<h2>03. Droit a l'effacement</h2>
<p><strong>Ce que dit la loi :</strong> Art. 17 RGPD (non encore explicite dans Loi 2008-12)</p>
<p><strong>Concretement :</strong> Vous pouvez demander la suppression de vos donnees quand : elles ne sont plus necessaires, vous retirez votre consentement, vous vous opposez au traitement, ou elles ont ete collectees illegalement.</p>
<p><strong>Comment l'exercer :</strong> Formulez une demande d'effacement. L'organisation doit effacer vos donnees dans 1 mois, sauf exception legale (conservation comptable, litiges en cours).</p>
<h2>04. Droit d'opposition</h2>
<p><strong>Ce que dit la loi :</strong> Art. 50 Loi 2008-12 / Art. 21 RGPD</p>
<p><strong>Concretement :</strong> Vous pouvez vous opposer au traitement de vos donnees, notamment pour la prospection commerciale (publicite, SMS, emails promotionnels). L'opposition a la prospection est absolue.</p>
<p><strong>Comment l'exercer :</strong> Cliquez sur 'Se desabonner' dans tout email commercial. Ou envoyez un email explicite. L'organisation doit cesser immediatement toute prospection.</p>
<h2>05. Droit a la portabilite</h2>
<p><strong>Ce que dit la loi :</strong> Art. 20 RGPD (residents UE uniquement &mdash; reforme Loi 2008-12 en cours)</p>
<p><strong>Concretement :</strong> Vous pouvez recevoir vos donnees dans un format lisible par machine (CSV, JSON) pour les transferer vers un autre prestataire. Ex: transferer votre historique musical d'un service de streaming a un autre.</p>
<p><strong>Comment l'exercer :</strong> Adressez une demande de portabilite. Ce droit s'applique aux donnees que vous avez fournies activement et pour les traitements bases sur consentement ou contrat.</p>
<h2>06. Droit de limitation</h2>
<p><strong>Ce que dit la loi :</strong> Art. 18 RGPD</p>
<p><strong>Concretement :</strong> Vous pouvez demander que vos donnees ne soient plus utilisees (mais pas effacees) pendant une periode, notamment si vous contestez leur exactitude ou avez exerce une opposition.</p>
<p><strong>Comment l'exercer :</strong> Demandez la limitation par ecrit. Vos donnees sont 'gelees' : conservees mais non traitees jusqu'a resolution du litige.</p>
<h2>07. Droit de ne pas subir une decision automatisee</h2>
<p><strong>Ce que dit la loi :</strong> Art. 22 RGPD / Art. 18 Loi 2008-12</p>
<p><strong>Concretement :</strong> Si une decision importante (refus de credit, offre d'emploi, scoring) est prise par un algorithme sans intervention humaine, vous pouvez demander une intervention humaine et contester la decision.</p>
<p><strong>Comment l'exercer :</strong> Demandez explicitement qu'un etre humain revoie la decision automatisee. Cela s'applique aux decisions ayant un effet juridique ou vous affectant significativement.</p>
<h2>08. Droit a l'information</h2>
<p><strong>Ce que dit la loi :</strong> Art. 37-40 Loi 2008-12 / Art. 13-14 RGPD</p>
<p><strong>Concretement :</strong> Toute organisation qui collecte vos donnees doit vous informer au moment de la collecte : qui traite vos donnees, pourquoi, pendant combien de temps, et quels sont vos droits.</p>
<p><strong>Comment l'exercer :</strong> Verifiez systematiquement la politique de confidentialite avant de remplir un formulaire. Si ces informations manquent, l'organisation est en infraction.</p>
<h2>09. Droit de retirer son consentement</h2>
<p><strong>Ce que dit la loi :</strong> Art. 7 RGPD / Art. 18 Loi 2008-12</p>
<p><strong>Concretement :</strong> Si vous avez donne votre consentement pour un traitement, vous pouvez le retirer a tout moment. Le retrait ne remet pas en cause la legalite des traitements anterieurs.</p>
<p><strong>Comment l'exercer :</strong> Desinscrivez-vous de la newsletter, retirez vos autorisations dans les parametres d'une application, ou envoyez un email de retrait. Ce doit etre aussi simple que le consentement initial.</p>
<h2>10. Droit de reclamation</h2>
<p><strong>Ce que dit la loi :</strong> Art. 66 Loi 2008-12 / Art. 77 RGPD</p>
<p><strong>Concretement :</strong> Si vous estimez que vos droits ne sont pas respectes, vous pouvez saisir la Commission des Donnees Personnelles du Senegal (CDP) ou la CNIL pour les residents de l'UE.</p>
<p><strong>Comment l'exercer :</strong> CDP Senegal : www.cdp.sn | CNIL France : www.cnil.fr | Formulez votre plainte en decrivant les faits et les demarches deja effectuees aupres de l'organisation concernee.</p>


<h2>Comment exercer vos droits en pratique ?</h2>
<div class="grid2">
  <div class="card-sm"><strong>1. Identifiez-vous</strong><br><small>Precisez votre nom complet, adresse et une copie de votre piece d'identite si demandee</small></div>
  <div class="card-sm"><strong>2. Precisez votre demande</strong><br><small>Indiquez clairement le droit exerce et les donnees concernees</small></div>
  <div class="card-sm"><strong>3. Conservez une trace</strong><br><small>Gardez une copie de votre demande et notez la date d'envoi</small></div>
  <div class="card-sm"><strong>4. Attendez la reponse</strong><br><small>30 jours pour une reponse (extensible a 3 mois avec justification)</small></div>
  <div class="card-sm"><strong>5. En cas de refus</strong><br><small>Saisissez la CDP (Senegal) ou la CNIL (UE) si votre demande est ignoree</small></div>
  <div class="card-sm"><strong>6. Gratuite</strong><br><small>L'exercice de vos droits est toujours gratuit. Des frais ne peuvent etre exiges que si les demandes sont manifestement excessives.</small></div>
</div>
</div>
<div class="footer-doc">DataProtect Senegal &mdash; Henry Pierre Diouf, DPO M2 &mdash; henrypierrediouf@gmail.com &mdash; cdp.sn &mdash; cnil.fr</div>
</body></html>""",
    "registre-traitements": """<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Registre des Traitements - DataProtect SN</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e; background: #fff; }
  .doc-header { background: linear-gradient(135deg, #1a5c34, #1a4f8a); color: #fff; padding: 2.5rem; }
  .doc-header h1 { font-size: 1.6rem; font-weight: 800; margin-bottom: .5rem; }
  .doc-header p { opacity: .8; font-size: .9rem; }
  .doc-meta { display: flex; gap: 1.5rem; margin-top: 1rem; font-size: .8rem; opacity: .75; }
  .doc-body { max-width: 900px; margin: 0 auto; padding: 2.5rem; }
  h2 { color: #1a5c34; font-size: 1.1rem; margin: 2rem 0 .75rem; padding-bottom: .4rem; border-bottom: 2px solid #eaf5ef; }
  h3 { color: #2c3e50; font-size: .95rem; margin: 1.25rem 0 .5rem; }
  p { line-height: 1.8; color: #374151; font-size: .92rem; margin-bottom: .75rem; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; margin: 1rem 0; }
  th { background: #1a5c34; color: #fff; padding: .65rem .85rem; text-align: left; }
  td { padding: .6rem .85rem; border-bottom: 1px solid #e5e7eb; }
  tr:nth-child(even) td { background: #f8fffe; }
  .check-item { display: flex; align-items: flex-start; gap: .75rem; padding: .65rem 0; border-bottom: 1px solid #f0f0f0; }
  .check-item input { margin-top: 3px; accent-color: #1a5c34; flex-shrink: 0; }
  .highlight { background: #eaf5ef; border-left: 4px solid #1a5c34; border-radius: 0 8px 8px 0; padding: .85rem 1.1rem; margin: 1rem 0; font-size: .88rem; }
  .warning { background: #fdf6e3; border-left: 4px solid #b8860b; border-radius: 0 8px 8px 0; padding: .85rem 1.1rem; margin: 1rem 0; font-size: .88rem; }
  .footer-doc { background: #f8f7f4; border-top: 1px solid #e5e7eb; padding: 1.5rem 2.5rem; font-size: .8rem; color: #6b7280; text-align: center; }
  @media print { .no-print { display: none; } }
  .btn-print { background: #1a5c34; color: #fff; border: none; padding: .6rem 1.2rem; border-radius: 6px; cursor: pointer; font-size: .85rem; margin-top: 1rem; }
</style>
</head>
<body>
<div class="doc-header">
  <h1>Registre des Activites de Traitement</h1>
  <p>Conforme a l'article 18 de la Loi 2008-12 et a l'article 30 du RGPD (UE 2016/679)</p>
  <div class="doc-meta">
    <span>Organisation : ___________________</span>
    <span>Responsable du traitement : ___________________</span>
    <span>Date de mise a jour : ___________________</span>
  </div>
  <button class="btn-print no-print" onclick="window.print()">Imprimer / Sauvegarder PDF</button>
</div>
<div class="doc-body">
  <div class="highlight"><strong>Obligation legale :</strong> Toute organisation traitant des donnees personnelles doit tenir ce registre a jour et le presenter a la CDP sur demande (Art. 18 Loi 2008-12). Il doit etre mis a jour a chaque nouveau traitement.</div>

  <h2>1. Informations sur le responsable du traitement</h2>
  <table>
    <tr><th>Champ</th><th>Information</th></tr>
    <tr><td>Nom de l'organisation</td><td>&nbsp;</td></tr>
    <tr><td>Forme juridique</td><td>&nbsp;</td></tr>
    <tr><td>Adresse du siege</td><td>&nbsp;</td></tr>
    <tr><td>Representant legal</td><td>&nbsp;</td></tr>
    <tr><td>DPO / Referent RGPD</td><td>&nbsp;</td></tr>
    <tr><td>Contact DPO</td><td>&nbsp;</td></tr>
    <tr><td>Numero de declaration CDP</td><td>&nbsp;</td></tr>
  </table>

  <h2>2. Registre des activites de traitement</h2>
  <p>Completer une ligne par activite de traitement. Utiliser plusieurs feuilles si necessaire.</p>

  <table>
    <tr>
      <th>N&deg;</th><th>Nom du traitement</th><th>Finalite</th><th>Base legale</th>
      <th>Categories de donnees</th><th>Personnes concernees</th><th>Destinataires</th>
      <th>Duree conservation</th><th>Transferts hors SN</th><th>Mesures securite</th>
    </tr>
    <tr><td>01</td><td>Gestion RH / paie</td><td>Administration du personnel</td><td>Contrat / Obligation legale</td><td>Identite, salaire, conges, evaluations</td><td>Employes, stagiaires</td><td>DRH, comptabilite, IPRES, CSS</td><td>5 ans apres fin contrat</td><td>Non</td><td>Acces restreint, chiffrement</td></tr>
    <tr><td>02</td><td>Gestion clients / CRM</td><td>Facturation, SAV</td><td>Execution du contrat</td><td>Identite, coordonnees, historique achats</td><td>Clients</td><td>Equipe commerciale, comptabilite</td><td>3 ans apres dernier contact</td><td>Si outil etranger</td><td>HTTPS, MFA, logs acces</td></tr>
    <tr><td>03</td><td>Prospection / newsletter</td><td>Marketing commercial</td><td>Consentement explicite</td><td>Email, telephone, preferences</td><td>Prospects consentants</td><td>Equipe marketing</td><td>Jusqu'au desabonnement</td><td>Si outil etranger</td><td>Gestion consentements</td></tr>
    <tr><td>04</td><td>Video-surveillance</td><td>Securite locaux</td><td>Interet legitime</td><td>Images video</td><td>Employes, visiteurs</td><td>Direction, securite</td><td>30 jours max</td><td>Non</td><td>Acces restreint, affichage</td></tr>
    <tr><td>05</td><td>Site web / cookies</td><td>Audience, UX</td><td>Consentement</td><td>IP, cookies, pages visitees</td><td>Visiteurs</td><td>Equipe web, analytique</td><td>13 mois max</td><td>Si outil etranger</td><td>Banniere consentement</td></tr>
    <tr><td>06</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>07</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>08</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
  </table>

  <h2>3. Bases legales disponibles (Art. 18 Loi 2008-12 / Art. 6 RGPD)</h2>
  <table>
    <tr><th>Base legale</th><th>Conditions</th><th>Exemples</th></tr>
    <tr><td><strong>Consentement</strong></td><td>Libre, specifique, eclaire, explicite, retractable</td><td>Newsletter, cookies analytiques, prospection</td></tr>
    <tr><td><strong>Execution du contrat</strong></td><td>Traitement necessaire a un contrat avec la personne</td><td>Livraison commande, paiement, SAV</td></tr>
    <tr><td><strong>Obligation legale</strong></td><td>Imposition par une loi ou reglementation</td><td>Declarations fiscales, registre du commerce</td></tr>
    <tr><td><strong>Interet legitime</strong></td><td>Interet reel, necessaire, ne primant pas sur les droits</td><td>Securite locaux, prevention fraude</td></tr>
    <tr><td><strong>Mission d'interet public</strong></td><td>Exercice d'une mission publique</td><td>Administrations, hopitaux publics</td></tr>
  </table>

  <div class="warning"><strong>Important :</strong> Certains traitements necessitent une autorisation prealable de la CDP (donnees de sante, biometriques, genetiques, concernant des mineurs). Une simple declaration ne suffit pas.</div>

  <h2>4. Gestion des violations de donnees</h2>
  <table>
    <tr><th>Date</th><th>Nature de la violation</th><th>Donnees concernees</th><th>Personnes affectees</th><th>Actions menees</th><th>Notification CDP</th></tr>
    <tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>
  </table>
</div>
<div class="footer-doc">
  DataProtect Senegal &mdash; Henry Pierre Diouf, DPO M2 &mdash; henrypierrediouf@gmail.com &mdash; +33 7 53 65 61 31<br>
  Document genere le 17/04/2026 &mdash; Pour usage interne uniquement
</div>
</body></html>""",
    "checklist-loi-2008-12": """<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><title>Checklist Conformite Loi 2008-12 - DataProtect SN</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Segoe UI', Arial, sans-serif; color: #1a1a2e; background: #fff; }
  .doc-header { background: linear-gradient(135deg, #1a5c34, #1a4f8a); color: #fff; padding: 2.5rem; }
  .doc-header h1 { font-size: 1.6rem; font-weight: 800; margin-bottom: .5rem; }
  .doc-header p { opacity: .8; font-size: .9rem; }
  .doc-meta { display: flex; gap: 1.5rem; margin-top: 1rem; font-size: .8rem; opacity: .75; }
  .doc-body { max-width: 900px; margin: 0 auto; padding: 2.5rem; }
  h2 { color: #1a5c34; font-size: 1.1rem; margin: 2rem 0 .75rem; padding-bottom: .4rem; border-bottom: 2px solid #eaf5ef; }
  h3 { color: #2c3e50; font-size: .95rem; margin: 1.25rem 0 .5rem; }
  p { line-height: 1.8; color: #374151; font-size: .92rem; margin-bottom: .75rem; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; margin: 1rem 0; }
  th { background: #1a5c34; color: #fff; padding: .65rem .85rem; text-align: left; }
  td { padding: .6rem .85rem; border-bottom: 1px solid #e5e7eb; }
  tr:nth-child(even) td { background: #f8fffe; }
  .check-item { display: flex; align-items: flex-start; gap: .75rem; padding: .65rem 0; border-bottom: 1px solid #f0f0f0; }
  .check-item input { margin-top: 3px; accent-color: #1a5c34; flex-shrink: 0; }
  .highlight { background: #eaf5ef; border-left: 4px solid #1a5c34; border-radius: 0 8px 8px 0; padding: .85rem 1.1rem; margin: 1rem 0; font-size: .88rem; }
  .warning { background: #fdf6e3; border-left: 4px solid #b8860b; border-radius: 0 8px 8px 0; padding: .85rem 1.1rem; margin: 1rem 0; font-size: .88rem; }
  .footer-doc { background: #f8f7f4; border-top: 1px solid #e5e7eb; padding: 1.5rem 2.5rem; font-size: .8rem; color: #6b7280; text-align: center; }
  @media print { .no-print { display: none; } }
  .btn-print { background: #1a5c34; color: #fff; border: none; padding: .6rem 1.2rem; border-radius: 6px; cursor: pointer; font-size: .85rem; margin-top: 1rem; }
</style>
</head>
<body>
<div class="doc-header">
  <h1>Checklist Conformite &mdash; Loi n&deg;2008-12 du Senegal</h1>
  <p>30 points de controle pour verifier la conformite de votre organisation a la loi senegalaise sur la protection des donnees</p>
  <div class="doc-meta">
    <span>Organisation : ___________________</span>
    <span>Auditeur : ___________________</span>
    <span>Date d'audit : ___________________</span>
  </div>
  <button class="btn-print no-print" onclick="window.print()">Imprimer / Sauvegarder PDF</button>
</div>
<div class="doc-body">
  <div class="highlight"><strong>Mode d'emploi :</strong> Cochez chaque point accompli. Un score inferieur a 20/30 indique des risques significatifs. Contactez un DPO pour un accompagnement personnalise.</div>

  <h2>A. Formalites prealables (Art. 18-22 Loi 2008-12)</h2>
  <div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Toutes les activites de traitement ont fait l'objet d'une declaration prealable a la CDP</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les traitements de donnees sensibles (sante, biometrie, opinions politiques/religieuses) ont obtenu une autorisation prealable CDP</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les transferts de donnees vers des pays tiers ont ete notifies a la CDP avec justification des garanties</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un responsable du traitement est clairement designe et identifiable</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Le registre des traitements est tenu a jour et disponible pour controle CDP sous 48h</span></div>

  <h2>B. Information des personnes (Art. 37-40)</h2>
  <div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Une politique de confidentialite est publiee, accessible et redigee en francais (ou wolof pour les publics locaux)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Chaque formulaire de collecte indique : identite du responsable, finalite, droits des personnes, duree de conservation</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Le consentement est recueilli de facon libre, specifique et documentee (horodatage, preuve)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les cases pre-cochees et consentements groupes ont ete supprimes de tous les formulaires</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un mecanisme de retrait du consentement est aussi simple que son obtention (bouton desabonnement, etc.)</span></div>

  <h2>C. Droits des personnes (Art. 47-52)</h2>
  <div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un processus de traitement des demandes d'acces est en place (reponse dans 30 jours maximum)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les demandes de rectification sont traitees dans les delais reglementaires</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les demandes de suppression et d'opposition sont honorees sauf exceptions prevues par la loi</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un registre des demandes d'exercice de droits est tenu (date, demande, reponse apportee)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">L'organisation a designe un point de contact pour les droits des personnes (email dedie ou formulaire)</span></div>

  <h2>D. Securite des donnees (Art. 53-55)</h2>
  <div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les communications sont chiffrees (HTTPS obligatoire, TLS 1.2 minimum)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les mots de passe sont stockes sous forme hachee (SHA-256, bcrypt ou argon2 - jamais en clair)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les acces aux donnees personnelles sont limites au principe du moindre privilege</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Une procedure de gestion des violations de donnees est documentee (notification CDP sous 72h Art. 33 RGPD)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les sous-traitants traitant des donnees personnelles sont encadres par des contrats incluant des clauses de protection</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Des sauvegardes regulieres des donnees sont effectuees et testees (minimum hebdomadaire)</span></div>

  <h2>E. Durees de conservation (Art. 29-31)</h2>
  <div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Des durees de conservation sont definies et documentees pour chaque categorie de donnees</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un processus d'effacement ou d'anonymisation automatique est mis en place a l'issue des delais</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les archives intermediaires sont separees des donnees en traitement actif</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">La politique de conservation est connue et appliquee par toute l'equipe</span></div>

  <h2>F. Gouvernance et culture data (Art. 18 et suivants)</h2>
  <div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Le personnel est forme a la protection des donnees au moins une fois par an</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Une personne referente (DPO interne ou externe) est identifiee et joignable</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un plan de mise en conformite avec echeancier est etabli et suivi</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les nouveaux projets impliquant des donnees font l'objet d'une revue privacy before launch</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un bilan annuel de conformite est realise et documente</span></div>

  <h2>Synthese de l'audit</h2>
  <table>
    <tr><th>Section</th><th>Points max</th><th>Points obtenus</th><th>Score (%)</th></tr>
    <tr><td>A. Formalites prealables</td><td>5</td><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>B. Information des personnes</td><td>5</td><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>C. Droits des personnes</td><td>5</td><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>D. Securite</td><td>6</td><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>E. Durees de conservation</td><td>4</td><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td>F. Gouvernance</td><td>5</td><td>&nbsp;</td><td>&nbsp;</td></tr>
    <tr><td><strong>TOTAL</strong></td><td><strong>30</strong></td><td>&nbsp;</td><td>&nbsp;</td></tr>
  </table>
  <div class="highlight">Score 25-30 : Conformite satisfaisante | 20-24 : Risques moderes | 15-19 : Risques significatifs | &lt;15 : Risques eleves &mdash; action immediate requise</div>
</div>
<div class="footer-doc">DataProtect Senegal &mdash; Henry Pierre Diouf, DPO M2 &mdash; henrypierrediouf@gmail.com &mdash; Pour accompagnement DPO : +33 7 53 65 61 31</div>
</body></html>""",
    "checklist-rgpd-entreprises-sn": """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Checklist RGPD - Entreprises Senegalaises - DataProtect SN</title><style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',Arial,sans-serif;color:#1a1a2e;background:#fff}
  .doc-header{background:linear-gradient(135deg,#1a5c34,#1a4f8a);color:#fff;padding:2.5rem}
  .doc-header h1{font-size:1.6rem;font-weight:800;margin-bottom:.5rem}
  .doc-header p{opacity:.8;font-size:.9rem}
  .doc-meta{display:flex;gap:1.5rem;margin-top:1rem;font-size:.8rem;opacity:.75}
  .doc-body{max-width:900px;margin:0 auto;padding:2.5rem}
  h2{color:#1a5c34;font-size:1.1rem;margin:2rem 0 .75rem;padding-bottom:.4rem;border-bottom:2px solid #eaf5ef}
  h3{color:#2c3e50;font-size:.95rem;margin:1.25rem 0 .5rem}
  p{line-height:1.8;color:#374151;font-size:.92rem;margin-bottom:.75rem}
  table{width:100%;border-collapse:collapse;font-size:.85rem;margin:1rem 0}
  th{background:#1a5c34;color:#fff;padding:.65rem .85rem;text-align:left}
  td{padding:.6rem .85rem;border-bottom:1px solid #e5e7eb}
  tr:nth-child(even) td{background:#f8fffe}
  .check-item{display:flex;align-items:flex-start;gap:.75rem;padding:.65rem 0;border-bottom:1px solid #f0f0f0}
  .check-item input{margin-top:3px;accent-color:#1a5c34;flex-shrink:0}
  .highlight{background:#eaf5ef;border-left:4px solid #1a5c34;border-radius:0 8px 8px 0;padding:.85rem 1.1rem;margin:1rem 0;font-size:.88rem}
  .warning{background:#fdf6e3;border-left:4px solid #b8860b;border-radius:0 8px 8px 0;padding:.85rem 1.1rem;margin:1rem 0;font-size:.88rem}
  .danger{background:#fdecea;border-left:4px solid #c0392b;border-radius:0 8px 8px 0;padding:.85rem 1.1rem;margin:1rem 0;font-size:.88rem}
  .footer-doc{background:#f8f7f4;border-top:1px solid #e5e7eb;padding:1.5rem 2.5rem;font-size:.8rem;color:#6b7280;text-align:center;margin-top:3rem}
  .btn-print{background:#1a5c34;color:#fff;border:none;padding:.6rem 1.2rem;border-radius:6px;cursor:pointer;font-size:.85rem;margin-top:1rem}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin:.75rem 0}
  .card-sm{background:#f8fffe;border:1px solid #d1fae5;border-radius:8px;padding:.85rem}
  @media print{.no-print{display:none}}
</style></head>
<body>
<div class="doc-header">
  <h1>Checklist RGPD &mdash; Entreprises Senegalaises exportant vers l'UE</h1>
  <p>Guide de conformite RGPD pour les organisations traitant des donnees de residents europeens</p>
  <div class="doc-meta"><span>Organisation : ___________________</span><span>Date : ___________________</span></div>
  <button class="btn-print no-print" onclick="window.print()">Imprimer / PDF</button>
</div>
<div class="doc-body">
<div class="danger"><strong>Portee extraterritoriale (Art. 3 RGPD) :</strong> Le RGPD s'applique a toute organisation dans le monde qui offre des biens/services a des residents de l'UE ou surveille leur comportement. Etre au Senegal ne vous exempte pas.</div>

<h2>A. Etablissement de la base legale (Art. 6-7)</h2>
<div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Une base legale valide est identifiee pour chaque traitement : consentement, contrat, obligation legale, interet vital, mission publique, interet legitime</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Le consentement est granulaire (1 case = 1 finalite), retractable et documente avec horodatage</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les cases pre-cochees, les consentements groupes et les cases 'j'accepte les CGU et la politique' ont ete supprimes</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un mecanisme de retrait du consentement est aussi facile a utiliser que son obtention (bouton visible, 1 clic)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">La base 'interet legitime' a fait l'objet d'un test de mise en balance (LIA - Legitimate Interest Assessment)</span></div>

<h2>B. Droits des personnes (Art. 15-22) - specificites RGPD</h2>
<div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Droit d'acces (Art. 15) : reponse dans 1 mois maximum (extensible a 3 mois si requete complexe)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Droit a l'effacement / droit a l'oubli (Art. 17) : procedure documentee, effacement des sauvegardes inclus</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Droit a la portabilite (Art. 20) : donnees fournissables en format structuree (CSV, JSON, XML) &mdash; absent de la Loi 2008-12</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Droit d'opposition (Art. 21) : notamment pour la prospection commerciale et le profilage</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Droit a la limitation (Art. 18) : possibilite de geler un traitement en cas de contestation</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Droit de ne pas faire l'objet d'une decision automatisee uniquement (Art. 22) : intervention humaine disponible sur demande</span></div>

<h2>C. Transferts internationaux Senegal-UE (Art. 44-49)</h2>
<div class="warning">Le Senegal n'est pas reconnu comme pays adequat par la Commission europeenne. Chaque transfert doit etre encadre.</div>
<div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Des Clauses Contractuelles Types (CCT) approuvees par la Commission europeenne (juin 2021) sont en place avec chaque sous-traitant europeen</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un registre des transferts internationaux est tenu (destinataire, pays, mecanisme de garantie)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les sous-traitants hors UE traitant des donnees europeennes ont signe un Accord de Traitement des Donnees (DPA)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Une analyse d'impact sur les transferts (TIA) a ete realisee pour les pays sans adequation</span></div>

<h2>D. Privacy by Design & Securite (Art. 25 & 32)</h2>
<div class="check-item"><input type="checkbox"><span style="font-size:.88rem">La protection des donnees est integree des la conception des nouveaux produits (Privacy by Design)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Par defaut, seules les donnees strictement necessaires sont collectees (Privacy by Default)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les donnees sont pseudonymisees ou anonymisees des que possible</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Les mesures de securite sont proportionnees au risque : chiffrement, controle acces, journaux, tests de penetration</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un plan de reprise apres incident (DREP) couvre les donnees personnelles</span></div>

<h2>E. Analyse d'Impact (AIPD) - Art. 35</h2>
<div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Une AIPD a ete realisee pour les traitements a risque eleve (biometrie, profilage, surveillance, sante, mineurs)</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">L'AIPD documente : description du traitement, necessite, risques identifies, mesures d'attenuation, risque residuel</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">La CNIL (ou autorite competente) a ete consultee si le risque residuel reste eleve apres mesures</span></div>

<h2>F. Violations de donnees (Art. 33-34)</h2>
<div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Une procedure de notification a l'autorite de controle dans 72h est documentee et testee</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">Un registre des violations est tenu avec : nature, donnees concernees, nombre de personnes, mesures prises</span></div><div class="check-item"><input type="checkbox"><span style="font-size:.88rem">La procedure de notification aux personnes concernees (si risque eleve) est documentee</span></div>

<h2>Grille d'evaluation globale</h2>
<table>
  <tr><th>Section</th><th>Points</th><th>Score</th><th>Priorite</th></tr>
  <tr><td>A. Base legale</td><td>5</td><td>&nbsp;</td><td>CRITIQUE</td></tr>
  <tr><td>B. Droits des personnes</td><td>6</td><td>&nbsp;</td><td>CRITIQUE</td></tr>
  <tr><td>C. Transferts internationaux</td><td>4</td><td>&nbsp;</td><td>TRES IMPORTANT</td></tr>
  <tr><td>D. Privacy by Design</td><td>5</td><td>&nbsp;</td><td>IMPORTANT</td></tr>
  <tr><td>E. AIPD</td><td>3</td><td>&nbsp;</td><td>SELON TRAITEMENTS</td></tr>
  <tr><td>F. Violations</td><td>3</td><td>&nbsp;</td><td>IMPORTANT</td></tr>
  <tr><td><strong>TOTAL</strong></td><td><strong>26</strong></td><td>&nbsp;</td><td>&nbsp;</td></tr>
</table>
</div>
<div class="footer-doc">DataProtect Senegal &mdash; Henry Pierre Diouf, DPO M2 &mdash; henrypierrediouf@gmail.com &mdash; +33 7 53 65 61 31</div>
</body></html>""",
    "modele-politique-confidentialite": """<!DOCTYPE html>
<html lang="fr"><head><meta charset="UTF-8"><title>Modele Politique Confidentialite - DataProtect SN</title><style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',Arial,sans-serif;color:#1a1a2e;background:#fff}
  .doc-header{background:linear-gradient(135deg,#1a5c34,#1a4f8a);color:#fff;padding:2.5rem}
  .doc-header h1{font-size:1.6rem;font-weight:800;margin-bottom:.5rem}
  .doc-header p{opacity:.8;font-size:.9rem}
  .doc-meta{display:flex;gap:1.5rem;margin-top:1rem;font-size:.8rem;opacity:.75}
  .doc-body{max-width:900px;margin:0 auto;padding:2.5rem}
  h2{color:#1a5c34;font-size:1.1rem;margin:2rem 0 .75rem;padding-bottom:.4rem;border-bottom:2px solid #eaf5ef}
  h3{color:#2c3e50;font-size:.95rem;margin:1.25rem 0 .5rem}
  p{line-height:1.8;color:#374151;font-size:.92rem;margin-bottom:.75rem}
  table{width:100%;border-collapse:collapse;font-size:.85rem;margin:1rem 0}
  th{background:#1a5c34;color:#fff;padding:.65rem .85rem;text-align:left}
  td{padding:.6rem .85rem;border-bottom:1px solid #e5e7eb}
  tr:nth-child(even) td{background:#f8fffe}
  .check-item{display:flex;align-items:flex-start;gap:.75rem;padding:.65rem 0;border-bottom:1px solid #f0f0f0}
  .check-item input{margin-top:3px;accent-color:#1a5c34;flex-shrink:0}
  .highlight{background:#eaf5ef;border-left:4px solid #1a5c34;border-radius:0 8px 8px 0;padding:.85rem 1.1rem;margin:1rem 0;font-size:.88rem}
  .warning{background:#fdf6e3;border-left:4px solid #b8860b;border-radius:0 8px 8px 0;padding:.85rem 1.1rem;margin:1rem 0;font-size:.88rem}
  .danger{background:#fdecea;border-left:4px solid #c0392b;border-radius:0 8px 8px 0;padding:.85rem 1.1rem;margin:1rem 0;font-size:.88rem}
  .footer-doc{background:#f8f7f4;border-top:1px solid #e5e7eb;padding:1.5rem 2.5rem;font-size:.8rem;color:#6b7280;text-align:center;margin-top:3rem}
  .btn-print{background:#1a5c34;color:#fff;border:none;padding:.6rem 1.2rem;border-radius:6px;cursor:pointer;font-size:.85rem;margin-top:1rem}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin:.75rem 0}
  .card-sm{background:#f8fffe;border:1px solid #d1fae5;border-radius:8px;padding:.85rem}
  @media print{.no-print{display:none}}
</style></head>
<body>
<div class="doc-header">
  <h1>Modele de Politique de Confidentialite</h1>
  <p>Conforme a la Loi 2008-12 (Senegal) et au RGPD (UE) &mdash; A personnaliser avec vos informations</p>
  <div class="doc-meta"><span>Instructions : Remplacez tout texte entre [crochets] par vos informations reelles</span></div>
  <button class="btn-print no-print" onclick="window.print()">Imprimer / PDF</button>
</div>
<div class="doc-body">
<div class="highlight">Ce modele est fourni a titre indicatif. Faites-le valider par un DPO qualifie avant publication. Contact : henrypierrediouf@gmail.com</div>

<h2 style="text-align:center;font-size:1.4rem;color:#1a1a2e">POLITIQUE DE PROTECTION DES DONNEES PERSONNELLES</h2>
<p style="text-align:center;color:#6b7280"><em>[NOM_ORGANISATION] &mdash; Version [X.X] &mdash; Derniere mise a jour : [DATE]</em></p>

<h2>1. Identite et coordonnees du responsable du traitement</h2>
<p>[NOM_ORGANISATION], [FORME_JURIDIQUE] dont le siege social est situe a [ADRESSE], immatriculee sous le numero [NUMERO], est responsable du traitement de vos donnees personnelles collectees sur [NOM_DU_SITE_OU_SERVICE].</p>
<p><strong>Contact DPO / Referent RGPD :</strong> [NOM_DPO] &mdash; [EMAIL_DPO] &mdash; [TEL_DPO]</p>

<h2>2. Donnees collectees et finalites</h2>
<p>Dans le cadre de nos activites, nous collectons les categories de donnees suivantes :</p>
<table>
  <tr><th>Donnees</th><th>Finalite</th><th>Base legale</th><th>Conservation</th></tr>
  <tr><td>[Ex: Nom, email, telephone]</td><td>[Ex: Gestion des demandes clients]</td><td>[Ex: Consentement / Contrat]</td><td>[Ex: 3 ans]</td></tr>
  <tr><td>[...]</td><td>[...]</td><td>[...]</td><td>[...]</td></tr>
</table>
<p>Nous appliquons le principe de minimisation : seules les donnees strictement necessaires aux finalites declarees sont collectees (Art. 5.1.c RGPD / Art. 18 Loi 2008-12).</p>

<h2>3. Destinataires de vos donnees</h2>
<p>Vos donnees sont traitees par [NOM_ORGANISATION] et peuvent etre partagees avec :</p>
<p>&mdash; [NOM_SOUS_TRAITANT_1] pour [FINALITE_1] &mdash; [PAYS] &mdash; [LIEN_POLITIQUE_CONFIDENTIALITE]<br>
&mdash; [NOM_SOUS_TRAITANT_2] pour [FINALITE_2] &mdash; [PAYS]<br>
Vos donnees ne sont jamais vendues ni cedees a des fins commerciales.</p>

<h2>4. Transferts internationaux</h2>
<p>[Si applicable :] Certaines de vos donnees peuvent etre transferees vers [PAYS]. Ces transferts sont encadres par [Clauses Contractuelles Types / Decision d'adequation / Regles d'entreprise contraignantes] conformement a l'Art. 46 RGPD et l'Art. 47 Loi 2008-12.</p>

<h2>5. Vos droits</h2>
<p>Conformement a l'Art. 48 de la Loi 2008-12 et aux Art. 15-22 du RGPD, vous disposez des droits suivants :</p>
<div class="grid2">
  <div class="card-sm"><strong>Droit d'acces</strong><br><small>Obtenir confirmation et copie de vos donnees</small></div>
  <div class="card-sm"><strong>Droit de rectification</strong><br><small>Corriger des donnees inexactes ou incompletes</small></div>
  <div class="card-sm"><strong>Droit a l'effacement</strong><br><small>Demander la suppression sous conditions</small></div>
  <div class="card-sm"><strong>Droit d'opposition</strong><br><small>S'opposer notamment a la prospection</small></div>
  <div class="card-sm"><strong>Droit a la portabilite</strong><br><small>Recevoir vos donnees en format structure (UE)</small></div>
  <div class="card-sm"><strong>Retrait du consentement</strong><br><small>A tout moment, sans effet retroactif</small></div>
</div>
<p>Pour exercer vos droits : [EMAIL_EXERCICE_DROITS] &mdash; Reponse sous 30 jours (Art. 12 RGPD).</p>

<h2>6. Securite des donnees</h2>
<p>Nous mettons en oeuvre les mesures de securite suivantes : [lister : chiffrement HTTPS, hachage mots de passe, controle d'acces, journaux, sauvegardes, etc.]</p>

<h2>7. Cookies</h2>
<p>Notre site utilise des cookies. [Description des types de cookies.] Vous pouvez gerer vos preferences via [outil de gestion]. Pour plus d'informations, consultez notre politique des cookies.</p>

<h2>8. Violations de donnees</h2>
<p>En cas de violation susceptible d'affecter vos droits, nous notifierons la CDP (cdp.sn) dans les 72h et vous informerons sans delai injustifie si le risque est eleve (Art. 33-34 RGPD).</p>

<h2>9. Autorites de controle</h2>
<p>Vous pouvez introduire une reclamation aupres de la <strong>CDP Senegal</strong> (cdp.sn) ou de la <strong>CNIL</strong> (cnil.fr) pour les residents de l'UE.</p>

<h2>10. Modifications</h2>
<p>Cette politique peut etre mise a jour. La date en haut du document reflete la version en vigueur. Toute modification substantielle sera communiquee par [email / banniere sur le site].</p>

<div class="highlight"><strong>Validation recommandee :</strong> Ce modele doit etre adapte a votre situation specifique et valide par un DPO. Contact : henrypierrediouf@gmail.com &mdash; +33 7 53 65 61 31</div>
</div>
<div class="footer-doc">DataProtect Senegal &mdash; Henry Pierre Diouf, DPO M2 &mdash; Modele fourni a titre indicatif, a adapter et valider</div>
</body></html>""",
}

@app.get("/docs/{filename}")
async def serve_doc(filename: str):
    import re as _re
    name = filename.replace(".html", "")
    if name not in DOCS:
        raise HTTPException(status_code=404, detail="Document introuvable")
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=DOCS[name])

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
