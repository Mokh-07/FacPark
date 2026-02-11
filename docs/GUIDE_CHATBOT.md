# 🚀 GUIDE RAPIDE - Chatbot FacPark (Admin)
**Version**: 1.1  
**Pour**: Administrateurs du parking

---

## 📖 TABLE DES MATIÈRES

1. [Créer un étudiant](#1-créer-un-étudiant)
2. [Ajouter un véhicule](#2-ajouter-un-véhicule)
3. [Créer un abonnement](#3-créer-un-abonnement)
4. [Attribuer une place](#4-attribuer-une-place)
5. [Vérifier l'accès (test)](#5-vérifier-laccès)
6. [Suspendre un accès](#6-suspendre-un-accès)
7. [Lister les places](#7-lister-les-places-de-parking-)
8. [Consulter les infos](#8-consulter-les-infos)
9. [Supprimer](#9-supprimer)

---

## 1️⃣ CRÉER UN ÉTUDIANT

### Format structuré (RECOMMANDÉ) ✅
```
créer étudiant email=jean.dupont@fac.tn nom="Jean Dupont" password=SecurePass123
```

### Format naturel (fonctionne aussi)
```
créer étudiant jean.dupont@fac.tn Jean Dupont SecurePass123
```

### ⚠️ IMPORTANT
- Le **password** est obligatoire pour que l'étudiant puisse se connecter
- Si omis, le système utilise `changeme123` par défaut

### ✅ Résultat attendu
```
L'étudiant 'Jean Dupont' avec l'adresse e-mail 'jean.dupont@fac.tn' 
a été créé avec succès. Votre identifiant est 28.
```

### 🧪 Test de validation
**LOGIN**: Vérifier que l'étudiant peut se connecter avec le password fourni.

---

## 2️⃣ AJOUTER UN VÉHICULE

### Syntaxe
```
ajouter véhicule 155 تونس 8899 à jean.dupont@fac.tn
```

### Variantes acceptées
```
ajouter plaque 155 تونس 8899 étudiant jean.dupont@fac.tn
```

### ⚠️ Limites
- **Maximum 3 véhicules** par étudiant (trigger MySQL)
- Si limite atteinte → Erreur explicite

### ✅ Résultat attendu
```
Véhicule '155 تونس 8899' ajouté à jean.dupont@fac.tn. 
Identifiant: 16
```

---

## 3️⃣ CRÉER UN ABONNEMENT

### Syntaxe
```
créer abonnement mensuel pour jean.dupont@fac.tn
```

### Types d'abonnement
| Mot-clé | Anglais | Durée |
|---------|---------|-------|
| `mensuel` | `monthly` | 30 jours |
| `semestriel` | `semester` | 180 jours |
| `annuel` | `annual` | 365 jours |

### Variantes acceptées
```
Créer abonnement Mensuel pour jean.dupont@fac.tn  ← Majuscules OK
abonner jean.dupont@fac.tn type semestriel  ← Ordre flexible
créer abonnement annual jean.dupont@fac.tn  ← Anglais OK
```

### ⚠️ IMPORTANT (NOUVEAU)
➤ Un **véhicule** doit être enregistré AVANT de créer l'abonnement
➤ Si pas de véhicule → Erreur avec solution:

```
❌ Impossible de créer un abonnement pour jean.dupont@fac.tn.

⚠️ Raison: Aucun véhicule enregistré.

✅ Solution: Ajoutez d'abord un véhicule:
   'ajouter véhicule 123 تونس 4567 à jean.dupont@fac.tn'
```

### ✅ Résultat attendu
```
✅ Abonnement MENSUEL créé pour jean.dupont@fac.tn.
Durée: 30 jours
Date d'expiration: 2026-02-20
```

---

## 4️⃣ ATTRIBUER UNE PLACE

### Syntaxe
```
attribuer place A-15 à jean.dupont@fac.tn
```

### Codes de places disponibles
- **Zone A**: A-01 à A-40 (40 places)
- **Zone B**: B-01 à B-40 (40 places)
- **Zone C**: C-01 à C-20 (20 places)

### ⚠️ Cas particuliers

#### Place déjà occupée
```
❌ La place 'B-12' est déjà occupée.

✅ Places disponibles (échantillon): A-05, A-12, B-03, B-08, C-01

💡 Conseil: Tapez 'statistiques' pour voir le nombre total de places disponibles.
```
→ Choisissez une alternative suggérée

#### Étudiant a déjà une place
```
❌ Impossible d'attribuer la place C-05 à jean.dupont@fac.tn.

⚠️ Raison: Cet étudiant a déjà une place active (B-12).

💡 Conseil: Libérez d'abord la place B-12.
```
→ Trigger MySQL empêche 2 places actives

### ✅ Résultat attendu
```
✅ Place A-15 attribuée avec succès à jean.dupont@fac.tn.
```

---

## 5️⃣ VÉRIFIER L'ACCÈS

### Syntaxe
```
vérifier plaque 155 تونس 8899
```

### Variantes
```
check accès 155 تونس 8899
tester plaque 155 تونس 8899
```

### ✅ Résultat si tout OK (ALLOW)
```
✅ ACCÈS AUTORISÉ

Plaque: 155 تونس 8899
Étudiant: Jean Dupont (jean.dupont@fac.tn)
Abonnement: MENSUEL (expire le 2026-02-20)
Place attribuée: A-15
Raison: REF-00 (Tous les critères sont remplis)
```

### ❌ Résultat si refusé (DENY)
```
❌ ACCÈS REFUSÉ

Plaque: 999 تونس 9999
Raison: REF-03 (Plaque non enregistrée dans le système)
```

### 📋 Codes de raison
| Code | Signification |
|------|--------------|
| `REF-00` | ✅ Accès autorisé |
| `REF-01` | ❌ Étudiant inactif |
| `REF-02` | ❌ Véhicule non trouvé |
| `REF-03` | ❌ Plaque non enregistrée |
| `REF-04` | ❌ Abonnement expiré |
| `REF-05` | ❌ Étudiant suspendu |
| `REF-06` | ❌ Pas de place attribuée |

---

## 6️⃣ SUSPENDRE UN ACCÈS

### Syntaxe
```
suspendre jean.dupont@fac.tn 7 jours raison=Stationnement dangereux
```

### Variantes
```
suspendre jean.dupont@fac.tn 7j raison=Non-respect du règlement
bloquer jean.dupont@fac.tn 14 jours motif=Récidive
```

### ✅ Résultat attendu
```
✅ L'accès de jean.dupont@fac.tn a été suspendu.
Durée: 7 jours
Expire le: 2026-01-28
Raison: Stationnement dangereux
```

### Vérification après suspension
```
Commande: vérifier plaque 155 تونس 8899
Résultat:
❌ ACCÈS REFUSÉ
Raison: REF-05 (Étudiant suspendu jusqu'au 2026-01-28)
Motif de suspension: Stationnement dangereux
```

---

## 7️⃣ LISTER LES PLACES DE PARKING 🆕

### Lister TOUTES les places (avec statut)
```
lister toutes les places
```

**Variantes acceptées**:
```
liste des places
voir les places
afficher les places
toutes les places
```

### ✅ Résultat attendu
```
📊 **Statistiques des places de parking:**

**Total:** 100 places
**Disponibles:** ✅ 99 places
**Occupées:** 🔴 1 places

**Zone A:** 40 places (✅ 40 disponibles, 🔴 0 occupées)
**Zone B:** 40 places (✅ 39 disponibles, 🔴 1 occupées)
**Zone C:** 20 places (✅ 20 disponibles, 🔴 0 occupées)
```

### Lister uniquement les places DISPONIBLES
```
places disponibles
```

**Variantes acceptées**:
```
liste des places disponibles
voir places disponibles
places libres
quelles places sont disponibles
```

### ✅ Résultat attendu
```
✅ **Places disponibles:** 99 place(s)

**Zone A:** A-01, A-02, A-03, A-04, ... A-40
**Zone B:** B-01, B-02, B-03, ... B-39, B-40
**Zone C:** C-01, C-02, ... C-20
```

### Filtrer par zone (optionnel)
```
lister places zone A
places disponibles zone B
```

### 💡 Cas d'usage
- **Avant d'attribuer une place** → Voir quelles places sont libres
- **Maintenance du parking** → Vue d'ensemble de l'occupation
- **Planification** → Combien de places disponibles par zone

---

## 8️⃣ CONSULTER LES INFOS

### Liste des étudiants
```
liste des étudiants
```
ou
```
tous les étudiants
```

### Statistiques globales
```
statistiques
```
ou
```
stats
```
ou
```
dashboard
```

**Résultat typique**:
```json
{
  "total_students": 12,
  "total_vehicles": 18,
  "active_subscriptions": 10,
  "available_slots": 85,
  "occupied_slots": 15,
  "total_slots": 100,
  "pending_suspensions": 2
}
```

### Consulter le règlement (RAG)
```
Quelles sont les sanctions en cas de stationnement interdit?
```

**Résultat** (avec citations):
```
Selon le règlement du parking FacPark [[CIT_1]]:

Les sanctions pour stationnement interdit incluent:
• 1ère infraction: Avertissement écrit
• 2ème infraction: Suspension de 7 jours
• 3ème infraction: Suspension d'un mois

[[CIT_1]]: Règlement parking - Article 12 (page 5)
```

---

## 9️⃣ SUPPRIMER

### Supprimer un étudiant
```
supprimer étudiant jean.dupont@fac.tn
```

⚠️ **ATTENTION**: Action irréversible !
- Supprime l'étudiant
- Supprime ses véhicules (cascade)
- Désactive son abonnement
- Libère sa place

### Supprimer un véhicule
```
supprimer véhicule 155 تونس 8899
```
ou
```
retirer plaque 155 تونس 8899
```

---

## 💡 CONSEILS D'UTILISATION

### Workflow complet recommandé
```
1. créer étudiant email=... nom="..." password=...
2. ajouter véhicule ... à ...
3. créer abonnement mensuel pour ...
4. attribuer place A-XX à ...
5. vérifier plaque ...  ← Test final
```

### En cas d'erreur
Le chatbot fournit maintenant:
- ✅ **Raison de l'erreur** claire
- ✅ **Solution concrète** avec exemple
- ✅ **Suggestions** basées sur votre saisie

**Exemple**:
```
Vous: Créer abonnement Mensuel pour john@fac.tn

Chatbot:
❌ Type d'abonnement 'Mensuel' invalide.

✅ Types acceptés:
• mensuel ou monthly → 30 jours

💡 Vouliez-vous dire 'mensuel' ?

💡 Exemple: 'créer abonnement mensuel pour john@fac.tn'
```

### Typos et variations
Le chatbot est flexible:
- **Majuscules/minuscules**: `Mensuel` → détecte `mensuel`
- **Ordre flexible**: `étudiant X pour abonnement` → OK
- **Mots-clés optionnels**: `créer` vs `crr` vs `ajouter`

---

## 🆘 AIDE CONTEXTUELLE

### Demander de l'aide
```
aide
```
ou
```
actions
```
ou
```
comment créer un abonnement?
```

Le chatbot affiche alors:
- Liste des commandes disponibles
- Exemples pour chaque action
- Paramètres requis

---

## 🧪 TESTS DE VALIDATION

Avant de déployer en production, testez:

1. ✅ **Créer un étudiant** → **Login fonctionne**
2. ✅ **Ajouter 3 véhicules** → **4e bloqué**
3. ✅ **Créer abonnement sans véhicule** → **Erreur claire**
4. ✅ **Attribuer place occupée** → **Alternatives suggérées**
5. ✅ **Suspendre + vérifier accès** → **DENY avec REF-05**

---

## 📞 SUPPORT

- **Documentation complète**: `AUDIT_COMPLET_FACPARK2.md`
- **Scénario de test**: `SCENARIO_TEST_COMPLET.md`
- **Correctifs appliqués**: `CORRECTIFS_APPLIQUES.md`

---

**Guide créé par**: Antigravity AI  
**Version**: 1.1  
**Date**: 2026-01-21
