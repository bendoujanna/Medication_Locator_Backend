# MedLocator - Backend API

Django REST Framework backend for MedLocator, a location-aware medicine availability
platform designed for under-resourced healthcare communities in sub-Saharan Africa.
The backend exposes a REST API consumed by the React frontend and handles clinic
inventory management, patient hold requests, Firebase authentication, and real-time
stock alerts.

---

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Local Setup](#local-setup)
- [Environment Variables](#environment-variables)
- [Firebase Setup](#firebase-setup)
- [Running the Server](#running-the-server)
- [Seeding the Database](#seeding-the-database)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Key Design Decisions](#key-design-decisions)

---

## Overview

MedLocator addresses a critical information gap in regional African healthcare: patients
have no way to know which nearby clinic has the medicine they need, leading to dangerous
delays and wasted transport costs. This backend powers two interfaces:

- A public-facing client portal where patients search for medicines, view real-time stock
  availability as a traffic-light system, and place 2-hour hold requests
- A clinic staff dashboard where pharmacists manage inventory, process hold requests,
  and receive automated low-stock alerts

---

## Tech Stack

| Technology | Version | Purpose |
|---|---|---|
| Python | 3.11+ | Runtime |
| Django | 5.0.6 | Web framework |
| Django REST Framework | 3.15.2 | API layer |
| PostgreSQL | 15+ | Primary database |
| Firebase Admin SDK | 6.5.0 | Authentication and user provisioning |
| django-apscheduler | 0.6.2 | Scheduled hold expiry and PHI purge |
| Gunicorn | 22.0.0 | WSGI server (production) |
| WhiteNoise | 6.7.0 | Static file serving (production) |

---

## Project Structure

```
medlocator-backend/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── config/
│   ├── settings.py          # Single settings file, environment-controlled
│   ├── urls.py              # Root URL router
│   ├── wsgi.py
│   └── asgi.py
├── authentication/
│   ├── firebase.py          # Firebase token verification and user provisioning
│   ├── permissions.py       # RBAC permission classes
│   ├── serializers.py       # Staff profile serializer
│   └── views.py             # /auth/me/ and /health/ endpoints
├── clinics/
│   ├── models.py            # Clinic, ClinicStaff
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── medications/
│   ├── models.py            # ActiveIngredient, Medication
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── management/
│       └── commands/
│           └── seed_eml.py  # Populates the Essential Medicines List
├── inventory/
│   ├── models.py            # Inventory, StockAlert
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── apps.py              # Registers post_save signal
├── holds/
│   ├── models.py            # HoldRequest with PHI purge logic
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── tasks.py             # Scheduled expiry job
│   └── apps.py              # Starts the background scheduler
└── search/
    ├── views.py             # Public search, substitutes, map pins, OSRM proxy
    ├── serializers.py
    ├── urls.py
    └── utils.py             # Haversine distance calculation, OSRM client
```

---

## Prerequisites

Before setting up the project, make sure the following are installed:

- Python 3.11 or higher
- PostgreSQL 15 or higher
- A Firebase project with Email/Password authentication enabled
- pip and virtualenv (or venv)

---

## Local Setup

**1. Clone the repository**

```bash
git clone https://github.com/your-username/medlocator-backend.git
cd medlocator-backend
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv

# macOS and Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Create the PostgreSQL database**

```bash
psql -U postgres
CREATE DATABASE medlocator;
CREATE USER medlocator_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE medlocator TO medlocator_user;
\q
```

**5. Set up environment variables**

```bash
cp .env.example .env
```

Open `.env` and fill in all required values. See the Environment Variables section below
for a full description of each variable.

**6. Run database migrations**

```bash
python manage.py makemigrations authentication
python manage.py makemigrations clinics
python manage.py makemigrations medications
python manage.py makemigrations inventory
python manage.py makemigrations holds
python manage.py makemigrations search
python manage.py migrate
```

**7. Seed the Essential Medicines List**

```bash
python manage.py seed_eml
```

This populates the `ActiveIngredient` and `Medication` tables with 10 essential
ingredients and their common brand-name variants. The command is idempotent and safe
to run multiple times.

**8. Create a Django superuser**

```bash
python manage.py createsuperuser
```

The superuser account is used to access the Django admin panel and provision the first
clinic via the API. It does not use Firebase authentication.

**9. Start the development server**

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`. Confirm it is running by visiting
`http://localhost:8000/api/v1/health/`, which should return `{"status": "ok"}`.

---

## Environment Variables

Copy `.env.example` to `.env` and set the following:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Django secret key. Generate one with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | Yes | Set to `True` for local development, `False` in production |
| `ALLOWED_HOSTS` | Yes | Comma-separated list of allowed hosts, e.g. `localhost,127.0.0.1` |
| `DB_NAME` | Yes | PostgreSQL database name |
| `DB_USER` | Yes | PostgreSQL username |
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `DB_HOST` | Yes | Database host, typically `localhost` for local development |
| `DB_PORT` | Yes | Database port, typically `5432` |
| `FIREBASE_CREDENTIALS_PATH` | Yes | Absolute path to your Firebase service account JSON file |
| `CORS_ALLOWED_ORIGINS` | Yes | Comma-separated origins allowed to call the API, e.g. `http://localhost:5173` |
| `OSRM_BASE_URL` | No | OSRM routing engine URL. Defaults to the public instance at `http://router.project-osrm.org` |

---

## Firebase Setup

Authentication is delegated entirely to Firebase. Django never stores or validates
passwords. Follow these steps to configure Firebase:

**1. Create a Firebase project**

Go to the [Firebase Console](https://console.firebase.google.com) and create a new project.

**2. Enable Email/Password authentication**

In your project, navigate to Authentication > Sign-in method and enable the
Email/Password provider.

**3. Download the service account key**

Navigate to Project Settings > Service Accounts > Generate New Private Key.
Download the JSON file and store it somewhere safe on your machine.

Set `FIREBASE_CREDENTIALS_PATH` in your `.env` to the absolute path of this file,
for example:

```
FIREBASE_CREDENTIALS_PATH=/home/yourname/keys/medlocator-serviceAccountKey.json
```

**Important:** Never commit this file to version control. It is included in `.gitignore`
by default. Treat it like a password.

**4. Provision the first staff account**

Once the server is running, use the Postman collection (see API Reference below) to
create a clinic and then provision a staff member. The provisioning endpoint creates
a Firebase user and a Django `ClinicStaff` record simultaneously, in a single
atomic operation. If either step fails, the other is rolled back.

---

## Running the Server

**Development**

```bash
python manage.py runserver
```

**Production (Gunicorn)**

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2
```

---

## Seeding the Database

The `seed_eml` management command loads the Essential Medicines List, which is the
reference dataset all medication searches are built on. It is safe to run multiple
times as it uses `get_or_create` to avoid duplicates.

```bash
python manage.py seed_eml
```

After seeding, the following active ingredients are available:
Paracetamol, Amoxicillin, Oral Rehydration Salts, Ibuprofen, Azithromycin,
Metformin, Artemether/Lumefantrine, Amoxicillin/Clavulanate, Ciprofloxacin, Salbutamol.

---

## API Reference

All API endpoints have been tested on Postman. 

[API endpoints documentation](https://docs.google.com/document/d/1xkSXa8PQplb02rruqD7dzq7YzElDwl7n_t6hLK-WJy8/edit?usp=sharing)

**Endpoint groups**

| Group | Base path | Auth |
|---|---|---|
| Health check | `/api/v1/health/` | None |
| Authentication | `/api/v1/auth/` | Firebase Bearer token |
| Clinics | `/api/v1/clinics/` | Firebase Bearer token |
| Ingredients (EML) | `/api/v1/ingredients/` | None (read), Firebase (write) |
| Medications | `/api/v1/medications/` | None (read), Firebase (write) |
| Inventory | `/api/v1/clinics/{id}/inventory/` | Firebase Bearer token |
| Stock Alerts | `/api/v1/clinics/{id}/alerts/` | Firebase Bearer token |
| Hold Requests (client) | `/api/v1/hold-requests/` | None |
| Hold Requests (clinic) | `/api/v1/clinics/{id}/hold-requests/` | Firebase Bearer token |
| Search | `/api/v1/search/` | None |
| Routing proxy | `/api/v1/routing/` | None |

---

## Authentication

The backend uses Firebase Authentication for all clinic staff. The flow is:

1. The React frontend calls Firebase directly with the staff member's email and password.
2. Firebase returns a short-lived ID token to the browser.
3. The frontend attaches this token to every API request as `Authorization: Bearer <token>`.
4. The `FirebaseAuthentication` class in `authentication/firebase.py` verifies the token
   on every incoming request using the Firebase Admin SDK.
5. After verification, it looks up the matching `ClinicStaff` record by `firebase_uid`
   and attaches it to the request as `request.clinic_staff`.
6. Permission classes then read `request.clinic_staff.role` to enforce RBAC.

Public endpoints (patient search, hold request creation and tracking, health check) have
no authentication requirement.

**Role-Based Access Control**

| Role | Capabilities |
|---|---|
| `STANDARD_PHARMACIST` | View and update inventory, process hold requests, view stock alerts |
| `ADMINISTRATOR` | All pharmacist capabilities plus staff management, facility profile editing, alert threshold configuration |

---

## Running Tests

```bash
python manage.py test
```

Test factories are available via `factory-boy`. Individual app tests can be run with:

```bash
python manage.py test authentication
python manage.py test clinics
python manage.py test inventory
python manage.py test holds
python manage.py test search
```

---

## Deployment

The application is designed to deploy on Render.com's free tier.

**Build command**

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Start command**

```bash
gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2
```

**Environment variables**

Set all variables from the Environment Variables section above in the Render dashboard
under Environment. Set `DEBUG=False` and `ALLOWED_HOSTS` to your Render domain.

**Keep-warm configuration**

Render's free tier spins down services after 15 minutes of inactivity, causing cold
start delays of 30-60 seconds. To meet the 99% uptime requirement, set up a free
UptimeRobot monitor targeting `https://your-app.onrender.com/api/v1/health/` with a
10-minute check interval.

---

## Key Design Decisions

**Single settings file**
All configuration is controlled through environment variables in a single `config/settings.py`
file rather than separate development and production settings files. The `DEBUG` environment
variable controls which behavior is active, keeping the configuration simple and the
deployment process straightforward.

**Firebase for authentication, Django for authorization**
Firebase handles credential storage, password validation, and token issuance. Django
handles role resolution and resource-level permission checks. This separation means
Django never stores passwords and benefits from Firebase's security infrastructure
without the complexity of a custom authentication system.

**Status computed on save**
The `Inventory.status` field is always computed from `quantity_on_hand` and
`low_stock_threshold` inside `Inventory.save()`. No view or serializer ever sets this
field directly. This guarantees the status is always correct regardless of which
code path triggered the save.

**PHI purge on resolution**
The patient phone number collected during a hold request (`patient_contact`) is the only
piece of Protected Health Information the system ever stores. It is permanently deleted
the moment the hold is resolved (approved, denied, or expired) via `HoldRequest.purge_phi()`.
The scheduled task in `holds/tasks.py` enforces this for expired holds every 5 minutes.

**Polling instead of WebSockets**
The clinic dashboard and client hold tracker both use client-side polling at 30-second
intervals rather than persistent WebSocket connections. This is a deliberate constraint
to maintain zero infrastructure cost on the free hosting tier.
