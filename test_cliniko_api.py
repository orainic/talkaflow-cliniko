"""
Cliniko API Integration Tests
==============================
Live integration tests against the Cliniko API.
Tests all major API features: CRUD operations on patients, appointments,
contacts, appointment types, and read-only endpoints.

Usage:
    python -m pytest test_cliniko_api.py -v
    python -m pytest test_cliniko_api.py -v -k "patient"     # run only patient tests
    python -m pytest test_cliniko_api.py -v -k "appointment"  # run only appointment tests
"""

import os
import pytest
from datetime import datetime, timedelta
from dotenv import load_dotenv

from cliniko_api import ClinikoAPI, ClinikoAPIError

# ── Configuration (loaded from .env) ──────────────────────────────────────────

load_dotenv()

API_KEY = os.environ["CLINIKO_API_KEY"]
USER_AGENT = os.environ.get("CLINIKO_USER_AGENT", "TalkaFlow Test Suite")


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def api():
    """Create a shared API client for all tests."""
    return ClinikoAPI(api_key=API_KEY, user_agent=USER_AGENT)


@pytest.fixture(scope="session")
def practitioner_id(api):
    """Get the first available practitioner ID."""
    data = api.list_practitioners()
    assert "practitioners" in data
    assert len(data["practitioners"]) > 0, "No practitioners found - add one in Cliniko"
    return data["practitioners"][0]["id"]


@pytest.fixture(scope="session")
def business_id(api):
    """Get the first available business ID."""
    data = api.list_businesses()
    assert "businesses" in data
    assert len(data["businesses"]) > 0
    return data["businesses"][0]["id"]


@pytest.fixture(scope="session")
def appointment_type_id(api):
    """Get the first available appointment type ID."""
    data = api.list_appointment_types()
    assert "appointment_types" in data
    assert len(data["appointment_types"]) > 0
    return data["appointment_types"][0]["id"]


@pytest.fixture(scope="session")
def test_patient(api):
    """Create a test patient, return it, and clean up would require delete (not available)."""
    patient = api.create_patient(
        first_name="IntegrationTest",
        last_name="Patient",
        email="integration.test@example.com",
    )
    assert patient["id"]
    yield patient
    # Cleanup: archive the test patient
    try:
        api.archive_patient(patient["id"])
    except ClinikoAPIError:
        pass


