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
