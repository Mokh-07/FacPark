"""
Script pour activer l'abonnement et la place pour un véhicule.
Usage: python backend/scripts/activate_subscription.py "190 تونس 2765"
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import date, timedelta
from backend.db.session import SessionLocal
from backend.db.models import Vehicle, Subscription, SlotAssignment, Slot, SubscriptionType

def activate_vehicle(plate: str):
    """Active l'abonnement et attribue une place pour un véhicule."""
    db = SessionLocal()
    try:
        # 1. Trouver le véhicule
        vehicle = db.query(Vehicle).filter(Vehicle.plate == plate).first()
        if not vehicle:
            print(f"❌ Véhicule '{plate}' non trouvé en BDD!")
            # Afficher les plaques disponibles
            all_vehicles = db.query(Vehicle).all()
            print("\n📋 Plaques enregistrées:")
            for v in all_vehicles:
                print(f"   - {v.plate}")
            return False
        
        user_id = vehicle.user_id
        print(f"✅ Véhicule trouvé: {vehicle.plate}")
        print(f"   User ID: {user_id}")
        print(f"   Marque: {vehicle.make or 'N/A'}, Modèle: {vehicle.model or 'N/A'}")
        
        # 2. Ajouter abonnement actif si nécessaire
        existing_sub = db.query(Subscription).filter(
            Subscription.user_id == user_id,
            Subscription.is_active == 1
        ).first()
        
        if not existing_sub:
            sub = Subscription(
                user_id=user_id,
                subscription_type=SubscriptionType.ANNUEL,
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365),
                is_active=1
            )
            db.add(sub)
            db.flush()
            print(f"✅ Abonnement ANNUEL créé (expire: {sub.end_date})")
        else:
            print(f"ℹ️  Abonnement existe déjà: {existing_sub.subscription_type.value} (expire: {existing_sub.end_date})")
        
        # 3. Attribuer une place si nécessaire
        existing_slot = db.query(SlotAssignment).filter(
            SlotAssignment.user_id == user_id,
            SlotAssignment.is_active == 1
        ).first()
        
        if not existing_slot:
            slot = db.query(Slot).filter(Slot.is_available == True).first()
            if slot:
                assignment = SlotAssignment(
                    user_id=user_id,
                    slot_id=slot.id,
                    is_active=1
                )
                db.add(assignment)
                slot.is_available = False
                print(f"✅ Place {slot.code} attribuée!")
            else:
                print("⚠️  Aucune place disponible!")
        else:
            slot = existing_slot.slot
            print(f"ℹ️  Place déjà attribuée: {slot.code if slot else 'N/A'}")
        
        db.commit()
        print("\n🎉 Terminé! Le véhicule devrait maintenant être ALLOW.")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # Default plate or from command line
    plate = sys.argv[1] if len(sys.argv) > 1 else "190 تونس 2765"
    print(f"\n🚗 Activation pour: {plate}\n" + "="*50)
    activate_vehicle(plate)
