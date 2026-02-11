# 🧠 EXPLICATION TECHNIQUE - RAG HYBRIDE & ARCHITECTURE IA

**Projet** : FacPark - Système de parking intelligent  
**Perspective** : Expert en Intelligence Artificielle  
**Date** : 2026-01-21

---

## 📑 TABLE DES MATIÈRES

1. [Vue d'ensemble architecture IA](#-vue-densemble-architecture-ia)
2. [RAG Hybride - Explication approfondie](#-rag-hybride---explication-approfondie)
3. [Pipeline Vision (YOLO + OCR)](#-pipeline-vision-yolo--ocr)
4. [Agent LLM avec outils](#-agent-llm-avec-outils)
5. [Flux de données complet](#-flux-de-données-complet)
6. [Optimisations et bonnes pratiques](#-optimisations-et-bonnes-pratiques)

---

## 🏗️ VUE D'ENSEMBLE ARCHITECTURE IA

### Composants IA du système

```
┌─────────────────────────────────────────────────────────────┐
│                     FRONTEND (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐     │
│  │ ChatBot  │  │  Image   │  │   PlateChecker       │     │
│  │Interface │  │  Upload  │  │   (Test barrière)    │     │
│  └────┬─────┘  └────┬─────┘  └──────────┬───────────┘     │
└───────┼─────────────┼────────────────────┼─────────────────┘
        │             │                    │
        │ WebSocket   │ HTTP POST          │ HTTP POST
        │             │                    │
┌───────▼─────────────▼────────────────────▼─────────────────┐
│                  BACKEND FASTAPI                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              AGENT ORCHESTRATOR                      │  │
│  │    (backend/core/agent.py)                          │  │
│  │  ┌───────────┐  ┌──────────┐  ┌─────────────┐     │  │
│  │  │ Intent    │  │ Injection│  │   Tool      │     │  │
│  │  │ Detection │  │ Detection│  │  Execution  │     │  │
│  │  └─────┬─────┘  └────┬─────┘  └──────┬──────┘     │  │
│  └────────┼─────────────┼───────────────┼─────────────┘  │
│           │             │               │                 │
│  ┌────────▼─────────────▼───────────────▼──────────────┐  │
│  │           LLM ORCHESTRATION                         │  │
│  │  ┌─────────────┐         ┌──────────────┐          │  │
│  │  │   Gemini    │ Fallback│    Groq      │          │  │
│  │  │ 2.0 Flash   │◄────────┤  llama-3.3   │          │  │
│  │  └─────────────┘         └──────────────┘          │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                3 SYSTÈMES IA                         │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │  1️⃣ RAG HYBRIDE (backend/core/rag.py)              │  │
│  │     ┌────────────┐  ┌────────┐  ┌──────────┐       │  │
│  │     │   FAISS    │  │  BM25  │  │   RRF    │       │  │
│  │     │  (Dense)   │  │(Sparse)│  │ (Fusion) │       │  │
│  │     └─────┬──────┘  └───┬────┘  └────┬─────┘       │  │
│  │           └─────────────┴────────────┘              │  │
│  │                      │                              │  │
│  │              Embeddings (all-MiniLM-L6-v2)         │  │
│  │                                                     │  │
│  │  2️⃣ VISION (backend/vision/)                      │  │
│  │     ┌──────────────┐      ┌──────────────┐        │  │
│  │     │   YOLOv11    │──────►│   LPRNet     │        │  │
│  │     │  (Détection) │      │     (OCR)     │        │  │
│  │     └──────────────┘      └──────────────┘        │  │
│  │                                                     │  │
│  │  3️⃣ DECISION ENGINE (backend/core/decision.py)   │  │
│  │     ┌──────────────────────────────────┐          │  │
│  │     │  Règles déterministes            │          │  │
│  │     │  (NO LLM - Pure Logic)           │          │  │
│  │     │  ALLOW / DENY + REF-XX           │          │  │
│  │     └──────────────────────────────────┘          │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              TOOLS (13 Admin + 6 Student)            │  │
│  │  backend/core/tools.py + tools_admin.py             │  │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐      │  │
│  │  │ DB     │ │  RBAC  │ │ Audit  │ │ Security│      │  │
│  │  │ Access │ │ Check  │ │  Logs  │ │  Events │      │  │
│  │  └────────┘ └────────┘ └────────┘ └────────┘      │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  BASE DE DONNÉES                     │  │
│  │  MySQL + SQLAlchemy + Triggers + Indexes            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔍 RAG HYBRIDE - EXPLICATION APPROFONDIE

### Qu'est-ce que le RAG ?

**RAG** = **R**etrieval-**A**ugmented **G**eneration

**Principe** : Enrichir les réponses du LLM avec des **connaissances externes** récupérées dynamiquement depuis une base documentaire.

**Problème résolu** :
- ❌ Les LLM ont des connaissances **figées** (date de coupure)
- ❌ Hallucinations fréquentes sur des domaines spécifiques
- ❌ Pas de traçabilité des sources

**Solution RAG** :
- ✅ Récupération de **documents pertinents**
- ✅ Injection comme **contexte** dans le prompt
- ✅ LLM répond **en citant les sources**

---

### Architecture Hybride FAISS + BM25

Le projet utilise un **RAG hybride** combinant :
1. **FAISS** (Dense retrieval - embeddings sémantiques)
2. **BM25** (Sparse retrieval - TF-IDF amélioré)
3. **RRF** (Reciprocal Rank Fusion - fusion des résultats)

#### Pourquoi hybride ?

**FAISS seul** :
- ✅ Comprend le **sens sémantique**
- ✅ Bon pour les questions reformulées
- ❌ Peut rater les **mots-clés exacts**

**BM25 seul** :
- ✅ Excellent pour les **correspondances lexicales**
- ✅ Rapide (pas d'embeddings)
- ❌ Ne comprend PAS la **sémantique**

**Hybride (FAISS + BM25 + RRF)** :
- ✅ **Meilleur des deux mondes**
- ✅ Robuste aux reformulations ET aux mots-clés
- ✅ Amélioration du recall de +15-30% (selon études)

---

### Flux RAG détaillé (backend/core/rag.py)

#### ÉTAPE 1 : Indexation (Offline - fait au démarrage)

```python
# backend/core/rag.py : build_index()

1️⃣ Chargement des documents PDF
   ↓
   Utilise PyMuPDF (fitz) pour extraire le texte
   fichier: data/docs/reglement_parking.pdf
   
2️⃣ Chunking intelligent
   ↓
   Découpe en chunks de 500 caractères avec overlap de 50
   Pourquoi ? Éviter de couper les phrases au milieu
   
   Chunk 1: "Article 3: Les horaires d'accès sont..."
   Chunk 2: "...sont de 7h à 20h. Article 4: Les sanctions..."
   
3️⃣ Création des embeddings (FAISS)
   ↓
   Modèle: sentence-transformers/all-MiniLM-L6-v2
   Dimension: 384
   
   Text → Embedding (vecteur dense)
   "Article 3: Les horaires..." → [0.12, -0.34, 0.87, ..., 0.45]
   
   Stockage dans un index FAISS (Flat L2)
   
4️⃣ Indexation BM25
   ↓
   rank-bm25 library
   Tokenisation + Calcul IDF (Inverse Document Frequency)
   
   Stockage en mémoire (dicts Python)
```

**Fichiers créés** :
```
data/faiss_index/
├── index.faiss           # Index FAISS (vecteurs)
├── chunks.pkl            # Chunks de texte
├── metadata.pkl          # Métadonnées (source, page, etc.)
└── bm25_index.pkl        # Index BM25
```

---

#### ÉTAPE 2 : Retrieval (Online - chaque requête)

```python
# backend/core/rag.py : retrieve_hybrid()

USER QUERY: "Quels sont les horaires du parking ?"

1️⃣ Embedding de la requête
   ↓
   "Quels sont les horaires du parking ?"
   → Embedding: [0.23, -0.12, 0.65, ..., 0.34] (384 dims)

2️⃣ FAISS Search (Dense)
   ↓
   Recherche par similarité cosine (L2 distance)
   
   K = 10 chunks les plus proches
   
   Résultats FAISS:
   1. Chunk 5: "Article 3: Horaires 7h-20h..." (score: 0.92)
   2. Chunk 12: "Accès parking lundi-vendredi..." (score: 0.85)
   3. Chunk 8: "Fermeture dimanche..." (score: 0.78)
   ...

3️⃣ BM25 Search (Sparse)
   ↓
   Tokenisation: ["horaires", "parking"]
   
   Calcul du score BM25 pour chaque document:
   BM25(d, q) = Σ IDF(q_i) * (f(q_i, d) * (k1 + 1)) / (f(q_i, d) + k1 * (1 - b + b * |d| / avgdl))
   
   Résultats BM25:
   1. Chunk 5: "Article 3: Horaires..." (score: 8.5)
   2. Chunk 3: "Horaires ouverture..." (score: 7.2)
   3. Chunk 9: "Planning parking..." (score: 6.8)
   ...

4️⃣ RRF Fusion (Reciprocal Rank Fusion)
   ↓
   Fusion des 2 listes de résultats
   
   RRF(d) = Σ 1 / (k + rank_i(d))
   
   où k = 60 (constante standard)
   
   Chunk 5 apparaît en position:
   - FAISS: rank 1 → score = 1/(60+1) = 0.0164
   - BM25:  rank 1 → score = 1/(60+1) = 0.0164
   Total RRF: 0.0328 (meilleur score)
   
   Chunk 3 apparaît en position:
   - FAISS: rank 8 → score = 1/(60+8) = 0.0147
   - BM25:  rank 2 → score = 1/(60+2) = 0.0161
   Total RRF: 0.0308

5️⃣ Reranking final
   ↓
   Top K = 5 chunks fusionnés
   
   Résultats finaux (ordonnés par RRF score):
   1. Chunk 5: "Article 3: Horaires 7h-20h..."
   2. Chunk 3: "Horaires ouverture parking..."
   3. Chunk 12: "Accès lundi-vendredi..."
   4. Chunk 9: "Planning parking..."
   5. Chunk 8: "Fermeture dimanche..."
```

---

#### ÉTAPE 3 : Contexte + Citations

```python
# backend/core/rag.py : format_context_with_citations()

1️⃣ Construction du contexte
   ↓
   Concaténation des chunks avec citations:
   
   Context = """
   [[CIT_1]]: Article 3: Les horaires d'accès au parking sont de 7h à 20h en semaine.
   Source: Règlement parking - Article 3 (page 2)
   
   [[CIT_2]]: Le parking est fermé les dimanches et jours fériés.
   Source: Règlement parking - Article 3 (page 2)
   
   [[CIT_3]]: Accès prolongé jusqu'à 22h pendant les examens.
   Source: Règlement parking - Article 8 (page 4)
   """

2️⃣ Mapping citations
   ↓
   citation_mapping = {
       "[[CIT_1]]": "Règlement parking - Article 3 (page 2)",
       "[[CIT_2]]": "Règlement parking - Article 3 (page 2)",
       "[[CIT_3]]": "Règlement parking - Article 8 (page 4)"
   }
```

---

#### ÉTAPE 4 : LLM Generation avec citations

```python
# backend/core/agent.py : process_message()

PROMPT envoyé au LLM:

"""
CONTEXTE (RÈGLEMENT DU PARKING):
{context avec citations [[CIT_X]]}

QUESTION: Quels sont les horaires du parking?

INSTRUCTIONS:
1. Utilisez UNIQUEMENT les informations du CONTEXTE ci-dessus
2. Citez vos sources avec [[CIT_X]]
3. Si l'info n'est PAS dans le contexte, dites "Je ne trouve pas"
4. Ne jamais inventer de règles
"""

LLM RESPONSE (brute):
"""
Selon le règlement [[CIT_1]], les horaires d'accès au parking sont:
- Lundi à Vendredi: 7h - 20h
- Samedi: 8h - 14h

Le parking est fermé le dimanche [[CIT_2]].

Pendant les périodes d'examens, l'accès peut être prolongé jusqu'à 22h [[CIT_3]].
"""

5️⃣ Post-processing
   ↓
   Remplacement des citations par les références complètes:
   
   [[CIT_1]] → "Règlement parking - Article 3 (page 2)"
```

**Réponse finale au user** :
```
Selon le règlement, les horaires d'accès au parking sont:
- Lundi à Vendredi: 7h - 20h
- Samedi: 8h - 14h

Le parking est fermé le dimanche.

Pendant les périodes d'examens, l'accès peut être prolongé jusqu'à 22h.

📚 Sources:
[1] Règlement parking - Article 3 (page 2)
[2] Règlement parking - Article 3 (page 2)
[3] Règlement parking - Article 8 (page 4)
```

---

### Anti-Hallucination : Cas "No Context"

**Question**: "Quel est le prix d'un abonnement VIP platine ?"

```python
1️⃣ Retrieval
   ↓
   FAISS + BM25 cherchent "VIP platine prix"
   
   Résultats: Chunks avec faible score de similarité (<0.5)
   
   → Aucun chunk pertinent trouvé

2️⃣ Check context_found
   ↓
   if max_similarity < threshold (0.5):
       context_found = False
       
3️⃣ Return early
   ↓
   return {
       "success": True,
       "data": {
           "context_found": False,
           "message": "Je ne trouve pas cette info dans le règlement"
       }
   }

4️⃣ Agent processing
   ↓
   if not context_found:
       return "❌ Je ne trouve pas cette information dans le règlement."
   
   # LLM n'est JAMAIS appelé si pas de contexte
```

**Résultat** : **Pas d'hallucination** ✅

---

## 🖼️ PIPELINE VISION (YOLO + OCR)

### Architecture à 2 étages

```
IMAGE (Plaque de voiture)
    │
    ▼
┌───────────────────────┐
│  ÉTAPE 1: YOLO v11   │  ← Détection d'objets
│  (backend/vision/    │
│   detect.py)         │
└───────┬───────────────┘
        │
        │ Bounding Box: [x, y, w, h]
        ▼
┌───────────────────────┐
│   CROP & RESIZE       │  ← Extraction zone de la plaque
└───────┬───────────────┘
        │
        │ Image cropped (plaque seule)
        ▼
┌───────────────────────┐
│  ÉTAPE 2: LPRNet     │  ← OCR spécialisé plaques
│  (backend/vision/    │
│   ocr.py)            │
└───────┬───────────────┘
        │
        │ Texte: "123 تونس 4567"
        ▼
┌───────────────────────┐
│   NORMALISATION      │  ← Format standard
└───────┬───────────────┘
        │
        ▼
    "123 تونس 4567"
```

---

### ÉTAPE 1 : YOLOv11 - Détection

**Modèle** : `yolov11n.pt` (nano - le plus rapide)

```python
# backend/vision/detect.py

from ultralytics import YOLO

model = YOLO("models/yolov11n.pt")

# Détection
results = model.predict(
    image,
    conf=0.25,      # Seuil de confiance
    iou=0.45,       # Non-Max Suppression
    classes=[2, 5, 7]  # Car, bus, truck
)

# Extraction bounding boxes
for box in results[0].boxes:
    x1, y1, x2, y2 = box.xyxy[0]  # Coordonnées
    conf = box.conf[0]             # Confiance
    cls = box.cls[0]               # Classe
    
    # Crop de la zone détectée
    plate_region = image[int(y1):int(y2), int(x1):int(x2)]
```

**Sortie** : Image croppée contenant la plaque

---

### ÉTAPE 2 : LPRNet - OCR

**Modèle** : LPRNet (License Plate Recognition Network)

**Architecture** :
```
Input (94x24x3)
    ↓
Conv2D (3→64) + ReLU
    ↓
MaxPool2D
    ↓
SmallBlock + ResidualBlock × 3
    ↓
Conv2D (64→128)
    ↓
GlobalAvgPool
    ↓
FC → Softmax
    ↓
CTC Decode (Connectionist Temporal Classification)
    ↓
Output: "123تونس4567"
```

```python
# backend/vision/ocr.py

class LPRNet(nn.Module):
    def __init__(self):
        # Architecture spécialisée pour plaques
        self.backbone = SmallBlock()
        self.residuals = nn.Sequential(
            ResidualBlock(64),
            ResidualBlock(64),
            ResidualBlock(64)
        )
        self.classifier = nn.Linear(128, num_classes)
    
    def forward(self, x):
        x = self.backbone(x)
        x = self.residuals(x)
        x = self.classifier(x)
        return x

# Inférence
def recognize_plate(image):
    # Preprocessing
    img = cv2.resize(image, (94, 24))
    img = img / 255.0
    
    # Forward pass
    logits = model(img)
    
    # CTC Decode
    plate_text = ctc_decode(logits)
    
    return plate_text  # "123 تونس 4567"
```

**Pourquoi CTC ?**
- Gère les séquences de longueur variable
- Pas besoin d'annotation caractère par caractère
- Robuste aux variations de taille de plaque

---

### Normalisation de plaque

```python
# backend/core/decision.py : _normalize_plate()

Input OCR: "176 7413 تونس"  (format OCR brut)
BD format: "176 تونس 7413"  (format standard)

Fonction de normalisation:
def _normalize_plate(plate: str) -> str:
    # Extraire les composants
    parts = plate.split()
    
    # Détection format
    if "تونس" in parts or "TN" in parts:
        # Tunisie
        numbers = [p for p in parts if p.isdigit()]
        
        if len(numbers) == 2:
            # Format: XXX تونس YYYY
            return f"{numbers[0]} تونس {numbers[1]}"
    
    return plate

Résultat: "176 تونس 7413" ✅ (match BD)
```

---

## 🤖 AGENT LLM AVEC OUTILS

### Architecture Agent

```
USER MESSAGE
    │
    ▼
┌─────────────────────────┐
│  1. INJECTION DETECTION │  ← Sécurité
└───────┬─────────────────┘
        │
        ▼
┌─────────────────────────┐
│  2. INTENT DETECTION    │  ← Quelle action ?
│     (Regex patterns)    │
└───────┬─────────────────┘
        │
        ├─► TOOL NEEDED?
        │   │
        │   ├─► YES → Execute Tool (DB/RAG/Decision)
        │   │         │
        │   │         └─► Tool Result
        │   │
        │   └─► NO → Direct to LLM
        │
        ▼
┌─────────────────────────┐
│  3. BUILD PROMPT        │
│     Context = Tool Data │
└───────┬─────────────────┘
        │
        ▼
┌─────────────────────────┐
│  4. LLM CALL            │
│     Gemini 2.0 Flash    │
│     (fallback: Groq)    │
└───────┬─────────────────┘
        │
        ▼
┌─────────────────────────┐
│  5. POST-PROCESSING     │
│     - Replace citations │
│     - Format response   │
└───────┬─────────────────┘
        │
        ▼
    RESPONSE
```

---

### Intent Detection (Sans LLM !)

**Pourquoi pas LLM pour intent ?**
- ❌ Coût élevé (API call)
- ❌ Latence (+500ms)
- ❌ Moins déterministe

**Solution : Regex patterns**

```python
# backend/core/agent.py : INTENT_PATTERNS

INTENT_PATTERNS = {
    "list_students": [
        r"liste? (?:des? )?étudiants?",
        r"tous? les? étudiants?",
        r"afficher? étudiants?",
    ],
    "create_student": [
        r"créer (?:un )?étudiant",
        r"ajouter (?:un )?étudiant",
    ],
    # ... 17 autres tools
}

def detect_intent(message: str) -> Optional[str]:
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message.lower()):
                return intent
    return None
```

**Avantages** :
- ✅ **Instantané** (<1ms)
- ✅ **Déterministe** (même input = même output)
- ✅ **Gratuit** (pas d'API)
- ✅ **Debuggable** facilement

---

### Parsing de paramètres

```python
# backend/core/agent.py : parse_params()

USER: "créer étudiant email=alice@fac.tn nom="Alice Martin" password=Pass123"

Extraction par regex:
├─ EMAIL: r'email[=:\s]+([\\w\\.-]+@[\\w\\.-]+\\.[a-zA-Z]+)'
│  → alice@fac.tn
│
├─ NOM: r'nom[=:\s]+["\']?([^"\\'@\\n,=]+)["\']?'
│  → Alice Martin
│
└─ PASSWORD: r'password[=:\s]+["\']?([^\s"\\']+)["\']?'
   → Pass123

Result: {
    "email": "alice@fac.tn",
    "full_name": "Alice Martin",
    "password": "Pass123"
}
```

**Fallback parsing** (format naturel) :
```python
USER: "créer étudiant alice@fac.tn Alice Martin Pass123"

# Extraction dans l'ordre
words = message.split()
email = [w for w in words if '@' in w][0]
# Retirer email du message
# Dernier mot = password (si alphanum et >6 chars)
# Reste = nom
```

---

### Tool Execution avec RBAC

```python
# backend/core/tools_admin.py : create_student()

def create_student(db, admin_id, email, full_name, password, ip):
    # 1. RBAC Check
    admin = db.query(User).get(admin_id)
    if admin.role != UserRole.ADMIN:
        # Log security violation
        _log_security_event(
            db, admin_id, "RBAC_VIOLATION",
            f"User {admin_id} tried to create student",
            ip
        )
        return {
            "success": False,
            "error": "Action non autorisée. Rôle ADMIN requis."
        }
    
    # 2. Business Logic
    if db.query(User).filter(User.email == email).first():
        return {
            "success": False,
            "error": f"L'email '{email}' existe déjà."
        }
    
    # 3. Create User
    user = User(
        email=email,
        full_name=full_name,
        role=UserRole.STUDENT,
        password_hash=pwd_context.hash(password)
    )
    db.add(user)
    db.commit()
    
    # 4. Audit Log
    _log_audit(
        db, admin_id, "CREATE_STUDENT", "user", user.id,
        {"email": email, "full_name": full_name},
        ip
    )
    
    # 5. Return
    return {
        "success": True,
        "data": {"id": user.id, "email": email},
        "message": f"Étudiant '{full_name}' créé."
    }
```

**4 couches de sécurité** :
1. ✅ RBAC (Role-Based Access Control)
2. ✅ Validation métier
3. ✅ Audit logging
4. ✅ Security events (violations)

---

## 🔄 FLUX DE DONNÉES COMPLET

### Cas d'usage : "Créer étudiant avec abonnement et vérifier accès"

```
USER (Admin): "créer étudiant email=test@fac.tn nom=Test User password=test123"
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ FRONTEND (React)                                         │
│  ChatInterface.jsx → sendMessage()                      │
│  → axios.post('/api/chat/message', {message})           │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP POST
                 ▼
┌─────────────────────────────────────────────────────────┐
│ BACKEND - FastAPI Router                                │
│  /api/chat/message (routes/chat.py)                    │
│  → Authenticate JWT                                      │
│  → Extract user from token                              │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ AGENT.PY - process_message()                           │
│                                                          │
│  1️⃣ INJECTION CHECK                                    │
│     InjectionDetector.check(message)                    │
│     → Patterns: "ignore", "admin", "password"...        │
│     → Score < 0.3 → ✅ PASS                             │
│                                                          │
│  2️⃣ INTENT DETECTION                                   │
│     detect_intent(message, user.role)                   │
│     → Match: "créer (?:un )?étudiant"                   │
│     → Intent: "create_student"                          │
│                                                          │
│  3️⃣ PARAMETER PARSING                                  │
│     parse_params(message, "create_student")             │
│     → email: "test@fac.tn"                              │
│     → full_name: "Test User"                            │
│     → password: "test123"                               │
│                                                          │
│  4️⃣ TOOL EXECUTION                                     │
│     execute_tool(db, user, "create_student", params)    │
│     ↓                                                    │
└─────┼────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ TOOLS_ADMIN.PY - create_student()                      │
│                                                          │
│  1. RBAC Check                                          │
│     if user.role != ADMIN: return error                 │
│                                                          │
│  2. Duplicate Check                                      │
│     if email exists: return error                       │
│                                                          │
│  3. Hash Password                                        │
│     pwd_hash = bcrypt.hash("test123")                   │
│                                                          │
│  4. Insert DB                                            │
│     INSERT INTO users (email, full_name, password_hash) │
│     VALUES ('test@fac.tn', 'Test User', '...')          │
│                                                          │
│  5. Audit Log                                            │
│     INSERT INTO audit_logs (user_id, action, ...)       │
│                                                          │
│  6. Return                                               │
│     {"success": True, "data": {...}, "message": "..."}  │
└─────┬───────────────────────────────────────────────────┘
      │ Tool Result
      ▼
┌─────────────────────────────────────────────────────────┐
│ AGENT.PY - LLM Formatting                              │
│                                                          │
│  Build Prompt:                                          │
│  """                                                     │
│  Tu es l'assistant FacPark.                             │
│  DONNÉES RÉELLES (BD):                                  │
│  {                                                       │
│    "success": true,                                     │
│    "data": {"id": 15, "email": "test@fac.tn"},          │
│    "message": "Étudiant 'Test User' créé."              │
│  }                                                       │
│                                                          │
│  PRÉSENTE ces données de manière claire et utile.       │
│  """                                                     │
│                                                          │
│  LLM Call:                                              │
│  Gemini 2.0 Flash (ou Groq si fail)                     │
│  ↓                                                       │
│  Response: "✅ Étudiant créé avec succès! ..."          │
└─────┬───────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│ FRONTEND - Display Response                            │
│  ChatInterface.jsx                                       │
│  → Format Markdown                                       │
│  → Display in chat bubble                               │
└─────────────────────────────────────────────────────────┘
```

---

## ⚙️ OPTIMISATIONS ET BONNES PRATIQUES

### 1. RAG Performance

**Indexation** :
```python
# Lazy loading de l'index FAISS
class RAGSystem:
    _instance = None
    _index_loaded = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def build_index(self):
        if not self._index_loaded:
            # Load FAISS index
            self.index = faiss.read_index("data/faiss_index/index.faiss")
            self._index_loaded = True
```

**Pourquoi ?**
- ✅ Chargement unique au startup (singleton)
- ✅ Pas de rechargement à chaque requête
- ✅ Économie de mémoire

**Optimisation FAISS** :
```python
# backend/core/rag.py

# Option 1: Flat (exact search)
index = faiss.IndexFlatL2(384)  # Slow mais précis

# Option 2: IVF (approximate search) - RECOMMANDÉ pour >10k docs
quantizer = faiss.IndexFlatL2(384)
index = faiss.IndexIVFFlat(quantizer, 384, nlist=100)
index.train(embeddings)  # Training requis
```

**Trade-off** :
- Flat: Précision 100%, Vitesse O(n)
- IVF: Précision ~95%, Vitesse O(log n)

---

### 2. LLM Orchestration

**Fallback Chain** :
```python
async def call_llm(prompt: str) -> LLMResponse:
    # Try Gemini first (faster, better quality)
    gemini = get_gemini_client()
    if gemini:
        try:
            response = gemini.generate_content(prompt)
            return LLMResponse(
                content=response.text,
                model="gemini-2.0-flash",
                success=True
            )
        except Exception as e:
            logger.warning(f"Gemini failed: {e}, trying Groq")
    
    # Fallback to Groq
    groq = get_groq_client()
    if groq:
        response = groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model="llama-3.3-70b",
            success=True
        )
    
    # No LLM available
    return LLMResponse(
        content="",
        success=False,
        error="No LLM configured"
    )
```

**Avantages** :
- ✅ Haute disponibilité (multi-provider)
- ✅ Coût-efficace (Gemini = gratuit tier, Groq = backup)
- ✅ Fail-safe

---

### 3. Database Triggers (Logique métier en BD)

**Exemple : Max 3 véhicules par étudiant**

```sql
-- data/sql/01_schema.sql

DELIMITER $$

CREATE TRIGGER before_vehicle_insert
BEFORE INSERT ON vehicles
FOR EACH ROW
BEGIN
    DECLARE vehicle_count INT;
    
    SELECT COUNT(*) INTO vehicle_count
    FROM vehicles
    WHERE user_id = NEW.user_id;
    
    IF vehicle_count >= 3 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Maximum 3 vehicles per student';
    END IF;
END$$

DELIMITER ;
```

**Pourquoi triggers ?**
- ✅ **Garantie au niveau BD** (même si backend contourné)
- ✅ **Atomicité** (transaction-safe)
- ✅ **Performance** (logique en SQL)

**Autres triggers** :
- 1 seul abonnement actif (désactive les autres)
- 1 seule place active par étudiant
- Libération automatique de place si étudiant supprimé

---

### 4. Caching & Memoization

```python
# Exemple: Cache embeddings
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding(text: str) -> np.ndarray:
    """Cache des embeddings fréquents"""
    return model.encode(text)
```

**Cas d'usage** :
- Questions répétitives ("horaires parking")
- Embeddings de chunks statiques

---

### 5. Logging structuré

```python
import logging
import json

logger = logging.getLogger(__name__)

# Structured logging
logger.info(json.dumps({
    "event": "tool_execution",
    "tool": "create_student",
    "user_id": user.id,
    "success": True,
    "latency_ms": 145,
    "timestamp": datetime.now().isoformat()
}))
```

**Avantages** :
- ✅ Parsing facile (ELK, CloudWatch)
- ✅ Métriques automatiques
- ✅ Debugging rapide

---

## 📊 MÉTRIQUES & OBSERVABILITÉ

### Métriques clés

```python
# Exemple de tracking
class MetricsTracker:
    def __init__(self):
        self.metrics = {
            "rag_queries": 0,
            "rag_cache_hits": 0,
            "llm_calls": 0,
            "llm_tokens_used": 0,
            "tool_executions": {},
            "avg_latency": {}
        }
    
    def track_rag_query(self, latency_ms, cache_hit):
        self.metrics["rag_queries"] += 1
        if cache_hit:
            self.metrics["rag_cache_hits"] += 1
        # ...
```

---

## 🎯 RÉSUMÉ ARCHITECTURE IA

| Composant | Technologie | Rôle | Caractéristiques |
|-----------|-------------|------|------------------|
| **RAG Retrieval** | FAISS + BM25 + RRF | Récupération documents | Hybride dense+sparse, RRF fusion |
| **Embeddings** | all-MiniLM-L6-v2 | Vectorisation texte | 384 dims, multilingual |
| **LLM** | Gemini 2.0 Flash / Groq | Génération + Formatting | Fallback chain, structured prompts |
| **Vision - Detection** | YOLOv11n | Détection plaques | Real-time, 80 FPS |
| **Vision - OCR** | LPRNet | Lecture plaques | CTC decode, arabe+latin |
| **Decision Engine** | Règles Python | Décision ALLOW/DENY | **NO LLM**, déterministe |
| **Agent** | Intent + Tools | Orchestration | Regex patterns, 19 tools |
| **Security** | Regex + RBAC | Anti-injection + Auth | Multi-layer, audit logs |

---

**Document créé par** : Antigravity AI (Expert IA)  
**Date** : 2026-01-21  
**Version** : 1.0 - Deep Dive Technique
