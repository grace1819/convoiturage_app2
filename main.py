from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional

from requests import Session
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from sqlalchemy.exc import SQLAlchemyError

# --- Base de données ---
DATABASE_URL = "sqlite:///./covoiturage.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
app = FastAPI()

# --- Modèles DB ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

class Ride(Base):
    __tablename__ = "rides"
    id = Column(Integer, primary_key=True, index=True)
    departure = Column(String)  # Départ du trajet
    destination = Column(String)
    date = Column(DateTime)  # Date du trajet
    price = Column(Integer)
    seats_available = Column(Integer)  # Nombre de places disponibles

class Reservation(Base):
    __tablename__ = "reservations"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ride_id = Column(Integer, ForeignKey("rides.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    ride = relationship("Ride")

# Crée toutes les tables
Base.metadata.create_all(bind=engine)

# --- Schémas Pydantic ---
class UserCreate(BaseModel):
    name: str

class RideCreate(BaseModel):
    departure: str  # Utiliser 'departure' pour la localisation de départ
    destination: str
    date: datetime  # Utiliser 'date' pour le départ
    price: int
    seats_available: int  # Nombre de places disponibles

class ReservationCreate(BaseModel):
    user_id: int
    ride_id: int

# --- Fonction pour obtenir la session DB ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Routes API ---

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'application de covoiturage!"}

@app.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    try:
        db_user = User(name=user.name)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la création de l'utilisateur")

@app.post("/rides/")
def create_ride(ride: RideCreate, db: Session = Depends(get_db)):
    try:
        db_ride = Ride(**ride.dict())  # Utilisation du dictionnaire des données
        db.add(db_ride)
        db.commit()
        db.refresh(db_ride)
        return db_ride
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de la création du trajet")

@app.get("/rides/search/")
def search_rides(destination: str, date: str, db: Session = Depends(get_db)):
    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d")  # Conversion de la date en datetime
        next_day = date_obj + timedelta(days=1)
        rides = db.query(Ride).filter(Ride.destination == destination, Ride.date >= date_obj, Ride.date < next_day).all()
        if not rides:
            raise HTTPException(status_code=404, detail="Aucun trajet trouvé pour cette destination à cette date.")
        return rides
    except SQLAlchemyError:
        raise HTTPException(status_code=500, detail="Erreur lors de la recherche des trajets")
    except ValueError:
        raise HTTPException(status_code=400, detail="Format de la date invalide, assurez-vous d'utiliser le format YYYY-MM-DD.")

@app.post("/reservations/")
def create_reservation(res: ReservationCreate, db: Session = Depends(get_db)):
    try:
        ride = db.query(Ride).filter(Ride.id == res.ride_id).first()
        if not ride:
            raise HTTPException(status_code=404, detail="Ride not found")

        if ride.seats_available < 1:
            raise HTTPException(status_code=400, detail="No available seats")

        ride.seats_available -= 1
        reservation = Reservation(user_id=res.user_id, ride_id=res.ride_id)
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        return reservation
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error creating reservation")


@app.delete("/reservations/{res_id}")
def cancel_reservation(res_id: int, db: Session = Depends(get_db)):
    try:
        reservation = db.query(Reservation).filter(Reservation.id == res_id).first()
        if not reservation:
            raise HTTPException(status_code=404, detail="Réservation introuvable")

        ride = reservation.ride
        now = datetime.utcnow()
        if ride.date - now > timedelta(hours=24):
            message = "Remboursement autorisé (annulation > 24h avant le départ)"
        else:
            message = "Annulation sans remboursement (moins de 24h)"

        ride.seats_available += 1
        db.delete(reservation)
        db.commit()
        return {"status": "Annulation effectuée", "remboursement": message}
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de l'annulation de la réservation")



