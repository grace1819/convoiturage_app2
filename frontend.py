import streamlit as st
import requests
from datetime import datetime

from app import destination, departure, full_datetime, price, seats

API_URL = "http://localhost:5000"


# Authentification utilisateur
def login_user():
    st.title("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type='password')

    if st.button('Login'):
        response = requests.post(f"{API_URL}/login", json={"email": email, "password_hash": password})
        if response.status_code == 200:
            token = response.json().get('access_token')
            st.session_state.token = token
            st.success("Login successful!")
        else:
            st.error("Invalid credentials")


# Recherche de trajets
def search_trips():
    st.title("Search Trips")
    destination = st.text_input("Destination")
    date = st.date_input("Date", min_value=datetime.today())

    if st.button('Search'):
        response = requests.get(f"{API_URL}/trips/", params={"destination": destination, "date": date})
        if response.status_code == 200:
            trips = response.json()
            for trip in trips:
                st.write(f"Trip ID: {trip['id']}, Departure: {trip['departure_location']} -> {trip['destination']}, "
                         f"Seats: {trip['available_seats']}, Price: {trip['price']}")
        else:
            st.error("No trips found")


data = {
    "departure": departure,
    "destination": destination,
    "date": full_datetime.isoformat(),
    "price": price,
    "seats_available": seats
}
r = requests.post(f"{API_URL}/rides/", json=data)


# Réservation de trajet
def reserve_trip():
    st.title("Reserve a Trip")
    trip_id = st.number_input("Trip ID", min_value=1)
    seats_reserved = st.number_input("Seats Reserved", min_value=1)

    if st.button('Reserve'):
        if trip_id and seats_reserved:
            headers = {"Authorization": f"Bearer {st.session_state.token}"}
            response = requests.post(f"{API_URL}/reservations/",
                                     json={"user_id": 1, "trip_id": trip_id, "seats_reserved": seats_reserved},
                                     headers=headers)
            if response.status_code == 200:
                st.success("Reservation successful!")
            else:
                st.error(f"Error in reservation: {response.json()['message']}")
        else:
            st.error("Please fill all fields correctly.")







# Annulation de réservation
def cancel_reservation():
    st.title("Cancel Reservation")
    reservation_id = st.number_input("Reservation ID", min_value=1)

    if st.button('Cancel'):
        headers = {"Authorization": f"Bearer {st.session_state.token}"}
        response = requests.delete(f"{API_URL}/reservations/{reservation_id}/cancel", headers=headers)
        if response.status_code == 200:
            st.success("Reservation cancelled and refunded")
        else:
            st.error("Error in cancellation")


# Interface Streamlit
def main():
    if "token" not in st.session_state:
        login_user()
    else:
        action = st.radio("Choose an action", ("Search Trips", "Reserve Trip", "Cancel Reservation"))
        if action == "Search Trips":
            search_trips()
        elif action == "Reserve Trip":
            reserve_trip()
        elif action == "Cancel Reservation":
            cancel_reservation()


if __name__ == "__main__":
    main()
