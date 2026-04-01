# DataProtect Sénégal — Guide d'installation locale

**Par Henry Pierre Diouf, DPO M2 — La Plateforme Numérique, Marseille**

---

## Structure du projet

```
dataprotect-sn/
├── index.html          ← Site web principal
├── admin.html          ← Interface d'administration
├── server.py           ← Serveur backend (FastAPI)
├── requirements.txt    ← Dépendances Python
├── DEMARRER.bat        ← Lancer le site (Windows, 1 clic)
├── netlify.toml        ← Configuration Netlify (déploiement)
└── database.db         ← Base SQLite (créée automatiquement)
```

---

## Installation rapide (Windows)

### Étape 1 — Installer Python
1. Va sur https://www.python.org/downloads/
2. Télécharge Python 3.11 ou plus récent
3. **Important** : coche "Add Python to PATH" lors de l'installation
4. Clique "Install Now"

### Étape 2 — Lancer le site
1. Place tous les fichiers dans un dossier (ex: `C:\dataprotect-sn`)
2. Double-clique sur **DEMARRER.bat**
3. Le navigateur s'ouvre automatiquement sur http://localhost:8000

**C'est tout !**

---

## Accès

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Site web public |
| http://localhost:8000/admin.html | Panel administrateur |
| http://localhost:8000/docs | Documentation API (Swagger) |

**Mot de passe admin** : `dataprotect2025`
> ⚠️ Change ce mot de passe dans `server.py` ligne 20 avant de mettre en production !

---

## Base de données

Le fichier `database.db` est créé automatiquement au premier lancement.

### Tables créées

| Table | Contenu |
|-------|---------|
| `contacts` | Messages du formulaire de contact |
| `abonnes` | Inscrits à la newsletter |
| `articles` | Articles de veille juridique |
| `utilisateurs` | Membres de l'espace privé |

### Consulter la base de données
Télécharge **DB Browser for SQLite** (gratuit) :
https://sqlitebrowser.org/dl/

---

## API disponibles

### Publiques (site web)
- `GET /api/articles` — Liste des articles publiés
- `POST /api/contact` — Envoyer un message
- `POST /api/newsletter` — S'abonner à la newsletter
- `POST /api/inscription` — Créer un compte membre
- `POST /api/connexion` — Se connecter

### Admin (protégées par mot de passe)
- `GET /api/admin/contacts` — Voir les messages
- `GET /api/admin/abonnes` — Voir les abonnés
- `GET /api/admin/stats` — Statistiques globales
- `POST /api/admin/articles` — Créer un article
- `DELETE /api/admin/articles/{id}` — Supprimer un article

---

## Connecter le formulaire au backend

Dans `index.html`, le formulaire de contact appelle déjà `/api/contact`.
Pour activer la connexion backend, remplace dans le JS :

```javascript
// Avant (simulation)
data-contact-btn="1"

// Après (vrai backend)
// Le formulaire envoie automatiquement vers http://localhost:8000/api/contact
```

---

## Déploiement en ligne

Pour mettre en production sur un serveur :

1. **Hébergeur recommandé** : Railway, Render, ou un VPS OVH
2. Lance avec : `uvicorn server:app --host 0.0.0.0 --port 8000`
3. Utilise `nginx` comme reverse proxy
4. Change `ADMIN_PASSWORD` dans `server.py`

---

## Dépannage

**"Python n'est pas reconnu"**
→ Réinstalle Python en cochant "Add Python to PATH"

**"Port 8000 déjà utilisé"**
→ Dans `server.py`, change `port=8000` par `port=8001`

**"Module not found"**
→ Lance dans le terminal : `pip install -r requirements.txt`

---

*DataProtect Sénégal © 2025 — Henry Pierre Diouf*
*henrypierrediouf@gmail.com | +33 7 53 65 61 31*