@pytest.fixture
def test_appointment(api, test_patient, practitioner_id, appointment_type_id, business_id):
    """Create a test appointment and clean up after."""
    tomorrow = datetime.now() + timedelta(days=1)
    starts_at = tomorrow.replace(hour=10, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")

    apt = api.create_individual_appointment(
        starts_at=starts_at,
        patient_id=test_patient["id"],
        practitioner_id=practitioner_id,
        appointment_type_id=appointment_type_id,
        business_id=business_id,
    )
    yield apt
    # Cleanup: try to delete the appointment
    try:
        api.delete_individual_appointment(apt["id"])
    except ClinikoAPIError:
        pass


# ── Connection & Auth Tests ────────────────────────────────────────────────────

class TestConnection:
    def test_api_client_initializes_with_shard(self):
        client = ClinikoAPI(api_key="testkey-au5", user_agent="Test")
        assert client.shard == "au5"
        assert client.base_url == "https://api.au5.cliniko.com/v1"

    def test_api_client_defaults_to_au1(self):
        client = ClinikoAPI(api_key="testkey_no_shard", user_agent="Test")
        assert client.shard == "au1"

    def test_successful_api_connection(self, api):
        data = api.list_practitioners()
        assert "practitioners" in data

    def test_invalid_api_key_raises_error(self):
        bad_api = ClinikoAPI(api_key="invalid-key-au5", user_agent="Test")
        with pytest.raises(ClinikoAPIError) as exc_info:
            bad_api.list_practitioners()
        assert exc_info.value.status_code == 401


# ── Practitioner Tests (Read-Only) ─────────────────────────────────────────────

class TestPractitioners:
    def test_list_practitioners(self, api):
        data = api.list_practitioners()
        assert "practitioners" in data
        practitioners = data["practitioners"]
        assert len(practitioners) >= 1
        p = practitioners[0]
        assert "id" in p
        assert "first_name" in p
        assert "last_name" in p

    def test_get_single_practitioner(self, api, practitioner_id):
        p = api.get_practitioner(practitioner_id)
        assert p["id"] == practitioner_id
        assert "first_name" in p

    def test_list_inactive_practitioners(self, api):
        data = api.list_inactive_practitioners()
        assert "practitioners" in data

    def test_list_practitioners_for_business(self, api, business_id):
        data = api.list_practitioners_for_business(business_id)
        assert "practitioners" in data

    def test_list_inactive_practitioners_for_business(self, api, business_id):
        data = api.list_inactive_practitioners_for_business(business_id)
        assert "practitioners" in data

    def test_list_practitioners_for_appointment_type(self, api, appointment_type_id):
        data = api.list_practitioners_for_appointment_type(appointment_type_id)
        assert "practitioners" in data

    def test_get_nonexistent_practitioner_raises_error(self, api):
        with pytest.raises(ClinikoAPIError) as exc_info:
            api.get_practitioner(999999999999)
        assert exc_info.value.status_code == 404


# ── Business Tests (Read-Only) ─────────────────────────────────────────────────

class TestBusinesses:
    def test_list_businesses(self, api):
        data = api.list_businesses()
        assert "businesses" in data
        assert len(data["businesses"]) >= 1
        b = data["businesses"][0]
        assert "id" in b
        assert "business_name" in b

    def test_get_single_business(self, api, business_id):
        b = api.get_business(business_id)
        assert b["id"] == business_id


# ── Patient Tests (CRUD) ──────────────────────────────────────────────────────

class TestPatients:
    def test_create_patient(self, api):
        patient = api.create_patient(
            first_name="CreateTest",
            last_name="Patient",
            email="create.test@example.com",
        )
        assert patient["id"]
        assert patient["first_name"] == "CreateTest"
        assert patient["last_name"] == "Patient"
        # cleanup
        api.archive_patient(patient["id"])

    def test_list_patients(self, api):
        data = api.list_patients()
        assert "patients" in data

    def test_get_patient(self, api, test_patient):
        p = api.get_patient(test_patient["id"])
        assert p["id"] == test_patient["id"]
        assert p["first_name"] == "IntegrationTest"

    def test_update_patient(self, api, test_patient):
        updated = api.update_patient(test_patient["id"], notes="Updated via integration test")
        assert updated["id"] == test_patient["id"]

    def test_archive_and_unarchive_patient(self, api):
        patient = api.create_patient(first_name="Archive", last_name="TestPatient")
        patient_id = patient["id"]

        # Archive
        result = api.archive_patient(patient_id)
        assert result is not None

        # Verify appears in archived list
        archived_list = api.list_archived_patients()
        archived_ids = [p["id"] for p in archived_list["patients"]]
        assert patient_id in archived_ids

        # Unarchive
        api.unarchive_patient(patient_id)
        unarchived = api.get_patient(patient_id)
        assert unarchived.get("archived_at") is None

        # Cleanup
        api.archive_patient(patient_id)

    def test_list_archived_patients(self, api):
        data = api.list_archived_patients()
        assert "patients" in data

    def test_list_deleted_patients(self, api):
        data = api.list_deleted_patients()
        assert "patients" in data

    def test_create_patient_missing_required_field(self, api):
        with pytest.raises(ClinikoAPIError) as exc_info:
            api.create_patient(first_name="", last_name="")
        assert exc_info.value.status_code in (422, 400)

    def test_get_nonexistent_patient(self, api):
        with pytest.raises(ClinikoAPIError) as exc_info:
            api.get_patient(999999999999)
        assert exc_info.value.status_code == 404


# ── Appointment Type Tests ─────────────────────────────────────────────────────

class TestAppointmentTypes:
    def test_list_appointment_types(self, api):
        data = api.list_appointment_types()
        assert "appointment_types" in data
        assert len(data["appointment_types"]) >= 1
        at = data["appointment_types"][0]
        assert "name" in at
        assert "duration_in_minutes" in at

    def test_get_appointment_type(self, api, appointment_type_id):
        at = api.get_appointment_type(appointment_type_id)
        assert at["id"] == appointment_type_id

    def test_list_archived_appointment_types(self, api):
        data = api.list_archived_appointment_types()
        assert "appointment_types" in data

    def test_list_appointment_types_for_practitioner(self, api, practitioner_id):
        data = api.list_appointment_types_for_practitioner(practitioner_id)
        assert "appointment_types" in data

    def test_create_update_delete_appointment_type(self, api):
        # Create
        at = api.create_appointment_type(
            name="API Test Type",
            duration_in_minutes=15,
            color="#FF5733",
            max_attendees=1,
            description="Created by integration test",
        )
        assert at["id"]
        assert at["name"] == "API Test Type"
        assert at["duration_in_minutes"] == 15

        # Update
        updated = api.update_appointment_type(at["id"], name="API Test Type Updated")
        assert updated["name"] == "API Test Type Updated"

        # Delete
        result = api.delete_appointment_type(at["id"])
        assert result is True


# ── Individual Appointment Tests ───────────────────────────────────────────────

class TestIndividualAppointments:
    def test_create_appointment(self, api, test_patient, practitioner_id, appointment_type_id, business_id):
        tomorrow = datetime.now() + timedelta(days=3)
        starts_at = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")

        apt = api.create_individual_appointment(
            starts_at=starts_at,
            patient_id=test_patient["id"],
            practitioner_id=practitioner_id,
            appointment_type_id=appointment_type_id,
            business_id=business_id,
        )
        assert apt["id"]
        assert apt["starts_at"]
        assert apt["ends_at"]

        # Cleanup
        api.delete_individual_appointment(apt["id"])

    def test_get_appointment(self, api, test_appointment):
        apt = api.get_individual_appointment(test_appointment["id"])
        assert apt["id"] == test_appointment["id"]

    def test_list_appointments(self, api):
        data = api.list_individual_appointments()
        assert "individual_appointments" in data

    def test_list_deleted_appointments(self, api):
        data = api.list_deleted_individual_appointments()
        assert "individual_appointments" in data

    def test_list_cancelled_appointments(self, api):
        data = api.list_cancelled_individual_appointments()
        assert "individual_appointments" in data

    def test_check_appointment_conflicts(self, api, test_appointment):
        result = api.check_individual_appointment_conflicts(test_appointment["id"])
        assert result is not None

    def test_reschedule_appointment(self, api, test_appointment):
        day_after = datetime.now() + timedelta(days=4)
        new_start = day_after.replace(hour=14, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")

        updated = api.update_individual_appointment(
            test_appointment["id"],
            starts_at=new_start,
            ends_at=None,
        )
        assert updated["id"] == test_appointment["id"]
        assert "14:00" in updated["starts_at"] or updated["starts_at"] != test_appointment["starts_at"]

    def test_cancel_appointment(self, api, test_patient, practitioner_id, appointment_type_id, business_id):
        # Create a fresh appointment to cancel
        day = datetime.now() + timedelta(days=5)
        starts_at = day.replace(hour=9, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")

        apt = api.create_individual_appointment(
            starts_at=starts_at,
            patient_id=test_patient["id"],
            practitioner_id=practitioner_id,
            appointment_type_id=appointment_type_id,
            business_id=business_id,
        )

        # Cancel with reason code
        result = api.cancel_individual_appointment(
            apt["id"],
            cancellation_reason=10,
            cancellation_note="Integration test cancellation",
        )
        assert result is True

    def test_cancel_with_all_reason_codes(self, api, test_patient, practitioner_id, appointment_type_id, business_id):
        """Test that all documented cancellation reason codes work."""
        reason_codes = [10, 20, 30, 31, 40, 50, 60]
        for i, code in enumerate(reason_codes):
            day = datetime.now() + timedelta(days=6 + i)
            starts_at = day.replace(hour=9, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")

            apt = api.create_individual_appointment(
                starts_at=starts_at,
                patient_id=test_patient["id"],
                practitioner_id=practitioner_id,
                appointment_type_id=appointment_type_id,
                business_id=business_id,
            )
            result = api.cancel_individual_appointment(apt["id"], cancellation_reason=code)
            assert result is True, f"Cancel with reason code {code} failed"

    def test_delete_appointment(self, api, test_patient, practitioner_id, appointment_type_id, business_id):
        day = datetime.now() + timedelta(days=15)
        starts_at = day.replace(hour=16, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")

        apt = api.create_individual_appointment(
            starts_at=starts_at,
            patient_id=test_patient["id"],
            practitioner_id=practitioner_id,
            appointment_type_id=appointment_type_id,
            business_id=business_id,
        )
        result = api.delete_individual_appointment(apt["id"])
        assert result is True

        # Verify deleted
        with pytest.raises(ClinikoAPIError) as exc_info:
            api.get_individual_appointment(apt["id"])
        assert exc_info.value.status_code == 404

    def test_create_appointment_missing_fields(self, api):
        with pytest.raises(ClinikoAPIError) as exc_info:
            api.create_individual_appointment(
                starts_at="2026-03-15T10:00:00",
                patient_id=0,
                practitioner_id=0,
                appointment_type_id=0,
                business_id=0,
            )
        assert exc_info.value.status_code in (422, 400, 404)

    def test_get_nonexistent_appointment(self, api):
        with pytest.raises(ClinikoAPIError) as exc_info:
            api.get_individual_appointment(999999999999)
        assert exc_info.value.status_code == 404


# ── Appointment Lifecycle Test ─────────────────────────────────────────────────

class TestAppointmentLifecycle:
    """End-to-end: create -> verify -> reschedule -> verify -> cancel -> verify."""

    def test_full_lifecycle(self, api, test_patient, practitioner_id, appointment_type_id, business_id):
        # 1. Create
        day = datetime.now() + timedelta(days=20)
        starts_at = day.replace(hour=10, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")

        apt = api.create_individual_appointment(
            starts_at=starts_at,
            patient_id=test_patient["id"],
            practitioner_id=practitioner_id,
            appointment_type_id=appointment_type_id,
            business_id=business_id,
        )
        apt_id = apt["id"]
        assert apt_id
        original_start = apt["starts_at"]

        # 2. Verify created
        fetched = api.get_individual_appointment(apt_id)
        assert fetched["id"] == apt_id
        assert fetched.get("cancelled_at") is None

        # 3. Reschedule
        new_day = datetime.now() + timedelta(days=21)
        new_start = new_day.replace(hour=15, minute=30, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")
        updated = api.update_individual_appointment(apt_id, starts_at=new_start, ends_at=None)
        assert updated["starts_at"] != original_start

        # 4. Verify rescheduled
        fetched2 = api.get_individual_appointment(apt_id)
        assert fetched2["starts_at"] == updated["starts_at"]

        # 5. Cancel
        result = api.cancel_individual_appointment(
            apt_id,
            cancellation_reason=50,
            cancellation_note="Full lifecycle test",
        )
        assert result is True


# ── Booking Tests (Read-Only) ──────────────────────────────────────────────────

class TestBookings:
    def test_list_bookings(self, api):
        data = api.list_bookings()
        assert "bookings" in data

    def test_get_booking_not_found(self, api):
        with pytest.raises(ClinikoAPIError) as exc_info:
            api.get_booking(999999999999)
        assert exc_info.value.status_code == 404


# ── Available Times Tests ──────────────────────────────────────────────────────

class TestAvailableTimes:
    def test_list_available_times(self, api, business_id, practitioner_id, appointment_type_id):
        from_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        to_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        try:
            data = api.list_available_times(
                business_id, practitioner_id, appointment_type_id,
                from_date, to_date,
            )
            assert "available_times" in data
        except ClinikoAPIError as e:
            # May fail if online bookings not configured
            assert e.status_code in (404, 422)

    def test_get_next_available_time(self, api, business_id, practitioner_id, appointment_type_id):
        try:
            data = api.get_next_available_time(business_id, practitioner_id, appointment_type_id)
            # Response may be empty if no availability
            assert data is not None
        except ClinikoAPIError as e:
            assert e.status_code in (404, 422)


# ── Contact Tests (CRUD) ──────────────────────────────────────────────────────

class TestContacts:
    def test_list_contacts(self, api):
        data = api.list_contacts()
        assert "contacts" in data

    def test_create_update_delete_contact(self, api):
        # Create
        contact = api.create_contact(
            first_name="Test",
            last_name="Doctor",
            country_code="AU",
            email="test.doctor@example.com",
        )
        assert contact["id"]
        assert contact["first_name"] == "Test"

        # Read
        fetched = api.get_contact(contact["id"])
        assert fetched["id"] == contact["id"]

        # Update
        updated = api.update_contact(contact["id"], first_name="UpdatedTest")
        assert updated["first_name"] == "UpdatedTest"

        # Delete
        result = api.delete_contact(contact["id"])
        assert result is True

    def test_get_nonexistent_contact(self, api):
        with pytest.raises(ClinikoAPIError) as exc_info:
            api.get_contact(999999999999)
        assert exc_info.value.status_code == 404


# ── Invoice Tests (Read-Only) ─────────────────────────────────────────────────

class TestInvoices:
    def test_list_invoices(self, api):
        data = api.list_invoices()
        assert "invoices" in data

    def test_list_deleted_invoices(self, api):
        data = api.list_deleted_invoices()
        assert "invoices" in data

    def test_list_invoices_for_patient(self, api, test_patient):
        data = api.list_invoices_for_patient(test_patient["id"])
        assert "invoices" in data

    def test_list_invoices_for_practitioner(self, api, practitioner_id):
        data = api.list_invoices_for_practitioner(practitioner_id)
        assert "invoices" in data


# ── Read-Only Endpoint Tests ──────────────────────────────────────────────────

class TestReadOnlyEndpoints:
    """Test all read-only list endpoints return valid responses."""

    def test_list_availability_blocks(self, api):
        data = api.list_availability_blocks()
        assert "availability_blocks" in data

    def test_list_unavailable_blocks(self, api):
        data = api.list_unavailable_blocks()
        assert "unavailable_blocks" in data

    def test_list_medical_alerts(self, api):
        data = api.list_medical_alerts()
        assert "medical_alerts" in data

    def test_list_treatment_notes(self, api):
        data = api.list_treatment_notes()
        assert "treatment_notes" in data

    def test_list_deleted_treatment_notes(self, api):
        data = api.list_deleted_treatment_notes()
        assert "treatment_notes" in data

    def test_list_group_appointments(self, api):
        data = api.list_group_appointments()
        assert "group_appointments" in data

    def test_list_attendees(self, api):
        data = api.list_attendees()
        assert "attendees" in data

    def test_list_billable_items(self, api):
        data = api.list_billable_items()
        assert "billable_items" in data

    def test_list_communications(self, api):
        data = api.list_communications()
        assert "communications" in data

    def test_list_concession_types(self, api):
        data = api.list_concession_types()
        assert "concession_types" in data

    def test_list_daily_availabilities(self, api):
        data = api.list_daily_availabilities()
        assert "daily_availabilities" in data

    def test_list_invoice_items(self, api):
        data = api.list_invoice_items()
        assert "invoice_items" in data

    def test_list_patient_attachments(self, api):
        data = api.list_patient_attachments()
        assert "patient_attachments" in data

    def test_list_patient_cases(self, api):
        data = api.list_patient_cases()
        assert "patient_cases" in data

    def test_list_patient_forms(self, api):
        data = api.list_patient_forms()
        assert "patient_forms" in data

    def test_list_patient_form_templates(self, api):
        data = api.list_patient_form_templates()
        assert "patient_form_templates" in data

    def test_list_products(self, api):
        data = api.list_products()
        assert "products" in data

    def test_list_referral_sources(self, api):
        data = api.list_referral_sources()
        assert "referral_sources" in data

    def test_list_referral_source_types(self, api):
        data = api.list_referral_source_types()
        assert "referral_source_types" in data

    def test_list_services(self, api):
        data = api.list_services()
        assert "services" in data

    def test_list_stock_adjustments(self, api):
        data = api.list_stock_adjustments()
        assert "stock_adjustments" in data

    def test_list_taxes(self, api):
        data = api.list_taxes()
        assert "taxes" in data

    def test_list_treatment_note_templates(self, api):
        data = api.list_treatment_note_templates()
        assert "treatment_note_templates" in data

    def test_list_practitioner_reference_numbers(self, api):
        data = api.list_practitioner_reference_numbers()
        assert "practitioner_reference_numbers" in data

    def test_list_users(self, api):
        data = api.list_users()
        assert "users" in data

    def test_get_settings(self, api):
        data = api.get_settings()
        assert data is not None


# ── Error Handling Tests ───────────────────────────────────────────────────────

class TestErrorHandling:
    def test_cliniko_api_error_has_status_code(self):
        err = ClinikoAPIError(422, "Validation Failed", {"base": "error"})
        assert err.status_code == 422
        assert "422" in str(err)

    def test_cliniko_api_error_has_errors_dict(self):
        err = ClinikoAPIError(422, "Validation Failed", {"field": "is required"})
        assert err.errors == {"field": "is required"}

    def test_404_on_nonexistent_resource(self, api):
        with pytest.raises(ClinikoAPIError) as exc_info:
            api.get_patient(1)
        assert exc_info.value.status_code == 404


# ── Filter Tests ───────────────────────────────────────────────────────────────

class TestFiltering:
    def test_filter_patients_by_first_name(self, api):
        # Cliniko uses q[] bracket filter syntax
        data = api.list_patients(**{"q[]": "first_name:~IntegrationTest"})
        assert "patients" in data

    def test_filter_appointments_by_practitioner(self, api, practitioner_id):
        data = api.list_individual_appointments(practitioner_id=practitioner_id)
        assert "individual_appointments" in data

    def test_pagination_per_page(self, api):
        data = api.list_patients(per_page=1)
        assert "patients" in data
