import json
from pathlib import Path

# Correct mapping based on reglement.txt content
FIXES = {
    "horaires": "Article 1",
    "ouvert": "Article 1",
    "dimanche": "Article 1",
    "voitures": "Article 5",
    "véhicules": "Article 5",
    "badge": "Article 6",  # Or Article 16 for documents
    "documents": "Article 16",
    "inscrire": "Article 16",
    "REF-": "Article 19",
    "sanctions": "Article 14",
    "prête": "Article 6", # R6 refers to Article 14, Article 6 forbids it
    "surveillé": "Article 11",
    "vol": "Article 12",
    "vitesse": "Article 13",
    "rouler": "Article 13",
    "renouveler": "Article 17",
    "visiteurs": "Article 10",
    "étudiants": "Article 16", # Or Preamble
    "moto": "Article 5", # Not explicitly mentioned but implies vehicles
    "deux-roues": "Article 5",
    "plaque": "Article 7", # Or Article 8/19
    "sale": "Article 7", # Implicit
    "handicapés": "Article 4", # Zones A/B/C? Not mentioned explicitly? Let's check.
    "zone": "Article 4",
    "ferme": "Article 1",
    "nuit": "Article 1", # Or 11 (surveillance)
    "fourrière": "Article 14", # Sanctions
    "payer": "Article 16",
    "tarif": "Annexe A",
    "combien": "Annexe A",
    "perdu": "Article 18", # Signalement
    "remplacement": "Article 9", # Véhicule remplacement? Badge replacement not explicit in text shown?
    "prof": "Préambule",
    "administratif": "Préambule",
    "circulation": "Article 13",
    "priorité": "Article 13",
    "klaxon": "Article 13"
}

# Specific manual overrides
MANUAL_FIXES = {
    "C'est quoi les horaires ?": "Article 1",
    "Quand est-ce que le parking est ouvert ?": "Article 1",
    "Est-ce que je peux me garer le dimanche ?": "Article 1",
    "Comment obtenir un badge ?": "Article 16", # Inscription
    "C'est quoi la procédure pour le badge d'accès ?": "Article 16",
    "Quels sont les documents pour l'abonnement ?": "Article 16",
    "Il faut quoi pour s'inscrire ?": "Article 16",
    "C'est quoi le code REF-04 ?": "Article 19",
    "Pourquoi mon accès est refusé avec REF-04 ?": "Article 19",
    "Quelles sont les sanctions si je triche ?": "Article 14",
    "Je risque quoi si je prête mon badge ?": "Article 14", # Or Article 6
    "Est-ce que le parking est surveillé ?": "Article 11",
    "Qui est responsable en cas de vol ?": "Article 12",
    "C'est quoi la vitesse limite ?": "Article 13",
    "Je peux rouler vite ?": "Article 13",
    "Refus REF-05 ça veut dire quoi ?": "Article 19",
    "Comment renouveler mon abonnement ?": "Article 17",
    "Les visiteurs ont le droit d'entrer ?": "Article 10",
    "C'est réservé aux étudiants ?": "Préambule",
    "Je peux garer ma moto ?": "Article 5", # Assumed
    "Les deux-roues sont acceptés ?": "Article 5",
    "C'est quoi REF-02 ?": "Article 19",
    "Plaque non reconnue, que faire ?": "Article 19", # REF-01
    "Ma plaque est sale, ça marche ?": "Article 19", # REF-01
    "Il y a des places handicapés ?": "Article 4", # Zone A maybe? Or Plan
    "C'est quoi la zone A ?": "Article 4",
    "Où se garer en zone B ?": "Article 4",
    "Le parking ferme à quelle heure ?": "Article 1",
    "C'est ouvert la nuit ?": "Article 1",
    "Je peux laisser ma voiture la nuit ?": "Article 1",
    "Sanction pour stationnement gênant ?": "Article 14",
    "La fourrière peut intervenir ?": "Article 14",
    "Comment payer l'abonnement ?": "Article 16", # Mentioned in 16
    "Tarif mensuel ?": "Annexe A", # Changed from Annexe Tarifs to Annexe A
    "C'est combien pour un an ?": "Annexe A",
    "J'ai perdu mon badge": "Article 18", # Signalement pb
    "Ruban adhésif sur plaque ?": "Article 6",
    "Je peux avoir 2 places ?": "Article 4",
    "C'est limité à une place par personne ?": "Article 4",
    "REF-07 c'est quoi ?": "Article 19",
    "Pourquoi accès interdit REF-07 ?": "Article 19",
    "Je suis prof, je peux entrer ?": "Préambule",
    "Accès personnel administratif": "Préambule",
    "Mon abonnement est fini": "Article 3", # Expiration
    "Délai de renouvellement": "Article 3", # Grace period
    "C'est quoi les règles de circulation ?": "Article 13",
    "Priorité à droite dans le parking ?": "Article 13",
    "Klaxon interdit ?": "Article 13"
}

source_path = Path("backend/eval/questions.jsonl")
output_path = source_path # Overwrite

new_questions = []
count_fixed = 0

with open(source_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip(): continue
        q = json.loads(line)
        query = q["query"]
        old_source = q["source"]
        
        # Apply fix
        new_source = old_source
        if query in MANUAL_FIXES:
            new_source = MANUAL_FIXES[query]
        
        q["source"] = new_source
        if new_source != old_source:
            count_fixed += 1
            # print(f"Fixed: {query} -> {old_source} to {new_source}")
            
        new_questions.append(q)

with open(output_path, "w", encoding="utf-8") as f:
    for q in new_questions:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")

print(f"Fixed {count_fixed} questions in {output_path}")
