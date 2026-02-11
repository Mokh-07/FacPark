"""
FacPark - LLM Agent with Automatic Tool Execution
Orchestrates LLM (Gemini/Groq) with automatic tool calling and RAG.

CRITICAL RULES:
1. LLM NEVER decides access (DecisionEngine only)
2. All DB writes via tools with RBAC
3. No context → No answer (anti-hallucination)
4. Tools are executed AUTOMATICALLY, not just mentioned
5. Prompt injection detection before processing
"""

import re
import json
import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import User, SecurityEvent, UserRole

logger = logging.getLogger(__name__)


# =============================================================================
# INJECTION DETECTION
# =============================================================================
class InjectionDetector:
    """Detects prompt injection attempts."""
    
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in settings.INJECTION_PATTERNS]
    
    def check(self, text: str) -> tuple[bool, Optional[str], float]:
        """
        Check if text contains injection patterns.
        Returns: (is_injection, matched_pattern, score)
        """
        if not text:
            return False, None, 0.0
        
        score = 0.0
        matched = None
        
        for pattern in self.patterns:
            if pattern.search(text):
                score += 0.3
                matched = pattern.pattern
                if score >= settings.INJECTION_SCORE_THRESHOLD:
                    break
        
        return score >= settings.INJECTION_SCORE_THRESHOLD, matched, score


_detector = InjectionDetector()


def log_injection_attempt(db: Session, user_id: Optional[int], text: str,
                          pattern: str, ip: Optional[str] = None):
    """Log injection attempt to security_events."""
    event = SecurityEvent(
        event_type="PROMPT_INJECTION",
        user_id=user_id,
        description="Tentative d'injection de prompt détectée",
        payload=text[:500],  # Truncate
        pattern_matched=pattern,
        severity="HIGH",
        ip_address=ip
    )
    db.add(event)
    db.commit()
    logger.warning(f"Injection attempt from user {user_id}: {pattern}")


# =============================================================================
# LLM CLIENTS
# =============================================================================
@dataclass
class LLMResponse:
    """Standard LLM response."""
    content: str
    model: str
    tokens_used: int
    success: bool
    error: Optional[str] = None
    tool_calls: List[Dict] = None


def get_gemini_client():
    """Get Gemini client. Reloads key from .env file directly."""
    import os
    from pathlib import Path
    
    # Try to read .env directly to get the latest key written by the tool
    env_path = Path(settings.BASE_DIR).parent / ".env"
    api_key = None
    
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GEMINI_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip()
                        break
        except Exception:
            pass
            
    # Fallback to env var or settings
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    
    if not api_key:
        return None
    
    # Also reload model name dynamically
    model_name = "gemini-pro" # Default safe model
    
    # Try multiple possible locations for .env
    possible_paths = [
        Path(settings.BASE_DIR).parent / ".env",          # Standard: /backend/..
        Path(settings.BASE_DIR) / ".env",                 # Inside backend
        Path(os.getcwd()) / ".env",                       # CWD
        Path("c:/Users/Mokhtar/Desktop/fac_park2/.env")   # Absolute fallback
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("GEMINI_MODEL="):
                            val = line.strip().split("=", 1)[1].strip()
                            if val: model_name = val
                        elif line.strip().startswith("GEMINI_API_KEY="):
                            val = line.strip().split("=", 1)[1].strip()
                            if val and not api_key: api_key = val
                break # Found valid .env
            except Exception:
                continue
            
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name), model_name


