"""
FacPark - Populate Parking Slots
Creates 100 parking slots in the database:
- Zone A: A-01 to A-40 (40 slots)
- Zone B: B-01 to B-40 (40 slots)
- Zone C: C-01 to C-20 (20 slots)
"""

import sys
import os

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.db.session import SessionLocal
from backend.db.models import Slot
from sqlalchemy import func

def populate_slots():
    """Create parking slots if they don't exist."""
    db = SessionLocal()
    
    try:
        # Check if slots already exist
        existing_count = db.query(func.count(Slot.id)).scalar()
        if existing_count > 0:
            print(f"ℹ️  {existing_count} places existent déjà dans la base de données.")
            
            response = input("Voulez-vous les recréer? (toutes les places seront supprimées) [y/N]: ")
            if response.lower() != 'y':
                print("Opération annulée.")
                return
            
            # Delete all slots
            print("🗑️  Suppression des places existantes...")
            db.query(Slot).delete()
            db.commit()
        
        print("📦 Création des places de parking...")
        
        slots_created = 0
        
        # Zone A: A-01 to A-40
        print("  Zone A: A-01 à A-40 (40 places)")
        for i in range(1, 41):
            slot_code = f"A-{i:02d}"
            slot = Slot(code=slot_code, zone="A", is_available=True)
            db.add(slot)
            slots_created += 1
        
        # Zone B: B-01 to B-40
        print("  Zone B: B-01 à B-40 (40 places)")
        for i in range(1, 41):
            slot_code = f"B-{i:02d}"
            slot = Slot(code=slot_code, zone="B", is_available=True)
            db.add(slot)
            slots_created += 1
        
        # Zone C: C-01 to C-20
        print("  Zone C: C-01 à C-20 (20 places)")
        for i in range(1, 21):
            slot_code = f"C-{i:02d}"
            slot = Slot(code=slot_code, zone="C", is_available=True)
            db.add(slot)
            slots_created += 1
        
        db.commit()
        
        print(f"\n✅ {slots_created} places créées avec succès!")
        print("\nRépartition:")
        print(f"  - Zone A: 40 places")
        print(f"  - Zone B: 40 places")
        print(f"  - Zone C: 20 places")
        print(f"  - TOTAL: {slots_created} places")
        
        # Verify
        total_in_db = db.query(func.count(Slot.id)).scalar()
        available = db.query(func.count(Slot.id)).filter(Slot.is_available == True).scalar()
        print(f"\nVérification:")
        print(f"  - Total en BD: {total_in_db}")
        print(f"  - Disponibles: {available}")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=" * 60)
    print("  FacPark - Peuplement des Places de Parking")
    print("=" * 60)
    print()
    
    populate_slots()
