# Car Rental API

[![Framework](https://img.shields.io/badge/Framework-FastAPI-green)](https://fastapi.tiangolo.com/)
[![Language](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![ORM](https://img.shields.io/badge/ORM-SQLModel-informational)](https://sqlmodel.tiangolo.com/)
[![Auth](https://img.shields.io/badge/Auth-JWT%20%2B%20CSRF-critical)](https://fastapi.tiangolo.com/tutorial/security/)

A comprehensive and secure backend API for a car rental platform. This project is built with FastAPI and SQLModel, and it features a robust authentication system, reservation management, and a full-featured admin portal.

The purpose of this project was to build a production-ready, secure, and efficient backend system.

* **Secure Authentication:**
    * Implements a modern JWT sytem with short-lived access tokens and long-lived refresh tokens.
    * **HttpOnly Cookies:** Stores refresh tokens in secure, `HttpOnly` cookies to prevent access from client-side scripts (XSS attacks).
    * **CSRF Protection:** Implements a true logout by invalidating (deleting) refresh tokens from the database.
    * **Strong Hashing:** Uses `passlib` with the modern `argon2` algorithm for securely hashing passwords.

* **Admin Panel & Role-Based Access:**
    * Clear distinction between standard user and admin roles, with protected admin-only endpoints.
    * Full CRUD (**C**reate, **R**ead, **U**pdate, **D**elete) functionality for managing cars and reservations.
    * **Efficient Pagination:** Uses cursor-based pagination for all admin lists (e.g., `get_reservations`, `get_cars`), which is more performant for large datasets than traditional offset pagination.

* **Reservation & Car Management:**
    * **Database-Level Integrity:** Uses a PostgreSQL `EXCLUDE` constraint to make it impossible for overlapping reservations for the same car to be entered into the database, protecting against race conditions.
    * **Application-Level Checks:** The API checks for conflicting reservations before attempting an insert.
    * **External Image Uploads:** Integrates with ImageKit for handling image uploads, leeping the API server and database light.
    * **Form & File Hanlding:** Demonstrates handling `multipart/form-data` for adding new cars, processing both form fields (`CarBase.as_form`) and file uploads (`List[UploadFile]`) in a single endpoint.

* **User Features:**
    * Authenticated users can view their own reservation history (active or inactive).
    * Users can cancel their own pending or confirmed reservations, but not those that are already completed, active, or cancelled.

## Technology Stack

* **Framework:** **FastAPI**
* **Database/ORM:** **SQLModel** (built on Pydantic and SQLAlchemy)
* **Database:** **PostgreSQL** (via `psycopg`)
* **Authentication:** **`python-jose`** for JWT, **`passlib[argon2]`** for hashing
* **Image Storage:** **ImageKit.io**
* **Server:** **Uvicorn**

## Setup and Installation

Follow these steps to get the project running locally.

### 1. Prerequisites

* Python 3.10+
* A running PostgreSQL database

### 2. Clone & Install

```
bash 
# Clone the repository
git clone [https://github.com/richiedlrsa/car-rental-backend.git](https://github.com/richiedlrsa/car-rental-backend.git)
cd car-rental-backend

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate # (or .\.venv\Scripts\active on Windows)

# Install the dependencies
pip install -r requirements.txt
```

### 3. Environment Variables

Create a file named `.env` in the root of the project and add the following variables.

```
.env
# Database (update with your credentials)
DB_URL=postgresql+psycopg://postgres:your_password@localhost:5432/car_rental_d

# JWT (generate a strong random string)
# You can use: openssl rand -hex 32
SECRET_KEY=your_very_string_32_character_secret_key
ALGORITHM=HS256

# ImageKit (get these from your ImageKit.io dashboard)
IK_PRIVATE=your_imagekit_private_key
IK_PUBLIC=your_imagekit_public_key
IK_URL=your_imagekit_url_endpoint
```

### 4. Database Setup (Optional but Highly Recommended)

This step adds a database-level constraint to guarantee data integrity and preven race conditions where two reservations might be created for the same car at the same time.

1. Connect to your PostgreSQL database (e.g., using `pgAdmin 4`).
2. Run the following command to enable the `btree_gist` extension:

    ```
    CREATE EXTENSION IF NOT EXISTS btree_gist
    ```
3. Next, apply the exclusion constraint to the `reservations` table. This constraint uses a GIST index to ensure no two "active" (`pending`, `active`, or `confirmed`) reservations for the *same* `car_id` have *overlapping* date ranges.

    ```
    ALTER TABLE reservations
    ADD CONSTRAINT reservation_no_overlap
    EXCLUDE USING gist (
        car_id WITH =,
        daterange(start_at, end_at, '[]') WITH &&
    )
    WHERE (status IN ('pending', 'active', 'confirmed'));
    ```

### 5. Run the Application

The application uses `create_db_and_tables()` to automatically create the database tables on startup.

```
bash
# Run the server with auto-reload
unvicorn main:app --reload
```

The API will be live at `http://127.0.0.1:8000`, and the interactive documentation (Swagger UI) will be available `http://127.0.0.1:8000/docs`.

## API Endpoint Structure

* `/user/`: Handles user registration, login, logout, token refreshing, and fetching the current user (`/me`).
* `/cars/`: Manages public car listings, checking availability, and admin-only car creation.
* `/reservations/`: Handles creation, viewing, and canceling of reservations by authenticated users.
* `/admin/`: Provides protected endpoints for managing the full lifecycle of cars and reservations (viewing, approving, canceling, deleting).

## Testing

This project includes a test suite built with pytest. The tests cover unit-level functionality (like token generation and password hashing) as well as integration-level API testing (like user registration, login flows, and reservation conflicts).

### Test environment setup

The test suite is designed to run against a live database. It's highly recommended to use a separate database and a .env.test file.

1. Create `.env.test`: In your project root, create this file. It should point to a separate test database.
```
# Point to a test database
DB_URL=postgresql+psycopg://postgres:your_password@localhost:5432/car_rental_test

# Use the same secrets as your main .env
SECRET_KEY=your_very_string_32_character_secret_key
ALGORITHM=HS256
# ... (include any other required env vars) ...
```

2. Create a pytest.ini: 
```
[pytest]
env_files =
    .env.test
```

### Running the Tests

**Important:** all tests must be run using the `pytest` command from the project's root directory. This allows the test files to use absolute imports like `from backend.models import Users`.

Running the files directly (e.g., python backend/testing/test_auth.py) will fail with a ModlueNotFoundError or ImportError.

### Test Coverage Overview
The suite is structured to test all critical components of the API:
* TestAuth (Authentication Flow):
    * Uses a pytest fixture to generate test user data
    * Tests the full user lifecycle:
     * Successful registration (`200 ok`)
     * Duplicate email (`409 conflict`)
     * Login with correct and incorrect credentials (`200 OK, 401 Unauthorized`)
     * Token refresh flow with CSRF validation(`200 ok, 403 Forbidden`)
     * Secure logout (verifying the refresh token is deleted from the DB)
* TestJwt (Token Security):
    * A pure unit test that validates the `create_access_token` and `create_refresh_token` functions
    * Assert that the token payloads (`sub`, `type`, `jti`) are correct
    * Verifies security by asserting that `pytest.raises(JWTError)` is triggered when decoding with an incorrect `SECRET KEY` or `access_token`
* TestReservations (Business Logic)
    * Uses a fixture to create a `Car` for the test
    * Confirms that a valid reservation returns a `200 ok`
    * Critically, it tests the reservation conflict logic, asserting that an overlapping booking for the same car returns a `409 Conflict`
* TestUserAuth (Hashing)
    * A simple, fast unit test to confirm that `hash_password` and `verify_password` are working correctly