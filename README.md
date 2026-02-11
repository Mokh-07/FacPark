# 🅿️ FacPark — Système de Parking Universitaire Intelligent

> Gestion intelligente de parking universitaire avec reconnaissance de plaques par IA et assistant virtuel conversationnel.

![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?logo=fastapi)
![React](https://img.shields.io/badge/React-18+-61dafb?logo=react)
![YOLOv11](https://img.shields.io/badge/YOLO-v11-purple)
![License](https://img.shields.io/badge/License-Academic-orange)

---

## 🌟 Fonctionnalités

### 🧠 Intelligence Artificielle
- **Détection de plaques** — YOLOv11 (temps réel, >95% précision)
- **OCR (LPRNet)** — Lecture de plaques tunisiennes (arabe + chiffres)
- **Assistant RAG** — Chatbot hybride FAISS + BM25 pour le règlement
- **Moteur de décision** — Système expert déterministe (ALLOW/DENY)

### 💻 Interface Utilisateur
- **Dashboard Étudiant** — Véhicules, abonnements, chatbot
- **Dashboard Admin** — Statistiques, logs, supervision
- **Simulation Barrière** — Upload photo → détection → décision d'accès

### 🔒 Sécurité
- Détection d'injections de prompt (regex + score de risque)
- RBAC strict (rôles Admin/Étudiant)
- JWT avec rotation (access 60min + refresh 7j)
- Anti-hallucination RAG

---

## 🛠️ Stack Technique

| Couche | Technologies |
|--------|-------------|
| **Backend** | FastAPI, SQLAlchemy, PyTorch, LangChain |
| **Frontend** | React 18, Vite, TailwindCSS, Recharts |
| **Base de données** | MySQL (XAMPP) |
| **Modèles IA** | YOLOv11 (détection), LPRNet (OCR) |
| **LLM** | Gemini / Groq (fallback) |
| **RAG** | FAISS + BM25 + RRF |

---

## 📁 Structure du Projet

```
FacPark/
├── backend/                    # API FastAPI
│   ├── api/                    # Endpoints REST
│   │   ├── auth.py             #   Authentification (JWT)
│   │   ├── chat.py             #   Chatbot / Agent
│   │   ├── vision.py           #   Détection + OCR
│   │   └── admin.py            #   Administration
│   ├── core/                   # Logique métier
│   │   ├── agent.py            #   Agent LLM + Tools
│   │   ├── decision.py         #   Moteur de décision
│   │   ├── rag.py              #   Pipeline RAG
│   │   ├── tools.py            #   Outils étudiant
│   │   └── tools_admin.py      #   Outils admin
│   ├── db/                     # Base de données
│   │   ├── models.py           #   Modèles SQLAlchemy
│   │   └── session.py          #   Session DB
│   ├── vision/                 # Modèles de vision
│   │   ├── detector.py         #   YOLO detector
│   │   └── ocr.py              #   LPRNet OCR
│   ├── eval/                   # Évaluation RAG
│   ├── scripts/                # Scripts utilitaires
│   │   ├── init_db.py          #   Initialisation DB
│   │   ├── ingest_docs.py      #   Ingestion documents RAG
│   │   ├── populate_slots.py   #   Créer les places
│   │   └── activate_subscription.py
│   ├── config.py               # Configuration centralisée
│   ├── main.py                 # Point d'entrée FastAPI
│   └── requirements.txt        # Dépendances Python
├── frontend/                   # Application React
│   ├── src/
│   │   ├── components/         # Composants UI
│   │   ├── pages/              # Pages (Login, Dashboards)
│   │   ├── context/            # AuthContext
│   │   └── services/           # API client
│   ├── package.json
│   └── vite.config.js
├── data/
│   ├── docs/                   # Documents RAG (règlement)
│   └── sql/                    # Scripts SQL
│       ├── 01_schema.sql       #   Schéma de la BD
│       ├── 02_seed.sql         #   Données de test
│       └── 03_indexes.sql      #   Index de performance
├── models/                     # Modèles IA (non versionnés)
│   ├── *.pt                    #   YOLO weights
│   ├── *.pth                   #   LPRNet weights
│   └── vocabulary.json         #   Vocabulaire OCR
├── docs/                       # Documentation technique
├── .env.example                # Template des variables d'env
├── start_project.bat           # Script de lancement Windows
└── README.md
```

---

## 🚀 Installation

### Prérequis
- **Python** 3.9+
- **Node.js** 18+
- **MySQL** (via XAMPP)
- **CUDA** (recommandé pour la vision)

### 1. Cloner le dépôt
```bash
git clone https://github.com/<votre-user>/FacPark.git
cd FacPark
```

### 2. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt
```

### 3. Variables d'environnement
```bash
copy .env.example .env
# Éditez .env et remplissez vos clés API (GEMINI_API_KEY et/ou GROQ_API_KEY)
```

### 4. Base de données MySQL
1. Démarrez MySQL dans XAMPP
2. Créez la base :
   ```sql
   CREATE DATABASE facpark CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```
3. Exécutez les scripts dans l'ordre :
   - `data/sql/01_schema.sql`
   - `data/sql/02_seed.sql`
   - `data/sql/03_indexes.sql`

### 5. Modèles IA
Téléchargez les modèles et placez-les dans `models/` :
- `smartalpr_hybrid_640_yolo11l_v2_best.pt` — YOLO detection
- `SmartALPR_LPRNet_v10_seed456_best.pth` — LPRNet OCR
- `vocabulary.json` — Vocabulaire de caractères

### 6. Ingestion RAG
```bash
# Depuis la racine du projet, avec le venv activé
python -m backend.scripts.ingest_docs
```

### 7. Frontend
```bash
cd frontend
npm install
```

### 8. Lancement
**Option A — Script automatique (Windows) :**
```bat
start_project.bat
```

**Option B — Manuel :**
```bash
# Terminal 1 (Backend)
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 (Frontend)
cd frontend && npm run dev
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Frontend | http://localhost:5173 |
| API Docs | http://localhost:8000/docs |

---

## 🧪 Comptes de Test

| Rôle | Email | Mot de passe |
|------|-------|--------------|
| **Admin** | `admin@fac.tn` | `admin123` |
| **Étudiant** | `ahmed.benali@etudiant.fac.tn` | `student123` |
| **Étudiant (suspendu)** | `leila.bouazizi@etudiant.fac.tn` | `student123` |

---

## 📊 Codes de Décision

| Code | Signification |
|------|---------------|
| `REF-00` | ✅ Accès autorisé |
| `REF-01` | ❌ Plaque non détectée |
| `REF-02` | ❌ Plaque non enregistrée |
| `REF-03` | ❌ Pas d'abonnement actif |
| `REF-04` | ❌ Compte suspendu |
| `REF-05` | ❌ Abonnement expiré |
| `REF-06` | ❌ Pas de place assignée |
| `REF-07` | ❌ Hors horaires d'ouverture |

---

## 📄 License

Projet académique — Université de Tunis 2025/2026
