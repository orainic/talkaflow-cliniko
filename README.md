# TalkaFlow - Cliniko API Integration

A comprehensive Python client and integration test suite for the [Cliniko API v1](https://docs.api.cliniko.com/developer-portal).

## Overview

This project provides:

- **`cliniko_api.py`** - A full-featured Python client covering all 34 Cliniko API resource types (80+ methods)
- **`test_cliniko_api.py`** - 83 live integration tests validating every major API feature
- **`cliniko_api_test.py`** - Interactive CLI tool for manual API testing and appointment lifecycle demos

---

## Quick Start

### Prerequisites

- Python 3.10+
- `requests` library
- `pytest` (for running tests)

```bash
pip install requests pytest python-dotenv
```

### Configuration

1. Copy the example environment file and add your real API key:

```bash
cp .env.example .env
```

2. Edit `.env` with your credentials:

```
CLINIKO_API_KEY=your-api-key-here-au5
CLINIKO_USER_AGENT=YourApp (you@email.com)
```

> **Important:** The `.env` file is in `.gitignore` and will never be committed to git. Never hardcode API keys in source files.

3. The test scripts and CLI tool load credentials from `.env` automatically. The API client module itself accepts the key as a parameter so you can pass it from any secret store:

```python
from cliniko_api import ClinikoAPI

api = ClinikoAPI(
    api_key=os.environ["CLINIKO_API_KEY"],
    user_agent=os.environ["CLINIKO_USER_AGENT"],
)
```

### Generate an API Key

1. Log in to Cliniko
2. Go to **My Info** > **Manage API Keys**
3. Click **Add an API Key**, give it a name, and copy it immediately
4. The key format is: `{KEY_VALUE}-{SHARD_ID}` (e.g. `...abc123-au5`)

Reference: [Cliniko Help - Generate an API Key](https://help.cliniko.com/en/articles/1023957-generate-a-cliniko-api-key)

---

## API Client (`cliniko_api.py`)

### Authentication

Cliniko uses HTTP Basic Auth. The API key is the username with an empty password. The client handles this automatically:

```python
api = ClinikoAPI(api_key="YOUR_KEY-au1", user_agent="MyApp (me@example.com)")
```

### Shard / Region Routing

API keys include a shard suffix that determines the base URL:

| Shard | Base URL |
|-------|----------|
| `au1` | `https://api.au1.cliniko.com/v1` |
| `au5` | `https://api.au5.cliniko.com/v1` |
| `uk1` | `https://api.uk1.cliniko.com/v1` |
| `us1` | `https://api.us1.cliniko.com/v1` |

The client parses the shard automatically from the API key.

### Error Handling

All API errors raise `ClinikoAPIError` with `status_code`, `message`, and `errors` attributes:

```python
from cliniko_api import ClinikoAPI, ClinikoAPIError

try:
    api.get_patient(999999)
except ClinikoAPIError as e:
    print(e.status_code)  # 404
    print(e.message)      # "The requested resource could not be found"
    print(e.errors)       # {}
```

---

## Complete API Reference

### Patients

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_patients(**filters)` | List all patients |
| GET | `list_deleted_patients(**filters)` | List deleted patients |
| GET | `list_archived_patients(**filters)` | List archived patients |
| GET | `get_patient(patient_id)` | Get a single patient |
| POST | `create_patient(first_name, last_name, **kwargs)` | Create a patient |
| PUT | `update_patient(patient_id, **kwargs)` | Update a patient |
| POST | `archive_patient(patient_id)` | Archive a patient |
| POST | `unarchive_patient(patient_id)` | Unarchive a patient |

**Create required fields:** `first_name`, `last_name`

**Optional fields:** `email`, `date_of_birth`, `address_1`, `address_2`, `address_3`, `city`, `state`, `post_code`, `country`, `gender_identity`, `sex`, `emergency_contact`, `notes`, `appointment_notes`, `occupation`, `patient_phone_numbers`, `preferred_first_name`, `pronouns`, `referral_source`, `reminder_type`, `time_zone`

**Filterable by:** `created_at`, `date_of_birth`, `email`, `first_name`, `id`, `last_name`, `old_reference_id`, `updated_at`

```python
# Create
patient = api.create_patient(first_name="Jane", last_name="Doe", email="jane@example.com")

# Update
api.update_patient(patient["id"], notes="VIP patient")

# Archive / Unarchive
api.archive_patient(patient["id"])
api.unarchive_patient(patient["id"])
```

---

### Practitioners (Read-Only)

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_practitioners(**filters)` | List all active practitioners |
| GET | `get_practitioner(practitioner_id)` | Get a single practitioner |
| GET | `list_inactive_practitioners(**filters)` | List inactive practitioners |
| GET | `list_practitioners_for_appointment_type(apt_type_id)` | Practitioners for an appointment type |
| GET | `list_practitioners_for_business(business_id)` | Practitioners for a business |
| GET | `list_inactive_practitioners_for_business(business_id)` | Inactive practitioners for a business |

**Filterable by:** `created_at`, `id`, `updated_at`, `user_id`

---

### Businesses (Read-Only)

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_businesses(**filters)` | List all businesses |
| GET | `get_business(business_id)` | Get a single business |

**Filterable by:** `created_at`, `id`, `updated_at`

---

### Appointment Types

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_appointment_types(**filters)` | List all appointment types |
| GET | `list_archived_appointment_types(**filters)` | List archived types |
| GET | `get_appointment_type(apt_type_id)` | Get a single type |
| GET | `list_appointment_types_for_practitioner(practitioner_id)` | Types for a practitioner |
| POST | `create_appointment_type(name, duration_in_minutes, color, max_attendees, **kwargs)` | Create a type |
| PUT | `update_appointment_type(apt_type_id, **kwargs)` | Update a type |
| DELETE | `delete_appointment_type(apt_type_id)` | Delete a type |

**Create required fields:** `name`, `duration_in_minutes`, `color` (hex, e.g. `"#FF5733"`), `max_attendees`

**Optional fields:** `category`, `description`, `show_in_online_bookings`

```python
apt_type = api.create_appointment_type(
    name="Initial Consult",
    duration_in_minutes=60,
    color="#3498DB",
    max_attendees=1,
)
```

---

### Individual Appointments

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_individual_appointments(**filters)` | List all appointments |
| GET | `list_deleted_individual_appointments(**filters)` | List deleted appointments |
| GET | `list_cancelled_individual_appointments(**filters)` | List cancelled appointments |
| GET | `get_individual_appointment(apt_id)` | Get a single appointment |
| GET | `check_individual_appointment_conflicts(apt_id)` | Check for scheduling conflicts |
| POST | `create_individual_appointment(starts_at, patient_id, practitioner_id, apt_type_id, business_id, **kwargs)` | Book an appointment |
| PUT | `update_individual_appointment(apt_id, **kwargs)` | Reschedule / update |
| DELETE | `delete_individual_appointment(apt_id)` | Permanently delete |
| PATCH | `cancel_individual_appointment(apt_id, cancellation_reason, cancellation_note=None)` | Cancel with reason |

**Create required fields:** `starts_at` (ISO 8601), `patient_id`, `practitioner_id`, `appointment_type_id`, `business_id`

**Optional:** `ends_at` (auto-calculated from appointment type duration if omitted)

**Cancellation reason codes:**

| Code | Meaning |
|------|---------|
| 10 | Patient cancelled |
| 20 | Practitioner cancelled |
| 30 | Patient DNA (did not arrive) |
| 31 | Patient DNA (arrived late) |
| 40 | Patient cancelled (charged) |
| 50 | Other |
| 60 | COVID-19 |

**Filterable by:** `appointment_type_id`, `archived_at`, `business_id`, `cancelled_at`, `created_at`, `ends_at`, `id`, `patient_id`, `practitioner_id`, `repeated_from_id`, `starts_at`, `updated_at`

#### Appointment Lifecycle Example

```python
from cliniko_api import ClinikoAPI

api = ClinikoAPI(api_key="YOUR_KEY-au5", user_agent="MyApp (me@example.com)")

# 1. Book
apt = api.create_individual_appointment(
    starts_at="2026-03-15T10:00:00",
    patient_id=123,
    practitioner_id=456,
    appointment_type_id=789,
    business_id=101,
)
print(f"Booked: {apt['id']} at {apt['starts_at']}")

# 2. Reschedule (set ends_at=None to auto-recalculate duration)
updated = api.update_individual_appointment(
    apt["id"],
    starts_at="2026-03-16T14:00:00",
    ends_at=None,
)
print(f"Rescheduled to: {updated['starts_at']}")

# 3. Cancel
api.cancel_individual_appointment(
    apt["id"],
    cancellation_reason=10,
    cancellation_note="Patient requested cancellation",
)
print("Cancelled.")
```

---

### Available Times (Read-Only)

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_available_times(business_id, practitioner_id, apt_type_id, from_date, to_date)` | Get available slots (max 7-day range) |
| GET | `get_next_available_time(business_id, practitioner_id, apt_type_id)` | Get next single available slot |

```python
times = api.list_available_times(
    business_id=101,
    practitioner_id=456,
    appointment_type_id=789,
    from_date="2026-03-10",
    to_date="2026-03-16",
)
```

---

### Bookings (Read-Only)

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_bookings(**filters)` | List all bookings (individual + group + unavailable blocks) |
| GET | `get_booking(booking_id)` | Get a single booking |

**Filterable by:** `archived_at`, `business_id`, `cancelled_at`, `created_at`, `ends_at`, `id`, `patient_ids`, `practitioner_id`, `starts_at`, `updated_at`

---

### Availability Blocks

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_availability_blocks(**filters)` | List all availability blocks |
| GET | `get_availability_block(block_id)` | Get a single block |
| POST | `create_availability_block(starts_at, ends_at, practitioner_id, business_id, **kwargs)` | Create a block |

---

### Unavailable Blocks

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_unavailable_blocks(**filters)` | List all unavailable blocks |
| GET | `get_unavailable_block(block_id)` | Get a single block |
| POST | `create_unavailable_block(starts_at, ends_at, practitioner_id, business_id, **kwargs)` | Create a block |
| DELETE | `delete_unavailable_block(block_id)` | Delete a block |

---

### Contacts

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_contacts(**filters)` | List all contacts |
| GET | `get_contact(contact_id)` | Get a single contact |
| POST | `create_contact(first_name, last_name, country_code, **kwargs)` | Create a contact |
| PUT | `update_contact(contact_id, **kwargs)` | Update a contact |
| DELETE | `delete_contact(contact_id)` | Delete a contact |

**Create required fields:** `first_name`, `last_name`, `country_code` (ISO 3166-1, e.g. `"AU"`)

**Optional fields:** `address_1`, `city`, `email`, `phone_numbers`, `company_name`, `doctor_type` (`"general_practitioner"`, `"specialist"`, or `null`)

---

### Invoices (Read-Only)

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_invoices(**filters)` | List all invoices |
| GET | `list_deleted_invoices(**filters)` | List deleted invoices |
| GET | `get_invoice(invoice_id)` | Get a single invoice |
| GET | `list_invoices_for_patient(patient_id, **filters)` | Invoices for a patient |
| GET | `list_invoices_for_practitioner(practitioner_id, **filters)` | Invoices for a practitioner |

---

### Products

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_products(**filters)` | List all products |
| GET | `get_product(product_id)` | Get a single product |
| POST | `create_product(item_code, name, price, tax_id, **kwargs)` | Create a product |
| PUT | `update_product(product_id, **kwargs)` | Update (cannot update `stock_level`) |
| DELETE | `delete_product(product_id)` | Delete a product |

---

### Treatment Notes

| Method | Function | Description |
|--------|----------|-------------|
| GET | `list_treatment_notes(**filters)` | List all treatment notes |
| GET | `list_deleted_treatment_notes(**filters)` | List deleted notes |
| GET | `get_treatment_note(note_id)` | Get a single note |
| POST | `create_treatment_note(patient_id, content, **kwargs)` | Create a note |
| PUT | `update_treatment_note(note_id, **kwargs)` | Update a note |
| DELETE | `delete_treatment_note(note_id)` | Delete a note |

---

### Additional Read-Only Endpoints

| Function | Endpoint |
|----------|----------|
| `list_medical_alerts(**filters)` | `GET /medical_alerts` |
| `get_medical_alert(alert_id)` | `GET /medical_alerts/:id` |
| `list_medical_alerts_for_patient(patient_id)` | `GET /patients/:id/medical_alerts` |
| `list_patient_attachments(**filters)` | `GET /patient_attachments` |
| `get_patient_attachment(attachment_id)` | `GET /patient_attachments/:id` |
| `list_attachments_for_patient(patient_id)` | `GET /patients/:id/attachments` |
| `list_patient_cases(**filters)` | `GET /patient_cases` |
| `get_patient_case(case_id)` | `GET /patient_cases/:id` |
| `list_communications(**filters)` | `GET /communications` |
| `get_communication(communication_id)` | `GET /communications/:id` |
| `list_referral_sources(**filters)` | `GET /referral_sources` |
| `get_referral_source(source_id)` | `GET /referral_sources/:id` |
| `list_referral_source_types(**filters)` | `GET /referral_source_types` |
| `list_concession_types(**filters)` | `GET /concession_types` |
| `get_concession_type(concession_type_id)` | `GET /concession_types/:id` |
| `list_taxes(**filters)` | `GET /taxes` |
| `get_tax(tax_id)` | `GET /taxes/:id` |
| `get_settings()` | `GET /settings` |
| `list_users(**filters)` | `GET /users` |
| `get_user(user_id)` | `GET /users/:id` |
| `list_billable_items(**filters)` | `GET /billable_items` |
| `get_billable_item(item_id)` | `GET /billable_items/:id` |
| `list_services(**filters)` | `GET /services` |
| `get_service(service_id)` | `GET /services/:id` |
| `list_stock_adjustments(**filters)` | `GET /stock_adjustments` |
| `get_stock_adjustment(adjustment_id)` | `GET /stock_adjustments/:id` |
| `list_group_appointments(**filters)` | `GET /group_appointments` |
| `get_group_appointment(appointment_id)` | `GET /group_appointments/:id` |
| `list_attendees(**filters)` | `GET /attendees` |
| `get_attendee(attendee_id)` | `GET /attendees/:id` |
| `list_daily_availabilities(**filters)` | `GET /daily_availabilities` |
| `list_patient_forms(**filters)` | `GET /patient_forms` |
| `get_patient_form(form_id)` | `GET /patient_forms/:id` |
| `list_patient_form_templates(**filters)` | `GET /patient_form_templates` |
| `list_treatment_note_templates(**filters)` | `GET /treatment_note_templates` |
| `get_treatment_note_template(template_id)` | `GET /treatment_note_templates/:id` |
| `list_invoice_items(**filters)` | `GET /invoice_items` |
| `get_invoice_item(item_id)` | `GET /invoice_items/:id` |
| `list_practitioner_reference_numbers(**filters)` | `GET /practitioner_reference_numbers` |
| `get_practitioner_reference_number(ref_id)` | `GET /practitioner_reference_numbers/:id` |

---

## Running Tests

### Run all 83 tests

```bash
python -m pytest test_cliniko_api.py -v
```

### Run specific test categories

```bash
python -m pytest test_cliniko_api.py -v -k "Patient"         # Patient CRUD tests
python -m pytest test_cliniko_api.py -v -k "Appointment"      # Appointment tests
python -m pytest test_cliniko_api.py -v -k "Lifecycle"        # Full lifecycle test
python -m pytest test_cliniko_api.py -v -k "Connection"       # Auth tests
python -m pytest test_cliniko_api.py -v -k "ReadOnly"         # All read-only endpoints
python -m pytest test_cliniko_api.py -v -k "Contact"          # Contact CRUD
python -m pytest test_cliniko_api.py -v -k "Error"            # Error handling
```

### Test Coverage Summary (83 tests)

| Category | Count | What's Covered |
|----------|-------|----------------|
| Connection & Auth | 4 | Shard parsing, successful auth, invalid key (401) |
| Practitioners | 7 | List, get, inactive, by business, by appointment type, 404 |
| Businesses | 2 | List, get single |
| Patients | 9 | Create, list, get, update, archive/unarchive, deleted, archived, validation (422), 404 |
| Appointment Types | 5 | List, get, archived, by practitioner, full create/update/delete cycle |
| Individual Appointments | 12 | Create, get, list, deleted, cancelled, conflicts, reschedule, cancel with all 7 reason codes, delete + verify, validation, 404 |
| Appointment Lifecycle | 1 | End-to-end: create -> verify -> reschedule -> verify -> cancel |
| Bookings | 2 | List, 404 |
| Available Times | 2 | List available slots, next available time |
| Contacts | 3 | List, full CRUD cycle, 404 |
| Invoices | 4 | List, deleted, by patient, by practitioner |
| Read-Only Endpoints | 27 | Every remaining endpoint verified (settings, users, taxes, etc.) |
| Error Handling | 3 | Error class attributes, status codes, 404 |
| Filtering | 3 | Name filter, practitioner filter, pagination |

---

### Interactive Test CLI

```bash
python cliniko_api_test.py                  # Interactive menu
python cliniko_api_test.py --list-resources # List practitioners, types, businesses, patients
python cliniko_api_test.py --run-all        # Run full booking lifecycle demo
```

---

## Project Structure

```
talkaflow-cliniko/
  cliniko_api.py          # API client module (import this in your apps)
  test_cliniko_api.py     # 83 integration tests (pytest)
  cliniko_api_test.py     # Interactive CLI test tool
  README.md               # This file
  .gitignore              # Git ignore rules
```

---

## References

- [Cliniko API Documentation](https://docs.api.cliniko.com/developer-portal)
- [Cliniko Help - Generate an API Key](https://help.cliniko.com/en/articles/1023957-generate-a-cliniko-api-key)
- [Cliniko API GitHub (archived)](https://github.com/redguava/cliniko-api)
>>>>>>> 42e61f3 (Add Cliniko API client, integration tests, and documentation)
