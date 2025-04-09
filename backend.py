from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from datetime import datetime, timedelta

from pydantic import BaseModel

app = Flask(__name__)

# Configuration de la base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///covoiturage.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'your_secret_key'

# Initialisation des extensions
db = SQLAlchemy(app)
ma = Marshmallow(app)
jwt = JWTManager(app)


# Modèles de données

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(100), nullable=False)


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    departure_location = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)


class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    seats_reserved = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Schemas pour sérialisation

class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User


class TripSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Trip


class ReservationSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Reservation


class RideCreate(BaseModel):
    departure_location: str  # Anciennement 'departure'
    destination: str
    departure_time: datetime  # Anciennement 'date'
    price: int
    available_seats: int  # Anciennement 'seats_available'

    class Config:
        # Assurez-vous que les noms des champs dans le modèle Pydantic correspondent à ceux dans la requête
        alias = {
            'departure_location': 'departure',
            'departure_time': 'date',
            'available_seats': 'seats_available'
        }




# Routes de l'API

# Création d'un utilisateur
@app.route('/users/', methods=['POST'])
def create_user():
    data = request.get_json()
    new_user = User(name=data['name'], email=data['email'], password_hash=data['password_hash'])
    db.session.add(new_user)
    db.session.commit()
    return user_schema.jsonify(new_user)


# Connexion d'un utilisateur et génération d'un token
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if user and user.password_hash == data['password_hash']:
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token)
    return jsonify({"message": "Invalid credentials"}), 401


# Recherche de trajets
@app.route('/trips/', methods=['GET'])
def get_trips():
    destination = request.args.get('destination')
    date = request.args.get('date')

    if destination and date:
        trips = Trip.query.filter(Trip.destination.like(f'%{destination}%'),
                                  Trip.departure_time >= datetime.strptime(date, '%Y-%m-%d')).all()
    else:
        trips = Trip.query.all()

    return trip_schema.jsonify(trips, many=True)


# Réservation d'un trajet

@app.route('/reservations/', methods=['POST'])
@jwt_required()
def create_reservation():
    data = request.get_json()
    user_id = data.get('user_id')
    trip_id = data.get('trip_id')
    seats_reserved = data.get('seats_reserved')

    if not user_id or not trip_id or not seats_reserved:
        return jsonify({"message": "Missing required fields"}), 400

    trip = Trip.query.get(trip_id)
    if not trip:
        return jsonify({"message": "Trip not found"}), 404

    if trip.available_seats < seats_reserved:
        return jsonify({"message": "Not enough seats available"}), 400

    trip.available_seats -= seats_reserved
    new_reservation = Reservation(user_id=user_id, trip_id=trip_id, seats_reserved=seats_reserved)
    db.session.add(new_reservation)
    db.session.commit()

    return reservation_schema.jsonify(new_reservation), 201



# Annulation d'une réservation avec remboursement si plus de 24h avant
@app.route('/reservations/<int:id>/cancel', methods=['DELETE'])
@jwt_required()
def cancel_reservation(id):
    reservation = Reservation.query.get_or_404(id)
    trip = Trip.query.get(reservation.trip_id)
    if trip.departure_time - timedelta(hours=24) > datetime.utcnow():
        db.session.delete(reservation)
        trip.available_seats += reservation.seats_reserved
        db.session.commit()
        return jsonify({"message": "Reservation cancelled and refunded"}), 200
    return jsonify({"message": "No refund available"}), 400


# Initialiser la base de données
@app.before_first_request
def create_tables():
    db.create_all()


# Instances des schémas
user_schema = UserSchema()
trip_schema = TripSchema()
reservation_schema = ReservationSchema()

if __name__ == '__main__':
    app.run(debug=True)
