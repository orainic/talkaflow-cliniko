"""
Cliniko API Test Suite
======================
Tests appointment booking, rescheduling, and cancellation via the Cliniko API.

Usage:
    python cliniko_api_test.py                  # Run interactive menu
    python cliniko_api_test.py --list-resources # List practitioners, types, businesses
    python cliniko_api_test.py --run-all        # Run full booking lifecycle test
"""

import os
import re
import requests
import json
import sys
from datetime import datetime, timedelta
from base64 import b64encode
from dotenv import load_dotenv

# ── Configuration (loaded from .env) ──────────────────────────────────────────

load_dotenv()

FULL_API_KEY = os.environ["CLINIKO_API_KEY"]
USER_AGENT = os.environ.get("CLINIKO_USER_AGENT", "TalkaFlow Cliniko Test")

# Parse shard from key suffix (e.g. "...-au5" -> shard="au5", raw key without suffix)
match = re.search(r"-([a-z]{2}\d+)$", FULL_API_KEY)
if match:
    SHARD = match.group(1)
    API_KEY = FULL_API_KEY[:match.start()]
else:
    SHARD = "au1"
    API_KEY = FULL_API_KEY

BASE_URL = f"https://api.{SHARD}.cliniko.com/v1"

# Cliniko uses HTTP Basic Auth: API key as username, empty password
auth_string = b64encode(f"{API_KEY}:".encode()).decode()

HEADERS = {
    "Authorization": f"Basic {auth_string}",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": USER_AGENT,
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def api_get(path, params=None):
    """GET request to Cliniko API."""
    url = f"{BASE_URL}{path}"
    print(f"  GET {url}")
    resp = requests.get(url, headers=HEADERS, params=params)
    print(f"  -> {resp.status_code}")
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"  Error: {resp.text[:500]}")
        return None


def api_post(path, data):
    """POST request to Cliniko API."""
    url = f"{BASE_URL}{path}"
    print(f"  POST {url}")
    print(f"  Payload: {json.dumps(data, indent=2)}")
    resp = requests.post(url, headers=HEADERS, json=data)
    print(f"  -> {resp.status_code}")
    if resp.status_code in (200, 201):
        return resp.json()
    else:
        print(f"  Error: {resp.text[:500]}")
        return None


def api_put(path, data):
    """PUT request to Cliniko API."""
    url = f"{BASE_URL}{path}"
    print(f"  PUT {url}")
    print(f"  Payload: {json.dumps(data, indent=2)}")
    resp = requests.put(url, headers=HEADERS, json=data)
    print(f"  -> {resp.status_code}")
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"  Error: {resp.text[:500]}")
        return None


def api_patch(path, data=None):
    """PATCH request to Cliniko API."""
    url = f"{BASE_URL}{path}"
    print(f"  PATCH {url}")
    if data:
        print(f"  Payload: {json.dumps(data, indent=2)}")
    resp = requests.patch(url, headers=HEADERS, json=data or {})
    print(f"  -> {resp.status_code}")
    if resp.status_code in (200, 204):
        return resp.json() if resp.content else True
    else:
        print(f"  Error: {resp.text[:500]}")
        return None


def api_delete(path):
    """DELETE request to Cliniko API."""
    url = f"{BASE_URL}{path}"
    print(f"  DELETE {url}")
    resp = requests.delete(url, headers=HEADERS)
    print(f"  -> {resp.status_code}")
    if resp.status_code == 204:
        return True
    else:
        print(f"  Error: {resp.text[:500]}")
        return None