def get_groq_client():
    """Get Groq client. Reloads key and model from .env file directly."""
    import os
    from pathlib import Path
    
    env_path = Path(settings.BASE_DIR).parent / ".env"
    api_key = None
    model_name = settings.GROQ_MODEL
    
    if env_path.exists():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("GROQ_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip()
                    elif line.strip().startswith("GROQ_MODEL="):
                        model_name = line.strip().split("=", 1)[1].strip()
        except Exception:
            pass
            
    if not api_key:
        api_key = os.environ.get("GROQ_API_KEY") or settings.GROQ_API_KEY
    
    if not api_key:
        return None
        
    from groq import Groq
    return Groq(api_key=api_key), model_name


# =============================================================================
# INTENT DETECTION & TOOL MAPPING
# =============================================================================
# =============================================================================
# TOOL HELP - Documentation for tools requiring parameters
# =============================================================================
TOOL_HELP = {
    "create_student": {
        "description": "Créer un nouvel étudiant",
        "required_params": ["email", "full_name"],
        "optional_params": ["password"],
        "example": 'Créer étudiant email=jean.dupont@etudiant.fac.tn nom="Jean Dupont"',
        "usage": """Pour créer un étudiant, dites par exemple:
• "Créer étudiant email=jean.dupont@etudiant.fac.tn nom=Jean Dupont"
• "Ajouter étudiant jean.dupont@etudiant.fac.tn Jean Dupont"

Paramètres requis:
- **email**: L'adresse email de l'étudiant
- **full_name** ou **nom**: Le nom complet

Paramètre optionnel:
- **password**: Mot de passe (par défaut: changeme123)"""
    },
    "delete_student": {
        "description": "Supprimer un étudiant",
        "required_params": ["student_email"],
        "example": "Supprimer étudiant jean.dupont@etudiant.fac.tn",
        "usage": """Pour supprimer un étudiant:
• "Supprimer étudiant jean.dupont@etudiant.fac.tn"

⚠️ Cette action est irréversible !"""
    },
    "add_vehicle": {
        "description": "Ajouter un véhicule à un étudiant",
        "required_params": ["student_email", "plate"],
        "example": "Ajouter véhicule 123 تونس 4567 à jean.dupont@etudiant.fac.tn",
        "usage": """Pour ajouter un véhicule:
• "Ajouter véhicule plaque=123 تونس 4567 étudiant=jean.dupont@etudiant.fac.tn"

Paramètres requis:
- **plate** ou **plaque**: La plaque d'immatriculation
- **student_email** ou **étudiant**: L'email de l'étudiant"""
    },
    "remove_vehicle": {
        "description": "Retirer un véhicule",
        "required_params": ["plate"],
        "example": "Retirer véhicule 123 تونس 4567",
        "usage": """Pour retirer un véhicule:
• "Retirer véhicule 123 تونس 4567"
• "Supprimer plaque 123 تونس 4567" """
    },
    "create_subscription": {
        "description": "Créer un abonnement",
        "required_params": ["student_email", "sub_type"],
        "example": "Créer abonnement mensuel pour jean.dupont@etudiant.fac.tn",
        "usage": """Pour créer un abonnement:
• "Créer abonnement mensuel pour jean.dupont@etudiant.fac.tn"
• "Abonner jean.dupont@etudiant.fac.tn type=annuel"

Types d'abonnement: **monthly** (30j), **semester** (180j), **annual** (365j)"""
    },
    "renew_subscription": {
        "description": "Renouveler un abonnement",
        "required_params": ["student_email", "days"],
        "example": "Renouveler abonnement jean.dupont@etudiant.fac.tn 30 jours",
        "usage": """Pour renouveler un abonnement:
• "Renouveler abonnement jean.dupont@etudiant.fac.tn 30 jours"

Paramètres requis:
- **student_email**: L'email de l'étudiant
- **days** ou **jours**: Nombre de jours à ajouter"""
    },
    "assign_slot": {
        "description": "Attribuer une place de parking",
        "required_params": ["student_email", "slot_code"],
        "example": "Attribuer place A-01 à jean.dupont@etudiant.fac.tn",
        "usage": """Pour attribuer une place:
• "Attribuer place A-01 à jean.dupont@etudiant.fac.tn"

Codes places: A-01 à A-40, B-01 à B-40, C-01 à C-20"""
    },
    "suspend_access": {
        "description": "Suspendre l'accès d'un étudiant",
        "required_params": ["student_email", "days", "reason"],
        "example": "Suspendre jean.dupont@etudiant.fac.tn 7 jours raison=Stationnement interdit",
        "usage": """Pour suspendre un accès:
• "Suspendre jean.dupont@etudiant.fac.tn 7 jours raison=Stationnement interdit"

Paramètres requis:
- **student_email**: L'email de l'étudiant
- **days** ou **jours**: Durée de suspension
- **reason** ou **raison**: Motif de la suspension"""
    },
    "check_plate_access": {
        "description": "Vérifier l'accès d'une plaque",
        "required_params": ["plate"],
        "example": "Vérifier plaque 123 تونس 4567",
        "usage": """Pour vérifier l'accès d'une plaque:
• "Vérifier plaque 123 تونس 4567"
• "Check accès 123 تونس 4567" """
    },
}

# Tools that don't require parameters (can be executed directly)
READ_ONLY_TOOLS = [
    "get_my_profile", "get_my_vehicles", "get_my_subscription",
    "get_my_slot", "get_my_access_history", "ask_reglement",
    "list_students", "get_admin_stats", "list_slots", "list_available_slots"
]

INTENT_PATTERNS = {
    # Student intents
    "get_my_profile": [
        r"mon profil", r"mes informations", r"qui suis[- ]?je", r"mon compte",
        r"mes données", r"profile", r"info(rmation)?s? sur moi"
    ],
    "get_my_vehicles": [
        r"mes? v[ée]hicules?", r"mes? voitures?", r"mes? plaques?", 
        r"quelles? plaques?", r"mes? autos?"
    ],
    "get_my_subscription": [
        r"mon abonnement", r"ma souscription", r"expir", r"validit[ée]",
        r"jours? restants?", r"fin abonnement", r"dur[ée]e"
    ],
    "get_my_slot": [
        r"ma place", r"mon? emplacement", r"o[uù] garer", r"parking assign[ée]",
        r"place attribu[ée]e", r"n[uméro]+ place"
    ],
    "get_my_access_history": [
        r"historique", r"mes? acc[eè]s", r"derni[eè]res? entr[ée]es?",
        r"log acc[eè]s", r"passages?"
    ],
    # Admin intents - READ
    "list_students": [
        r"liste? (?:des? )?[ée]tudiants?", r"tous? les? [ée]tudiants?",
        r"afficher? [ée]tudiants?", r"voir [ée]tudiants?", r"[ée]tudiants? inscrits?",
        r"combien d'[ée]tudiants?", r"donner? (?:les? )?[ée]tudiants?"
    ],
    "get_admin_stats": [
        r"statistiques?", r"stats?", r"dashboard", r"tableau de bord",
        r"r[ée]sum[ée]", r"overview", r"chiffres?"
    ],
    "list_slots": [
        r"lister? (?:toutes? )?(?:les? )?places?", r"liste? (?:des? )?places?",
        r"voir (?:les? )?places?", r"afficher? (?:les? )?places?",
        r"places? de parking", r"toutes? (?:les? )?places?"
    ],
    "list_available_slots": [
        r"places? disponibles?", r"liste? (?:des? )?places? disponibles?",
        r"voir places? disponibles?", r"places? libres?",
        r"quelles? places? (?:sont )?disponibles?"
    ],
    # Admin intents - WRITE
    "create_student": [
        r"cr[ée]er (?:un )?[ée]tudiant", r"ajouter (?:un )?[ée]tudiant",
        r"nouveau(?:vel)? [ée]tudiant", r"inscrire (?:un )?[ée]tudiant"
    ],
    "delete_student": [
        r"supprimer (?:l'?)?[ée]tudiant", r"retirer (?:l'?)?[ée]tudiant",
        r"effacer (?:l'?)?[ée]tudiant", r"delete student"
    ],
    "add_vehicle": [
        r"ajouter (?:un )?v[ée]hicule", r"ajouter (?:une )?plaque",
        r"ajouter (?:une )?voiture", r"nouveau v[ée]hicule"
    ],
    "remove_vehicle": [
        r"supprimer (?:le )?v[ée]hicule", r"retirer (?:la )?plaque",
        r"supprimer (?:la )?plaque", r"effacer v[ée]hicule"
    ],
    "create_subscription": [
        r"cr[ée]er (?:un )?abonnement", r"ajouter (?:un )?abonnement",
        r"abonner", r"nouveau abonnement",
        r"abonnement (?:mensuel|semestriel|annuel)",  # "abonnement mensuel pour..."
        r"crr?e+r? aboo?n+e?ment"  # Typos comme "crre aboonment"
    ],
    "renew_subscription": [
        r"renouveler (?:l'?)?abonnement", r"prolonger (?:l'?)?abonnement",
        r"renew"
    ],
    "assign_slot": [
        r"attribuer (?:une )?place", r"assigner (?:une )?place",
        r"affecter (?:une )?place", r"donner (?:une )?place"
    ],
    "suspend_access": [
        r"suspendre (?:l'?)?acc[eè]s", r"bloquer (?:l'?)?[ée]tudiant",
        r"suspendre (?:l'?)?[ée]tudiant", r"suspension"
    ],
    "check_plate_access": [
        r"v[ée]rifier (?:la )?plaque", r"check (?:la )?plaque",
        r"tester (?:la )?plaque", r"acc[eè]s plaque"
    ],
}


# =============================================================================
# PARAMETER PARSING
# =============================================================================
def parse_params(message: str, tool_name: str) -> Dict[str, Any]:
    """
    Parse parameters from natural language message.
    Supports flexible, natural language commands.
    
    Examples that should work:
    - "créer abonnement mensuel pour mokhtar.bouchekoua@fac.tn"
    - "abonner jean.dupont@mail.com type=annuel"
    - "ajouter étudiant email: test@fac.tn nom: Jean Test"
    """
    params = {}
    msg_lower = message.lower()
    
    # ========================================
    # EMAIL EXTRACTION (very flexible)
    # ========================================
    # Pattern for emails - supports various formats
    email_patterns = [
        r'([\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,})',  # Standard email
        r'email[=:\s]+["\']?([\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,})["\']?',  # email=xxx
        r'pour\s+([\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,})',  # "pour xxx@mail.com"
        r'[àa]\s+([\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,})',   # "à xxx@mail.com"
        r'etudiant\s+([\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,})', # "etudiant xxx@mail.com"
    ]
    for pattern in email_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            email = match.group(1)
            params["email"] = email
            params["student_email"] = email
            break
    
    # ========================================
    # PASSWORD EXTRACTION (do this FIRST to avoid including it in name)
    # ========================================
    pwd_patterns = [
        r'password[=:\s]+["\']?([^\s"\']+)["\']?',
        r'mot\s*de\s*passe[=:\s]+["\']?([^\s"\']+)["\']?',
        r'mdp[=:\s]+["\']?([^\s"\']+)["\']?',
    ]
    extracted_password = None
    for pattern in pwd_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            params["password"] = match.group(1)
            extracted_password = match.group(1)
            break
    
    # ========================================
    # NAME EXTRACTION
    # ========================================
    name_patterns = [
        r'nom[=:\s]+["\']?([^"\'@\n,=]+)["\']?',
        r'full_name[=:\s]+["\']?([^"\'@\n,=]+)["\']?',
        r'name[=:\s]+["\']?([^"\'@\n,=]+)["\']?',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if name and len(name) > 1:
                params["full_name"] = name
                break
    
    # Extract name from natural language if not found
    # IMPROVED: Remove password from message if detected to avoid including it in name
    if "full_name" not in params and tool_name == "create_student":
        msg_without_email = re.sub(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]+', '', message)
        
        # NEW: Remove extracted password from message before parsing name
        if extracted_password:
            msg_without_email = msg_without_email.replace(extracted_password, '')
        
        msg_clean = re.sub(
            r'(cr[ée]er|ajouter|nouveau|etudiant|[ée]tudiant|email|nom|full_name|password|mot\s*de\s*passe|mdp|=|@|:)', 
            '', msg_without_email, flags=re.IGNORECASE
        )
        words = [w.strip() for w in msg_clean.split() if len(w.strip()) > 1 and not w.startswith('=')]
        if words:
            # Take only the first 2-3 words (typical name: prénom nom)
            # Filter out numeric-only words (likely part of password)
            name_words = [w for w in words[:3] if not w.isdigit()]
            if name_words:
                params["full_name"] = " ".join(name_words).strip()
    
    
    # ========================================
    # SUBSCRIPTION TYPE (flexible parsing)
    # ========================================
    # IMPORTANT: Map to FRENCH values (MENSUEL, SEMESTRIEL, ANNUEL) to match SQL enum
    sub_type_map = {
        # French variants → French enum value
        "mensuel": "MENSUEL", "mois": "MENSUEL", "30j": "MENSUEL",
        "semestriel": "SEMESTRIEL", "semestre": "SEMESTRIEL", "180j": "SEMESTRIEL",
        "annuel": "ANNUEL", "année": "ANNUEL", "365j": "ANNUEL", "an": "ANNUEL",
        # English variants → French enum value (for flexibility)
        "monthly": "MENSUEL", "month": "MENSUEL",
        "semester": "SEMESTRIEL", "semestrial": "SEMESTRIEL",
        "annual": "ANNUEL", "yearly": "ANNUEL", "year": "ANNUEL"
    }
    for word, sub_type in sub_type_map.items():
        if word in msg_lower:
            params["sub_type"] = sub_type
            break
    
    # Also check for type=xxx format
    type_match = re.search(r'type[=:\s]+["\']?(\w+)["\']?', message, re.IGNORECASE)
    if type_match:
        type_val = type_match.group(1).lower()
        if type_val in sub_type_map:
            params["sub_type"] = sub_type_map[type_val]
    
    # ========================================
    # PLATE EXTRACTION (Arabic/Tunisian plates)
    # ========================================
    plate_patterns = [
        r'(\d{1,3})\s*(?:تونس|TN|tn|tun)\s*(\d{3,4})',  # 123 تونس 4567
        r'(\d{3,4})\s*(?:تونس|TN|tn)\s*(\d{1,3})',       # 4567 تونس 123 (reversed)
        r'plaque[=:\s]+["\']?([^"\'@\n,]+)["\']?',
    ]
    for i, pattern in enumerate(plate_patterns):
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            if i == 0:
                params["plate"] = f"{match.group(1)} تونس {match.group(2)}"
            elif i == 1:
                params["plate"] = f"{match.group(2)} تونس {match.group(1)}"
            else:
                params["plate"] = match.group(1).strip()
            break
    
    # ========================================
    # DAYS EXTRACTION (for suspension/renewal)
    # ========================================
    days_patterns = [
        r'(\d+)\s*(?:jours?|days?|j\b)',
        r'dur[ée]e[=:\s]*(\d+)',
    ]
    for pattern in days_patterns:
        match = re.search(pattern, msg_lower)
        if match:
            params["days"] = int(match.group(1))
            break
    
    # ========================================
    # REASON EXTRACTION (for suspension)
    # ========================================
    reason_patterns = [
        r'raison[=:\s]+["\']?([^"\'@\n]+)["\']?',
        r'motif[=:\s]+["\']?([^"\'@\n]+)["\']?',
        r'car\s+(.+)',
        r'parce\s+que\s+(.+)',
    ]
    for pattern in reason_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            params["reason"] = match.group(1).strip()
            break
    
    # Default reason for suspension
    if tool_name == "suspend_access" and "reason" not in params:
        params["reason"] = "Non spécifiée"
    
    # ========================================
    # SLOT CODE EXTRACTION (A-01, B-15, etc.)
    # ========================================
    slot_patterns = [
        r'([A-Ca-c])[-\s]?(\d{1,2})',
        r'place[=:\s]+["\']?([A-Ca-c][-\s]?\d{1,2})["\']?',
    ]
    for pattern in slot_patterns:
        match = re.search(pattern, message)
        if match:
            if len(match.groups()) == 2:
                params["slot_code"] = f"{match.group(1).upper()}-{match.group(2).zfill(2)}"
            else:
                # Clean up the slot code
                slot = match.group(1).upper().replace(' ', '-')
                if '-' not in slot:
                    slot = slot[0] + '-' + slot[1:]
                params["slot_code"] = slot
            break
    
    
    logger.info(f"Parsed params for {tool_name}: {params}")
    return params


def check_required_params(params: Dict, tool_name: str) -> tuple[bool, List[str]]:
    """Check if all required parameters are present."""
    if tool_name not in TOOL_HELP:
        return True, []
    
    required = TOOL_HELP[tool_name].get("required_params", [])
    missing = []
    
    for param in required:
        if param == "email" and "email" not in params and "student_email" not in params:
            missing.append("email")
        elif param == "student_email" and "email" not in params and "student_email" not in params:
            missing.append("email de l'étudiant")
        elif param == "full_name" and "full_name" not in params:
            missing.append("nom complet")
        elif param == "plate" and "plate" not in params:
            missing.append("plaque")
        elif param == "days" and "days" not in params:
            missing.append("nombre de jours")
        elif param == "reason" and "reason" not in params:
            missing.append("raison")
        elif param == "sub_type" and "sub_type" not in params:
            missing.append("type (mensuel/semestriel/annuel)")
        elif param == "slot_code" and "slot_code" not in params:
            missing.append("code place (ex: A-01)")
    
    return len(missing) == 0, missing


def detect_intent(message: str, user_role: UserRole) -> tuple[Optional[str], bool]:
    """
    Detect user intent from message.
    Returns: (intent_name, is_help_request)
    - is_help_request=True means user is asking HOW to do something
    - is_help_request=False means user wants to EXECUTE the action
    """
    message_lower = message.lower()
    
    # Check if it's a help/info request (not execution)
    help_patterns = [
        r"comment\s+", r"how\s+to", r"aide\s+", r"help\s+",
        r"\?$", r"expliquer?", r"qu'?est[- ]ce", r"c'?est quoi",
        r"exemple", r"montrer?", r"possible"
    ]
    is_help = any(re.search(p, message_lower) for p in help_patterns)
    
    # Define allowed intents based on role
    allowed_intents = list(INTENT_PATTERNS.keys())
    if user_role != UserRole.ADMIN:
        # Students can only use student tools
        allowed_intents = [k for k in allowed_intents if k.startswith("get_my_") or k == "ask_reglement"]
    
    for intent, patterns in INTENT_PATTERNS.items():
        if intent not in allowed_intents:
            continue
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return intent, is_help
    
    # Check for RAG query (regulations) - expanded keywords
    rag_keywords = [
        "règlement", "règle", "article", "sanction", "horaires", "horaire",
        "badge", "interdit", "autorisé", "permis", "pénalité", "amende",
        "accès", "parking", "place", "stationnement", "véhicule", "moto",
        "abonnement", "inscription", "procédure", "document", "tarif", "prix",
        "ouverture", "fermeture", "dimanche", "nuit", "invité", "visiteur",
        "caméra", "surveillance", "vol", "dégât", "responsabilité"
    ]
    if any(kw in message_lower for kw in rag_keywords):
        return "ask_reglement", False
    
    return None, False


# =============================================================================
# TOOL EXECUTION
# =============================================================================
def execute_tool(db: Session, user: User, tool_name: str, 
                 params: Dict = None, ip: Optional[str] = None) -> Dict:
    """Execute a tool and return result."""
    from backend.core.tools import (
        get_my_profile, get_my_vehicles, get_my_subscription,
        get_my_slot, get_my_access_history, get_my_suspension_status, ask_reglement
    )
    from backend.core.tools_admin import (
        list_students, create_student, delete_student,
        add_vehicle, remove_vehicle, create_subscription,
        renew_subscription, assign_slot, suspend_access,
        get_admin_stats, admin_check_plate_access,
        list_slots, list_available_slots
    )
    
    params = params or {}
    
    # Student tools
    if tool_name == "get_my_profile":
        return get_my_profile(db, user.id)
    elif tool_name == "get_my_vehicles":
        return get_my_vehicles(db, user.id)
    elif tool_name == "get_my_subscription":
        return get_my_subscription(db, user.id)
    elif tool_name == "get_my_slot":
        return get_my_slot(db, user.id)
    elif tool_name == "get_my_access_history":
        return get_my_access_history(db, user.id, params.get("limit", 10))
    elif tool_name == "get_my_suspension_status":
        return get_my_suspension_status(db, user.id)
    elif tool_name == "ask_reglement":
        return ask_reglement(db, user.id, params.get("query", ""), params.get("top_k", 5))
    
    # Admin tools
    elif tool_name == "list_students":
        return list_students(db, user.id, params.get("search"), params.get("limit", 50), ip)
    elif tool_name == "get_admin_stats":
        return get_admin_stats(db, user.id, ip)
    elif tool_name == "list_slots":
        return list_slots(db, user.id, params.get("zone"), ip)
    elif tool_name == "list_available_slots":
        return list_available_slots(db, user.id, params.get("zone"), params.get("limit", 50), ip)
    elif tool_name == "create_student":
        return create_student(db, user.id, params["email"], params["full_name"], 
                            params.get("password", "changeme123"), ip)
    elif tool_name == "delete_student":
        return delete_student(db, user.id, params["student_email"], ip)
    elif tool_name == "add_vehicle":
        return add_vehicle(db, user.id, params["student_email"], params["plate"],
                          params.get("plate_type", "TN"), ip)
    elif tool_name == "remove_vehicle":
        return remove_vehicle(db, user.id, params["plate"], ip)
    elif tool_name == "create_subscription":
        return create_subscription(db, user.id, params["student_email"], params["sub_type"], ip)
    elif tool_name == "renew_subscription":
        return renew_subscription(db, user.id, params["student_email"], params["days"], ip)
    elif tool_name == "assign_slot":
        return assign_slot(db, user.id, params["student_email"], params["slot_code"], ip)
    elif tool_name == "suspend_access":
        return suspend_access(db, user.id, params["student_email"], params["days"],
                            params["reason"], ip)
    elif tool_name == "check_plate_access":
        return admin_check_plate_access(db, user.id, params["plate"], ip)
    
    return {"success": False, "error": f"Outil '{tool_name}' non implémenté."}


# =============================================================================
# LLM CALL
# =============================================================================
async def call_llm(prompt: str, system_prompt: str = "") -> LLMResponse:
    """Call LLM with fallback: Gemini -> Groq."""
    gemini_error = None
    
    # Try Gemini first
    gemini_data = get_gemini_client()
    if gemini_data:
        gemini, gemini_model = gemini_data
        try:
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            response = gemini.generate_content(
                full_prompt,
                generation_config={
                    "max_output_tokens": settings.LLM_MAX_TOKENS,
                    "temperature": settings.LLM_TEMPERATURE
                }
            )
            return LLMResponse(
                content=response.text,
                model=gemini_model,
                tokens_used=0,
                success=True
            )
        except Exception as e:
            gemini_error = str(e)
            logger.warning(f"Gemini failed, trying Groq: {e}")
    
    # Fallback to Groq
    groq_data = get_groq_client()
    if groq_data:
        groq, groq_model = groq_data
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = groq.chat.completions.create(
                model=groq_model,
                messages=messages,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE
            )
            return LLMResponse(
                content=response.choices[0].message.content,
                model=groq_model,
                tokens_used=response.usage.total_tokens,
                success=True
            )
        except Exception as e:
            logger.error(f"Groq failed: {e}")
            error_msg = f"Groq Error: {e}"
            if gemini_error:
                error_msg += f" || Primary Gemini also failed: {gemini_error}"
                
            return LLMResponse(
                content="", model="", tokens_used=0, success=False,
                error=error_msg
            )
    
    # If we get here, neither worked or no clients configured
    error_msg = "No LLM configured."
    if gemini_error:
        error_msg = f"Gemini failed: {gemini_error}."
        
    return LLMResponse(
        content="", model="", tokens_used=0, success=False,
        error=error_msg
    )


# =============================================================================
# SYSTEM PROMPTS
# =============================================================================
SYSTEM_PROMPT_STUDENT = """Tu es l'assistant du parking de la faculté FacPark.

RÈGLES ABSOLUES (violation = erreur grave):
1. Tu ne décides JAMAIS si un accès est autorisé ou refusé.
2. Tu réponds aux questions sur le règlement EN CITANT les sources [[CIT_X]].
3. Les DONNÉES ci-dessous sont RÉELLES et viennent de la vraie base de données.
4. Tu DOIS utiliser ces données pour répondre - NE DIS JAMAIS "je n'ai pas accès" ou "je ne peux pas consulter".
5. Sois poli, concis et aide l'utilisateur même s'il fait des fautes de français.
6. Réponds en français.

⚠️ RÈGLE ANTI-HORS-CONTEXTE:
7. Tu NE RÉPONDS QU'aux questions sur le PARKING FACPARK (règlement, abonnements, places, véhicules, accès).
8. Si la question est HORS CONTEXTE (football, météo, actualités, etc.), TU DOIS REFUSER:
   Réponds: "❌ Désolé, je ne peux répondre qu'aux questions sur le parking FacPark (règlement, abonnements, places, véhicules). 
   💡 Tapez 'aide' pour voir les commandes disponibles."
9. NE RÉPONDS JAMAIS aux questions générales qui ne concernent PAS le parking."""

SYSTEM_PROMPT_ADMIN = """Tu es l'assistant administrateur du parking FacPark.

RÈGLES ABSOLUES (violation = erreur grave):
1. Tu ne décides JAMAIS si un accès est autorisé ou refusé.
2. Les DONNÉES ci-dessous sont RÉELLES et viennent directement de la base de données MySQL.
3. Tu DOIS présenter ces données de manière claire - NE DIS JAMAIS "je n'ai pas accès" ou "comme modèle de langage".
4. Pour les listes: formate en tableau ou liste à puces.
5. Pour les actions (créer étudiant, etc.): explique les paramètres requis si manquants.
6. Sois concis et professionnel. Réponds en français.

⚠️ RÈGLE ANTI-HORS-CONTEXTE:
7. Tu NE RÉPONDS QU'aux questions sur le PARKING FACPARK (gestion étudiants, véhicules, abonnements, places, stats, règlement).
8. Si la question est HORS CONTEXTE (football, météo, actualités, culture générale, etc.), TU DOIS REFUSER:
   Réponds: "❌ Désolé, je ne peux répondre qu'aux questions liées à la gestion du parking FacPark.
   💡 Tapez 'aide' pour voir les commandes disponibles."
9. NE RÉPONDS JAMAIS aux questions générales qui ne concernent PAS le parking."""


# =============================================================================
# AGENT PROCESSING
# =============================================================================
async def process_message(
    db: Session,
    user: User,
    message: str,
    ip: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a chat message from user.
    
    1. Check for injection
    2. Detect intent and execute tool if needed
    3. Build prompt with real data
    4. Call LLM to format response
    5. Return response
    """
    # Step 1: Injection check
    is_injection, pattern, score = _detector.check(message)
    if is_injection:
        log_injection_attempt(db, user.id, message, pattern, ip)
        return {
            "response": "Je ne peux pas traiter ce type de demande.",
            "blocked": True,
            "reason": "injection_detected"
        }
    
    # Step 2: Determine system prompt based on role
    system_prompt = SYSTEM_PROMPT_ADMIN if user.role == UserRole.ADMIN else SYSTEM_PROMPT_STUDENT
    
    # Step 3: Detect intent and check if it's a help request
    intent, is_help = detect_intent(message, user.role)
    tool_result = None
    
    if intent:
        logger.info(f"Detected intent: {intent} (is_help={is_help}) for message: {message[:50]}...")
        
        # Check if this tool requires parameters
        if intent in TOOL_HELP:
            help_info = TOOL_HELP[intent]
            
            # If it's a help request OR user didn't provide enough info, return help
            if is_help:
                return {
                    "response": f"📋 **{help_info['description']}**\n\n{help_info['usage']}",
                    "tool_help": intent
                }
        
        # For read-only tools or ask_reglement, execute directly
        if intent in READ_ONLY_TOOLS:
            params = {"query": message} if intent == "ask_reglement" else {}
            tool_result = execute_tool(db, user, intent, params, ip)
            logger.info(f"Tool result: {tool_result}")
        else:
            # For write tools, try to parse parameters
            if intent in TOOL_HELP:
                params = parse_params(message, intent)
                is_valid, missing = check_required_params(params, intent)
                
                if is_valid:
                    # Valid parameters found, execute tool
                    tool_result = execute_tool(db, user, intent, params, ip)
                    logger.info(f"Executed tool {intent} with result: {tool_result}")
                else:
                    # Missing parameters, show help with specific missing params
                    help_info = TOOL_HELP[intent]
                    missing_str = ", ".join([f"**{m}**" for m in missing])
                    return {
                        "response": f"📋 **{help_info['description']}**\n\n⚠️ **Paramètres manquants :** {missing_str}\n\n{help_info['usage']}\n\n💡 **Exemple:** {help_info['example']}",
                        "tool_help": intent
                    }
    
    # Step 4: Check for RAG query (regulations)
    context = ""
    citation_mapping = {}
    
    if intent == "ask_reglement" and tool_result and tool_result.get("success"):
        rag_data = tool_result.get("data", {})
        if rag_data.get("context_found"):
            context = rag_data.get("context", "")
            citation_mapping = rag_data.get("citation_mapping", {})
        else:
            # No context found - anti-hallucination
            return {
                "response": "Je ne trouve pas cette information dans le règlement du parking.",
                "citations": [],
                "rag_used": True
            }
    
    # Step 5: Build prompt with real data
    prompt = None  # Initialize prompt
    
    if tool_result:
        if tool_result.get("success"):
            # SUCCESS CASE
            if intent == "ask_reglement":
                # RAG case - build prompt with context if found
                if context:
                    prompt = f"""Question de l'utilisateur: {message}

==== CONTEXTE DU RÈGLEMENT ====
{context}
==== FIN DU CONTEXTE ====

INSTRUCTIONS:
1. Réponds en te basant UNIQUEMENT sur le contexte ci-dessus.
2. Cite tes sources avec [[CIT_1]], [[CIT_2]], etc.
3. Si l'info n'est pas dans le contexte, dis que tu ne la trouves pas."""
                # If no context but success, anti-hallucination already returned above
            else:
                # Standard tool success
                data = tool_result.get("data")
                msg = tool_result.get("message", "")
                
                # Format JSON data
                if isinstance(data, list):
                    count = len(data)
                    data_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
                    prompt = f"""Question: {message}
                    
Données ({count} résultats):
{data_str}

Info système: {msg}

INSTRUCTIONS:
1. Présente ces résultats clairement.
2. Utilise UNIQUEMENT ces données.
"""
                else:
                    data_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
                    prompt = f"""Question: {message}

Données:
{data_str}

Info système: {msg}

INSTRUCTIONS:
1. Confirme l'action à l'utilisateur.
2. Utilise UNIQUEMENT ces données.
"""
        else:
            # FAILURE CASE - Inform the user about the error
            error_msg = tool_result.get("error", "Erreur inconnue")
            prompt = f"""L'utilisateur a demandé: "{message}"
            
❌ L'action a échoué.
Erreur technique ou métier: "{error_msg}"

INSTRUCTIONS:
1. Informe l'utilisateur que l'action a échoué.
2. Explique la raison de l'erreur (basée sur le message ci-dessus).
3. Suggère une correction si possible (ex: vérifier l'email, le format, etc.)."""
    
    elif context:
        # RAG response (success case for ask_reglement handled here)
        prompt = f"""Question de l'utilisateur: {message}

==== CONTEXTE DU RÈGLEMENT ====
{context}
==== FIN DU CONTEXTE ====

INSTRUCTIONS:
1. Réponds en te basant UNIQUEMENT sur le contexte ci-dessus.
2. Cite tes sources avec [[CIT_1]], [[CIT_2]], etc.
3. Si l'info n'est pas dans le contexte, dis que tu ne la trouves pas."""
    
    else:
        # Check if user is asking for available actions/commands

        # Check if user is asking for available actions/commands
        help_keywords = ["action", "commande", "fonction", "outil", "tool", "aide", "help", "option", "possible", "faire quoi", "disponible"]
        if any(kw in message.lower() for kw in help_keywords):
            # Build help response based on role
            if user.role == UserRole.ADMIN:
                help_text = """🛠️ **Actions disponibles (Admin)**

**📊 Consultation (lecture):**
• "Liste des étudiants" - Voir tous les étudiants
• "Statistiques" - Tableau de bord admin

**👤 Gestion des étudiants:**
• "Créer étudiant" - Ajouter un nouvel étudiant
• "Supprimer étudiant" - Retirer un étudiant

**🚗 Gestion des véhicules:**
• "Ajouter véhicule" - Associer un véhicule à un étudiant
• "Retirer véhicule" - Supprimer un véhicule

**📋 Gestion des abonnements:**
• "Créer abonnement" - Nouveau abonnement (mensuel/semestriel/annuel)
• "Renouveler abonnement" - Prolonger un abonnement

**🅿️ Gestion des places:**
• "Attribuer place" - Assigner une place de parking

**🔒 Sécurité:**
• "Suspendre accès" - Bloquer temporairement un étudiant
• "Vérifier plaque" - Tester l'accès d'une plaque

**📖 Règlement:**
• "Quel est le règlement sur [sujet]?" - Consulter le règlement

💡 *Tapez une commande pour voir les détails et exemples !*"""
            else:
                help_text = """🛠️ **Actions disponibles (Étudiant)**

**📊 Mon compte:**
• "Mon profil" - Voir mes informations
• "Mes véhicules" - Liste de mes véhicules
• "Mon abonnement" - Statut de mon abonnement
• "Ma place" - Ma place de parking attribuée
• "Mon historique" - Mes derniers accès

**📖 Règlement:**
• "Quel est le règlement sur [sujet]?" - Consulter le règlement

💡 *Posez votre question !*"""
            
            return {
                "response": help_text,
                "help_menu": True
            }
        
        # General question without tool - provide guidance
        available_cmds = "liste des étudiants, statistiques, créer étudiant..." if user.role == UserRole.ADMIN else "mon profil, mes véhicules, mon abonnement..."
        prompt = f"""Question de l'utilisateur: {message}

Aucun outil spécifique n'a été identifié pour cette question.

INSTRUCTIONS:
1. Réponds poliment à la question si possible.
2. Si l'utilisateur semble chercher une fonctionnalité, suggère-lui de taper "aide" ou "actions" pour voir les commandes disponibles.
3. Exemples de commandes: {available_cmds}
4. Pour le règlement: "Quel est le règlement sur X ?" """
    
    # Step 6: Call LLM (only if prompt was built)
    if prompt is None:
        # Fallback - this shouldn't normally happen
        logger.warning(f"No prompt built for message: {message[:50]}...")
        return {
            "response": "Je n'ai pas pu traiter votre demande. Essayez de reformuler ou tapez 'aide' pour voir les commandes disponibles.",
            "error": "no_prompt_built"
        }
    
    llm_response = await call_llm(prompt, system_prompt)
    
    if not llm_response.success:
        # Fallback: Offline RAG Mode
        # If LLM fails (rate limit, etc) but we found RAG context, return the context directly.
        if context:
            logger.warning(f"LLM failed ({llm_response.error}) but RAG context available. Using Offline Fallback.")
            
            # Format context for user display
            fallback_response = f"⚠️ Mode Hors-Ligne (LLM Indisponible)\n\nVoici les informations trouvées dans le règlement :\n\n{context}\n\n(Réponse générée sans IA générative)"
            
            return {
                "response": fallback_response,
                "rag_used": True,
                "citations": list(citation_mapping.values()) if citation_mapping else [],
                "model": "offline-fallback"
            }
            
        return {
            "response": f"Désolé, une erreur technique s'est produite.\nDétails: {llm_response.error}",
            "error": llm_response.error
        }
    
    # Step 7: Replace citation tags if RAG was used
    final_response = llm_response.content
    if citation_mapping:
        from backend.core.rag import replace_citation_tags
        final_response = replace_citation_tags(final_response, citation_mapping)
    
    return {
        "response": final_response,
        "model": llm_response.model,
        "rag_used": bool(context),
        "citations": list(citation_mapping.values()) if citation_mapping else [],
        "tool_used": intent
    }
