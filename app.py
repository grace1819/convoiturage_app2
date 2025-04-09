import streamlit as st
import requests
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Covoiturage", layout="centered")
st.title("🚗 Plateforme de Covoiturage")

# Menu de navigation
menu = st.sidebar.selectbox("Navigation", ["Créer un utilisateur", "Créer un trajet", "Chercher un trajet", "Réserver",
                                           "Annuler une réservation"])

# Créer un utilisateur
if menu == "Créer un utilisateur":
    st.header("👤 Créer un utilisateur")
    name = st.text_input("Nom")
    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Créer"):
        if name and email and password:
            r = requests.post(f"{API_URL}/users/", json={"name": name, "email": email, "password_hash": password})
            if r.status_code == 200:
                st.success(f"Utilisateur créé : {r.json()}")
            else:
                st.error(f"Erreur : {r.json()['detail']}")
        else:
            st.warning("Veuillez remplir tous les champs.")

# Créer un trajet
elif menu == "Créer un trajet":
    st.header("🛣 Créer un trajet")
    departure = st.text_input("Départ")
    destination = st.text_input("Destination")
    date = st.date_input("Date")
    time = st.time_input("Heure")
    full_datetime = datetime.combine(date, time)
    price = st.number_input("Prix (€)", min_value=0)
    seats = st.number_input("Places disponibles", min_value=1)

    if st.button("Ajouter le trajet"):
        if departure and destination and price > 0 and seats > 0:
            data = {
                "departure_location": departure,
                "destination": destination,
                "departure_time": full_datetime.isoformat(),
                "price": price,
                "available_seats": seats
            }
            r = requests.post(f"{API_URL}/rides/", json=data)
            if r.status_code == 200:
                st.success(f"Trajet ajouté : {r.json()}")
            else:
                st.error(f"Erreur : {r.json()['detail']}")
        else:
            st.warning("Veuillez remplir tous les champs correctement.")

# Chercher un trajet
elif menu == "Chercher un trajet":
    st.header("🔍 Recherche de trajets")
    destination = st.text_input("Destination")
    date = st.date_input("Date du trajet", value=datetime.today())

    if st.button("Rechercher"):
        if destination:
            r = requests.get(f"{API_URL}/rides/search/",
                             params={"destination": destination, "date": date.strftime("%Y-%m-%d")})
            if r.status_code == 200:
                results = r.json()
                if results:
                    st.write("Trajets trouvés :")
                    for ride in results:
                        st.write(
                            f"🛣 {ride['departure_location']} ➡ {ride['destination']} - 🗓 {ride['departure_time']} - 💶 {ride['price']}€ - 🚘 Places restantes : {ride['available_seats']}")
                else:
                    st.warning("Aucun trajet trouvé.")
            else:
                st.error(f"Erreur lors de la recherche : {r.json()['detail']}")
        else:
            st.warning("Veuillez entrer une destination.")

# Réserver un trajet
elif menu == "Réserver":
    st.header("📩 Réserver une place")
    user_id = st.number_input("ID Utilisateur", min_value=1)
    ride_id = st.number_input("ID Trajet", min_value=1)

    if st.button("Réserver"):
        if user_id and ride_id:
            r = requests.post(f"{API_URL}/reservations/", json={"user_id": user_id, "ride_id": ride_id})
            if r.status_code == 200:
                st.success("Réservation réussie !")
            else:
                st.error(f"Erreur : {r.json()['detail']}")
        else:
            st.warning("Veuillez entrer un ID utilisateur et un ID de trajet valides.")

# Annuler une réservation
elif menu == "Annuler une réservation":
    st.header("❌ Annuler une réservation")
    res_id = st.number_input("ID Réservation", min_value=1)

    if st.button("Annuler"):
        if res_id:
            r = requests.delete(f"{API_URL}/reservations/{res_id}")
            if r.status_code == 200:
                res = r.json()
                st.success(f"{res['status']} - {res['remboursement']}")
            else:
                st.error(f"Erreur : {r.json()['detail']}")
        else:
            st.warning("Veuillez entrer un ID de réservation valide.")