def separator(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


# ── Resource Discovery ─────────────────────────────────────────────────────────

def list_practitioners():
    """List all practitioners."""
    separator("PRACTITIONERS")
    data = api_get("/practitioners")
    if data and "practitioners" in data:
        for p in data["practitioners"]:
            print(f"  ID: {p['id']} | {p.get('title', '')} {p['first_name']} {p['last_name']}")
        return data["practitioners"]
    return []


def list_appointment_types():
    """List all appointment types."""
    separator("APPOINTMENT TYPES")
    data = api_get("/appointment_types")
    if data and "appointment_types" in data:
        for at in data["appointment_types"]:
            print(f"  ID: {at['id']} | {at['name']} ({at['duration_in_minutes']} min)")
        return data["appointment_types"]
    return []


def list_businesses():
    """List all businesses/locations."""
    separator("BUSINESSES")
    data = api_get("/businesses")
    if data and "businesses" in data:
        for b in data["businesses"]:
            print(f"  ID: {b['id']} | {b.get('business_name', b.get('display_name', 'N/A'))}")
        return data["businesses"]
    return []


def list_patients(limit=10):
    """List patients."""
    separator("PATIENTS (first 10)")
    data = api_get("/patients", params={"per_page": limit})
    if data and "patients" in data:
        for p in data["patients"]:
            print(f"  ID: {p['id']} | {p['first_name']} {p['last_name']}")
        return data["patients"]
    return []


def create_test_patient():
    """Create a test patient for testing."""
    separator("CREATE TEST PATIENT")
    payload = {
        "first_name": "Test",
        "last_name": "Patient",
        "email": "test.patient@example.com",
    }
    result = api_post("/patients", payload)
    if result:
        print(f"  OK Created test patient ID: {result['id']}")
    return result


def list_appointments(status="upcoming"):
    """List appointments."""
    separator(f"APPOINTMENTS ({status})")
    if status == "cancelled":
        data = api_get("/individual_appointments/cancelled")
    else:
        data = api_get("/individual_appointments")
    if data and "individual_appointments" in data:
        for a in data["individual_appointments"]:
            patient_name = "N/A"
            print(f"  ID: {a['id']} | {a['starts_at']} | cancelled: {a.get('cancelled_at', 'No')}")
        return data["individual_appointments"]
    return []


# ── Appointment Operations ─────────────────────────────────────────────────────

def create_appointment(patient_id, practitioner_id, appointment_type_id, business_id, starts_at=None):
    """Create a new individual appointment."""
    separator("CREATE APPOINTMENT")

    if not starts_at:
        # Default: tomorrow at 10:00 AM
        tomorrow = datetime.now() + timedelta(days=1)
        starts_at = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")

    payload = {
        "starts_at": starts_at,
        "patient_id": patient_id,
        "practitioner_id": practitioner_id,
        "appointment_type_id": appointment_type_id,
        "business_id": business_id,
    }

    result = api_post("/individual_appointments", payload)
    if result:
        print(f"\n  OK Appointment created! ID: {result['id']}")
        print(f"    Starts: {result['starts_at']}")
        print(f"    Ends:   {result['ends_at']}")
    return result


def reschedule_appointment(appointment_id, new_starts_at):
    """Reschedule an appointment by updating its start time."""
    separator("RESCHEDULE APPOINTMENT")

    payload = {
        "starts_at": new_starts_at,
        "ends_at": None,  # Setting to null lets Cliniko auto-calculate from appointment type duration
    }

    result = api_put(f"/individual_appointments/{appointment_id}", payload)
    if result:
        print(f"\n  OK Appointment rescheduled! ID: {result['id']}")
        print(f"    New start: {result['starts_at']}")
        print(f"    New end:   {result['ends_at']}")
    return result


def cancel_appointment(appointment_id, reason_code=20, note="Cancelled via API test"):
    """
    Cancel an appointment.
    Reason codes:
      10 = Patient cancelled
      20 = Practitioner cancelled
      30 = Patient DNA (did not arrive)
      31 = Patient DNA (arrived late)
      40 = Patient cancelled (charged)
      50 = Other
      60 = COVID-19
    """
    separator("CANCEL APPOINTMENT")

    payload = {
        "cancellation_reason": reason_code,
        "cancellation_note": note,
    }

    result = api_patch(f"/individual_appointments/{appointment_id}/cancel", payload)
    if result:
        print(f"\n  OK Appointment {appointment_id} cancelled!")
    return result


def delete_appointment(appointment_id):
    """Permanently delete an appointment."""
    separator("DELETE APPOINTMENT")

    result = api_delete(f"/individual_appointments/{appointment_id}")
    if result:
        print(f"\n  OK Appointment {appointment_id} deleted!")
    return result


def get_appointment(appointment_id):
    """Get a single appointment's details."""
    separator("GET APPOINTMENT")
    result = api_get(f"/individual_appointments/{appointment_id}")
    if result:
        print(f"  ID:     {result['id']}")
        print(f"  Starts: {result['starts_at']}")
        print(f"  Ends:   {result['ends_at']}")
        print(f"  Cancel: {result.get('cancelled_at', 'No')}")
    return result


def check_conflicts(appointment_id):
    """Check if an appointment has scheduling conflicts."""
    separator("CHECK CONFLICTS")
    result = api_get(f"/individual_appointments/{appointment_id}/conflicts")
    if result:
        print(f"  Conflicts exist: {result.get('exist', 'unknown')}")
    return result


# ── Full Lifecycle Test ────────────────────────────────────────────────────────

def run_full_lifecycle():
    """Run a complete appointment lifecycle: create → reschedule → cancel."""
    separator("FULL APPOINTMENT LIFECYCLE TEST")

    # Step 1: Discover resources
    print("Step 1: Discovering available resources...\n")
    practitioners = list_practitioners()
    apt_types = list_appointment_types()
    businesses = list_businesses()
    patients = list_patients()

    if not all([practitioners, apt_types, businesses]):
        print("\n  FAIL Missing required resources. Cannot proceed.")
        print("    Make sure you have at least one practitioner, appointment type,")
        print("    and business in your Cliniko account.")
        return

    if not patients:
        print("\n  No patients found. Creating a test patient...")
        test_patient = create_test_patient()
        if test_patient:
            patients = [test_patient]
        else:
            print("  FAIL Could not create test patient.")
            return

    # Use first available of each
    practitioner_id = practitioners[0]["id"]
    apt_type_id = apt_types[0]["id"]
    business_id = businesses[0]["id"]
    patient_id = patients[0]["id"]

    print(f"\n  Using:")
    print(f"    Practitioner: {practitioners[0]['first_name']} {practitioners[0]['last_name']} (ID: {practitioner_id})")
    print(f"    Appt Type:    {apt_types[0]['name']} (ID: {apt_type_id})")
    print(f"    Business:     {businesses[0].get('business_name', 'N/A')} (ID: {business_id})")
    print(f"    Patient:      {patients[0]['first_name']} {patients[0]['last_name']} (ID: {patient_id})")

    # Step 2: Create appointment (tomorrow at 10:00)
    print("\n\nStep 2: Creating appointment...")
    tomorrow = datetime.now() + timedelta(days=1)
    start_time = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")
    appointment = create_appointment(patient_id, practitioner_id, apt_type_id, business_id, start_time)

    if not appointment:
        print("  FAIL Failed to create appointment. Stopping.")
        return

    apt_id = appointment["id"]

    # Step 3: Verify the appointment
    print("\n\nStep 3: Verifying appointment...")
    get_appointment(apt_id)

    # Step 4: Check for conflicts
    print("\n\nStep 4: Checking conflicts...")
    check_conflicts(apt_id)

    # Step 5: Reschedule (move to day after tomorrow at 14:00)
    print("\n\nStep 5: Rescheduling appointment...")
    day_after = datetime.now() + timedelta(days=2)
    new_time = day_after.replace(hour=14, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")
    reschedule_appointment(apt_id, new_time)

    # Step 6: Verify rescheduled appointment
    print("\n\nStep 6: Verifying rescheduled appointment...")
    get_appointment(apt_id)

    # Step 7: Cancel the appointment
    print("\n\nStep 7: Cancelling appointment...")
    cancel_appointment(apt_id, reason_code=20, note="Testing API - practitioner cancelled")

    # Step 8: Verify cancellation
    print("\n\nStep 8: Verifying cancellation...")
    get_appointment(apt_id)

    separator("LIFECYCLE TEST COMPLETE")
    print("  All steps completed. Check output above for any errors.\n")


# ── Interactive Menu ───────────────────────────────────────────────────────────

def interactive_menu():
    """Interactive menu for testing individual operations."""
    while True:
        print("\n" + "=" * 60)
        print("  CLINIKO API TEST MENU")
        print("=" * 60)
        print("  1. List practitioners")
        print("  2. List appointment types")
        print("  3. List businesses")
        print("  4. List patients")
        print("  5. List appointments")
        print("  6. List cancelled appointments")
        print("  7. Create appointment (interactive)")
        print("  8. Reschedule appointment")
        print("  9. Cancel appointment")
        print(" 10. Delete appointment")
        print(" 11. Get appointment details")
        print(" 12. Run full lifecycle test")
        print(" 13. Test API connection")
        print("  0. Exit")
        print()

        choice = input("  Choose an option: ").strip()

        if choice == "0":
            print("  Bye!")
            break
        elif choice == "1":
            list_practitioners()
        elif choice == "2":
            list_appointment_types()
        elif choice == "3":
            list_businesses()
        elif choice == "4":
            list_patients()
        elif choice == "5":
            list_appointments()
        elif choice == "6":
            list_appointments("cancelled")
        elif choice == "7":
            print("\n  Enter appointment details:")
            patient_id = input("    Patient ID: ").strip()
            practitioner_id = input("    Practitioner ID: ").strip()
            apt_type_id = input("    Appointment Type ID: ").strip()
            business_id = input("    Business ID: ").strip()
            starts_at = input("    Start time (YYYY-MM-DDTHH:MM:SS or blank for tomorrow 10am): ").strip()
            create_appointment(
                int(patient_id), int(practitioner_id), int(apt_type_id), int(business_id),
                starts_at if starts_at else None,
            )
        elif choice == "8":
            apt_id = input("    Appointment ID to reschedule: ").strip()
            new_time = input("    New start time (YYYY-MM-DDTHH:MM:SS): ").strip()
            reschedule_appointment(int(apt_id), new_time)
        elif choice == "9":
            apt_id = input("    Appointment ID to cancel: ").strip()
            print("    Reason codes: 10=patient, 20=practitioner, 30=DNA, 50=other")
            reason = input("    Reason code (default 20): ").strip()
            note = input("    Note (optional): ").strip()
            cancel_appointment(
                int(apt_id),
                int(reason) if reason else 20,
                note if note else "Cancelled via API test",
            )
        elif choice == "10":
            apt_id = input("    Appointment ID to delete: ").strip()
            confirm = input("    This is permanent! Type 'yes' to confirm: ").strip()
            if confirm.lower() == "yes":
                delete_appointment(int(apt_id))
        elif choice == "11":
            apt_id = input("    Appointment ID: ").strip()
            get_appointment(int(apt_id))
        elif choice == "12":
            run_full_lifecycle()
        elif choice == "13":
            separator("CONNECTION TEST")
            result = api_get("/practitioners")
            if result:
                print("  OK API connection successful!")
            else:
                print("  FAIL API connection failed. Check your API key and shard.")
        else:
            print("  Invalid option.")


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  Cliniko API Test Suite")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Shard: {SHARD}\n")

    if "--list-resources" in sys.argv:
        list_practitioners()
        list_appointment_types()
        list_businesses()
        list_patients()
    elif "--run-all" in sys.argv:
        run_full_lifecycle()
    else:
        interactive_menu()
