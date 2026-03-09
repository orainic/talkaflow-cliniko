"""
Cliniko API Client Module
=========================
Comprehensive Python client for the Cliniko API v1.

Usage:
    from cliniko_api import ClinikoAPI

    api = ClinikoAPI(api_key="your-key-here-au1", user_agent="YourApp (you@email.com)")
    patients = api.list_patients()
    appointment = api.create_individual_appointment(
        starts_at="2026-03-15T10:00:00",
        patient_id=123,
        practitioner_id=456,
        appointment_type_id=789,
        business_id=101,
    )
"""

import re
import requests
from base64 import b64encode


class ClinikoAPIError(Exception):
    """Raised when the Cliniko API returns an error."""

    def __init__(self, status_code, message, errors=None):
        self.status_code = status_code
        self.message = message
        self.errors = errors or {}
        super().__init__(f"HTTP {status_code}: {message}")


class ClinikoAPI:
    """Client for the Cliniko API v1."""

    def __init__(self, api_key, user_agent="ClinikoAPIClient (dev@example.com)"):
        """
        Initialize the Cliniko API client.

        Args:
            api_key: Cliniko API key (includes shard suffix, e.g. "...key...-au1")
            user_agent: Required User-Agent header (should include app name and contact email)
        """
        # Extract shard from API key suffix (e.g. "au1", "uk1", "au5")
        match = re.search(r"-([a-z]{2}\d+)$", api_key)
        if match:
            self.shard = match.group(1)
            self.raw_key = api_key[: match.start()]
        else:
            self.shard = "au1"
            self.raw_key = api_key

        self.base_url = f"https://api.{self.shard}.cliniko.com/v1"
        auth_string = b64encode(f"{self.raw_key}:".encode()).decode()

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Basic {auth_string}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": user_agent,
        })

    # ── Core HTTP Methods ──────────────────────────────────────────────────

    def _request(self, method, path, json=None, params=None):
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, json=json, params=params)

        if resp.status_code in (200, 201):
            return resp.json()
        elif resp.status_code == 204:
            return True
        else:
            try:
                body = resp.json()
                msg = body.get("message", resp.text)
                errors = body.get("errors", {})
            except Exception:
                msg = resp.text
                errors = {}
            raise ClinikoAPIError(resp.status_code, msg, errors)

    def _get(self, path, params=None):
        return self._request("GET", path, params=params)

    def _post(self, path, data):
        return self._request("POST", path, json=data)

    def _put(self, path, data):
        return self._request("PUT", path, json=data)

    def _patch(self, path, data=None):
        return self._request("PATCH", path, json=data or {})

    def _delete(self, path):
        return self._request("DELETE", path)

    # ── Patients ───────────────────────────────────────────────────────────

    def list_patients(self, **filters):
        """GET /patients - List all patients."""
        return self._get("/patients", params=filters)

    def list_deleted_patients(self, **filters):
        """GET /patients/deleted"""
        return self._get("/patients/deleted", params=filters)

    def list_archived_patients(self, **filters):
        """GET /patients/archived"""
        return self._get("/patients/archived", params=filters)

    def get_patient(self, patient_id):
        """GET /patients/:id"""
        return self._get(f"/patients/{patient_id}")

    def create_patient(self, first_name, last_name, **kwargs):
        """
        POST /patients - Create a patient.
        Required: first_name, last_name
        Optional: email, date_of_birth, address_1, city, state, post_code, country,
                  gender_identity, sex, phone_numbers, notes, occupation, etc.
        """
        data = {"first_name": first_name, "last_name": last_name, **kwargs}
        return self._post("/patients", data)

    def update_patient(self, patient_id, **kwargs):
        """PUT /patients/:id - Update a patient."""
        return self._put(f"/patients/{patient_id}", kwargs)

    def archive_patient(self, patient_id):
        """POST /patients/:id/archive"""
        return self._post(f"/patients/{patient_id}/archive", {})

    def unarchive_patient(self, patient_id):
        """POST /patients/:id/unarchive"""
        return self._post(f"/patients/{patient_id}/unarchive", {})

    # ── Practitioners (Read-Only) ──────────────────────────────────────────

    def list_practitioners(self, **filters):
        """GET /practitioners - List all active practitioners."""
        return self._get("/practitioners", params=filters)

    def get_practitioner(self, practitioner_id):
        """GET /practitioners/:id"""
        return self._get(f"/practitioners/{practitioner_id}")

    def list_inactive_practitioners(self, **filters):
        """GET /practitioners/inactive"""
        return self._get("/practitioners/inactive", params=filters)

    def list_practitioners_for_appointment_type(self, appointment_type_id):
        """GET /appointment_types/:id/practitioners"""
        return self._get(f"/appointment_types/{appointment_type_id}/practitioners")

    def list_practitioners_for_business(self, business_id):
        """GET /businesses/:id/practitioners"""
        return self._get(f"/businesses/{business_id}/practitioners")

    def list_inactive_practitioners_for_business(self, business_id):
        """GET /businesses/:id/practitioners/inactive"""
        return self._get(f"/businesses/{business_id}/practitioners/inactive")

    # ── Businesses (Read-Only) ─────────────────────────────────────────────

    def list_businesses(self, **filters):
        """GET /businesses - List all businesses."""
        return self._get("/businesses", params=filters)

    def get_business(self, business_id):
        """GET /businesses/:id"""
        return self._get(f"/businesses/{business_id}")

    # ── Appointment Types ──────────────────────────────────────────────────

    def list_appointment_types(self, **filters):
        """GET /appointment_types"""
        return self._get("/appointment_types", params=filters)

    def list_archived_appointment_types(self, **filters):
        """GET /appointment_types/archived"""
        return self._get("/appointment_types/archived", params=filters)

    def get_appointment_type(self, appointment_type_id):
        """GET /appointment_types/:id"""
        return self._get(f"/appointment_types/{appointment_type_id}")

    def list_appointment_types_for_practitioner(self, practitioner_id):
        """GET /practitioners/:id/appointment_types"""
        return self._get(f"/practitioners/{practitioner_id}/appointment_types")

    def create_appointment_type(self, name, duration_in_minutes, color, max_attendees=1, **kwargs):
        """
        POST /appointment_types
        Required: name, duration_in_minutes, color, max_attendees
        Optional: category, description, show_in_online_bookings
        """
        data = {
            "name": name,
            "duration_in_minutes": duration_in_minutes,
            "color": color,
            "max_attendees": max_attendees,
            **kwargs,
        }
        return self._post("/appointment_types", data)

    def update_appointment_type(self, appointment_type_id, **kwargs):
        """PUT /appointment_types/:id"""
        return self._put(f"/appointment_types/{appointment_type_id}", kwargs)

    def delete_appointment_type(self, appointment_type_id):
        """DELETE /appointment_types/:id"""
        return self._delete(f"/appointment_types/{appointment_type_id}")

    # ── Individual Appointments ────────────────────────────────────────────

    def list_individual_appointments(self, **filters):
        """GET /individual_appointments"""
        return self._get("/individual_appointments", params=filters)

    def list_deleted_individual_appointments(self, **filters):
        """GET /individual_appointments/deleted"""
        return self._get("/individual_appointments/deleted", params=filters)

    def list_cancelled_individual_appointments(self, **filters):
        """GET /individual_appointments/cancelled"""
        return self._get("/individual_appointments/cancelled", params=filters)

    def get_individual_appointment(self, appointment_id):
        """GET /individual_appointments/:id"""
        return self._get(f"/individual_appointments/{appointment_id}")

    def check_individual_appointment_conflicts(self, appointment_id):
        """GET /individual_appointments/:id/conflicts"""
        return self._get(f"/individual_appointments/{appointment_id}/conflicts")

    def create_individual_appointment(self, starts_at, patient_id, practitioner_id,
                                       appointment_type_id, business_id, **kwargs):
        """
        POST /individual_appointments
        Required: starts_at, patient_id, practitioner_id, appointment_type_id, business_id
        Optional: ends_at (auto-calculated if omitted)
        """
        data = {
            "starts_at": starts_at,
            "patient_id": patient_id,
            "practitioner_id": practitioner_id,
            "appointment_type_id": appointment_type_id,
            "business_id": business_id,
            **kwargs,
        }
        return self._post("/individual_appointments", data)

    def update_individual_appointment(self, appointment_id, **kwargs):
        """
        PUT /individual_appointments/:id
        Set ends_at=None to auto-recalculate from appointment type duration.
        """
        return self._put(f"/individual_appointments/{appointment_id}", kwargs)

    def delete_individual_appointment(self, appointment_id):
        """DELETE /individual_appointments/:id"""
        return self._delete(f"/individual_appointments/{appointment_id}")

    def cancel_individual_appointment(self, appointment_id, cancellation_reason, cancellation_note=None):
        """
        PATCH /individual_appointments/:id/cancel
        cancellation_reason codes:
            10 = Patient cancelled
            20 = Practitioner cancelled
            30 = Patient DNA (did not arrive)
            31 = Patient DNA (arrived late)
            40 = Patient cancelled (charged)
            50 = Other
            60 = COVID-19
        """
        data = {"cancellation_reason": cancellation_reason}
        if cancellation_note is not None:
            data["cancellation_note"] = cancellation_note
        return self._patch(f"/individual_appointments/{appointment_id}/cancel", data)

    # ── Bookings (Read-Only) ───────────────────────────────────────────────

    def list_bookings(self, **filters):
        """GET /bookings - List all bookings (individual, group, unavailable blocks)."""
        return self._get("/bookings", params=filters)

    def get_booking(self, booking_id):
        """GET /bookings/:id"""
        return self._get(f"/bookings/{booking_id}")

    # ── Available Times (Read-Only) ────────────────────────────────────────

    def list_available_times(self, business_id, practitioner_id, appointment_type_id, from_date, to_date):
        """
        GET /businesses/:bid/practitioners/:pid/appointment_types/:atid/available_times
        from_date/to_date: ISO date strings (max 7 days apart, not in the past)
        """
        path = (f"/businesses/{business_id}/practitioners/{practitioner_id}"
                f"/appointment_types/{appointment_type_id}/available_times")
        return self._get(path, params={"from": from_date, "to": to_date})

    def get_next_available_time(self, business_id, practitioner_id, appointment_type_id):
        """GET .../next_available_time"""
        path = (f"/businesses/{business_id}/practitioners/{practitioner_id}"
                f"/appointment_types/{appointment_type_id}/next_available_time")
        return self._get(path)

    # ── Availability Blocks ────────────────────────────────────────────────

    def list_availability_blocks(self, **filters):
        """GET /availability_blocks"""
        return self._get("/availability_blocks", params=filters)

    def get_availability_block(self, block_id):
        """GET /availability_blocks/:id"""
        return self._get(f"/availability_blocks/{block_id}")

    def create_availability_block(self, starts_at, ends_at, practitioner_id, business_id, **kwargs):
        """
        POST /availability_blocks
        Required: starts_at, ends_at, practitioner_id, business_id
        Optional: repeat_rule
        """
        data = {
            "starts_at": starts_at,
            "ends_at": ends_at,
            "practitioner_id": practitioner_id,
            "business_id": business_id,
            **kwargs,
        }
        return self._post("/availability_blocks", data)

    # ── Unavailable Blocks ─────────────────────────────────────────────────

    def list_unavailable_blocks(self, **filters):
        """GET /unavailable_blocks"""
        return self._get("/unavailable_blocks", params=filters)

    def get_unavailable_block(self, block_id):
        """GET /unavailable_blocks/:id"""
        return self._get(f"/unavailable_blocks/{block_id}")

    def create_unavailable_block(self, starts_at, ends_at, practitioner_id, business_id, **kwargs):
        """POST /unavailable_blocks"""
        data = {
            "starts_at": starts_at,
            "ends_at": ends_at,
            "practitioner_id": practitioner_id,
            "business_id": business_id,
            **kwargs,
        }
        return self._post("/unavailable_blocks", data)

    def delete_unavailable_block(self, block_id):
        """DELETE /unavailable_blocks/:id"""
        return self._delete(f"/unavailable_blocks/{block_id}")

    # ── Invoices (Read-Only) ───────────────────────────────────────────────

    def list_invoices(self, **filters):
        """GET /invoices"""
        return self._get("/invoices", params=filters)

    def list_deleted_invoices(self, **filters):
        """GET /invoices/deleted"""
        return self._get("/invoices/deleted", params=filters)

    def get_invoice(self, invoice_id):
        """GET /invoices/:id"""
        return self._get(f"/invoices/{invoice_id}")

    def list_invoices_for_patient(self, patient_id, **filters):
        """GET /patients/:id/invoices"""
        return self._get(f"/patients/{patient_id}/invoices", params=filters)

    def list_invoices_for_practitioner(self, practitioner_id, **filters):
        """GET /practitioners/:id/invoices"""
        return self._get(f"/practitioners/{practitioner_id}/invoices", params=filters)

    # ── Products ───────────────────────────────────────────────────────────

    def list_products(self, **filters):
        """GET /products"""
        return self._get("/products", params=filters)

    def get_product(self, product_id):
        """GET /products/:id"""
        return self._get(f"/products/{product_id}")

    def create_product(self, item_code, name, price, tax_id, **kwargs):
        """
        POST /products
        Required: item_code, name, price, tax_id
        Optional: product_supplier_name, cost_price, stock_level, serial_number, notes
        """
        data = {"item_code": item_code, "name": name, "price": price, "tax_id": tax_id, **kwargs}
        return self._post("/products", data)

    def update_product(self, product_id, **kwargs):
        """PUT /products/:id (note: stock_level cannot be updated here)"""
        return self._put(f"/products/{product_id}", kwargs)

    def delete_product(self, product_id):
        """DELETE /products/:id"""
        return self._delete(f"/products/{product_id}")

    # ── Treatment Notes ────────────────────────────────────────────────────

    def list_treatment_notes(self, **filters):
        """GET /treatment_notes"""
        return self._get("/treatment_notes", params=filters)

    def list_deleted_treatment_notes(self, **filters):
        """GET /treatment_notes/deleted"""
        return self._get("/treatment_notes/deleted", params=filters)

    def get_treatment_note(self, note_id):
        """GET /treatment_notes/:id"""
        return self._get(f"/treatment_notes/{note_id}")

    def create_treatment_note(self, patient_id, content, **kwargs):
        """
        POST /treatment_notes
        Required: patient_id, content
        Optional: draft, booking_id, treatment_note_template_id
        """
        data = {"patient_id": patient_id, "content": content, **kwargs}
        return self._post("/treatment_notes", data)

    def update_treatment_note(self, note_id, **kwargs):
        """PUT /treatment_notes/:id"""
        return self._put(f"/treatment_notes/{note_id}", kwargs)

    def delete_treatment_note(self, note_id):
        """DELETE /treatment_notes/:id"""
        return self._delete(f"/treatment_notes/{note_id}")

    # ── Contacts ───────────────────────────────────────────────────────────

    def list_contacts(self, **filters):
        """GET /contacts"""
        return self._get("/contacts", params=filters)

    def get_contact(self, contact_id):
        """GET /contacts/:id"""
        return self._get(f"/contacts/{contact_id}")

    def create_contact(self, first_name, last_name, country_code, **kwargs):
        """
        POST /contacts
        Required: first_name, last_name, country_code (ISO 3166-1)
        Optional: address_1, city, email, phone_numbers, company_name, doctor_type, etc.
        """
        data = {"first_name": first_name, "last_name": last_name, "country_code": country_code, **kwargs}
        return self._post("/contacts", data)

    def update_contact(self, contact_id, **kwargs):
        """PUT /contacts/:id"""
        return self._put(f"/contacts/{contact_id}", kwargs)

    def delete_contact(self, contact_id):
        """DELETE /contacts/:id"""
        return self._delete(f"/contacts/{contact_id}")

    # ── Medical Alerts ─────────────────────────────────────────────────────

    def list_medical_alerts(self, **filters):
        """GET /medical_alerts"""
        return self._get("/medical_alerts", params=filters)

    def get_medical_alert(self, alert_id):
        """GET /medical_alerts/:id"""
        return self._get(f"/medical_alerts/{alert_id}")

    def list_medical_alerts_for_patient(self, patient_id):
        """GET /patients/:id/medical_alerts"""
        return self._get(f"/patients/{patient_id}/medical_alerts")

    # ── Patient Attachments ────────────────────────────────────────────────

    def list_patient_attachments(self, **filters):
        """GET /patient_attachments"""
        return self._get("/patient_attachments", params=filters)

    def get_patient_attachment(self, attachment_id):
        """GET /patient_attachments/:id"""
        return self._get(f"/patient_attachments/{attachment_id}")

    def list_attachments_for_patient(self, patient_id):
        """GET /patients/:id/attachments"""
        return self._get(f"/patients/{patient_id}/attachments")

    # ── Patient Cases ──────────────────────────────────────────────────────

    def list_patient_cases(self, **filters):
        """GET /patient_cases"""
        return self._get("/patient_cases", params=filters)

    def get_patient_case(self, case_id):
        """GET /patient_cases/:id"""
        return self._get(f"/patient_cases/{case_id}")

    # ── Communications ─────────────────────────────────────────────────────

    def list_communications(self, **filters):
        """GET /communications"""
        return self._get("/communications", params=filters)

    def get_communication(self, communication_id):
        """GET /communications/:id"""
        return self._get(f"/communications/{communication_id}")

    # ── Referral Sources ───────────────────────────────────────────────────

    def list_referral_sources(self, **filters):
        """GET /referral_sources"""
        return self._get("/referral_sources", params=filters)

    def get_referral_source(self, source_id):
        """GET /referral_sources/:id"""
        return self._get(f"/referral_sources/{source_id}")

    def list_referral_source_types(self, **filters):
        """GET /referral_source_types"""
        return self._get("/referral_source_types", params=filters)

    # ── Concession Types ───────────────────────────────────────────────────

    def list_concession_types(self, **filters):
        """GET /concession_types"""
        return self._get("/concession_types", params=filters)

    def get_concession_type(self, concession_type_id):
        """GET /concession_types/:id"""
        return self._get(f"/concession_types/{concession_type_id}")

    # ── Taxes ──────────────────────────────────────────────────────────────

    def list_taxes(self, **filters):
        """GET /taxes"""
        return self._get("/taxes", params=filters)

    def get_tax(self, tax_id):
        """GET /taxes/:id"""
        return self._get(f"/taxes/{tax_id}")

    # ── Settings ───────────────────────────────────────────────────────────

    def get_settings(self):
        """GET /settings"""
        return self._get("/settings")

    # ── Users ──────────────────────────────────────────────────────────────

    def list_users(self, **filters):
        """GET /users"""
        return self._get("/users", params=filters)

    def get_user(self, user_id):
        """GET /users/:id"""
        return self._get(f"/users/{user_id}")

    # ── Billable Items ─────────────────────────────────────────────────────

    def list_billable_items(self, **filters):
        """GET /billable_items"""
        return self._get("/billable_items", params=filters)

    def get_billable_item(self, item_id):
        """GET /billable_items/:id"""
        return self._get(f"/billable_items/{item_id}")

    # ── Services ───────────────────────────────────────────────────────────

    def list_services(self, **filters):
        """GET /services"""
        return self._get("/services", params=filters)

    def get_service(self, service_id):
        """GET /services/:id"""
        return self._get(f"/services/{service_id}")

    # ── Stock Adjustments ──────────────────────────────────────────────────

    def list_stock_adjustments(self, **filters):
        """GET /stock_adjustments"""
        return self._get("/stock_adjustments", params=filters)

    def get_stock_adjustment(self, adjustment_id):
        """GET /stock_adjustments/:id"""
        return self._get(f"/stock_adjustments/{adjustment_id}")

    # ── Group Appointments ─────────────────────────────────────────────────

    def list_group_appointments(self, **filters):
        """GET /group_appointments"""
        return self._get("/group_appointments", params=filters)

    def get_group_appointment(self, appointment_id):
        """GET /group_appointments/:id"""
        return self._get(f"/group_appointments/{appointment_id}")

    # ── Attendees ──────────────────────────────────────────────────────────

    def list_attendees(self, **filters):
        """GET /attendees"""
        return self._get("/attendees", params=filters)

    def get_attendee(self, attendee_id):
        """GET /attendees/:id"""
        return self._get(f"/attendees/{attendee_id}")

    # ── Daily Availabilities ───────────────────────────────────────────────

    def list_daily_availabilities(self, **filters):
        """GET /daily_availabilities"""
        return self._get("/daily_availabilities", params=filters)

    # ── Patient Forms ──────────────────────────────────────────────────────

    def list_patient_forms(self, **filters):
        """GET /patient_forms"""
        return self._get("/patient_forms", params=filters)

    def get_patient_form(self, form_id):
        """GET /patient_forms/:id"""
        return self._get(f"/patient_forms/{form_id}")

    def list_patient_form_templates(self, **filters):
        """GET /patient_form_templates"""
        return self._get("/patient_form_templates", params=filters)

    # ── Treatment Note Templates ───────────────────────────────────────────

    def list_treatment_note_templates(self, **filters):
        """GET /treatment_note_templates"""
        return self._get("/treatment_note_templates", params=filters)

    def get_treatment_note_template(self, template_id):
        """GET /treatment_note_templates/:id"""
        return self._get(f"/treatment_note_templates/{template_id}")

    # ── Invoice Items ──────────────────────────────────────────────────────

    def list_invoice_items(self, **filters):
        """GET /invoice_items"""
        return self._get("/invoice_items", params=filters)

    def get_invoice_item(self, item_id):
        """GET /invoice_items/:id"""
        return self._get(f"/invoice_items/{item_id}")

    # ── Practitioner Reference Numbers ─────────────────────────────────────

    def list_practitioner_reference_numbers(self, **filters):
        """GET /practitioner_reference_numbers"""
        return self._get("/practitioner_reference_numbers", params=filters)

    def get_practitioner_reference_number(self, ref_id):
        """GET /practitioner_reference_numbers/:id"""
        return self._get(f"/practitioner_reference_numbers/{ref_id}")
