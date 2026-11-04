import re
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import IntegrityError
from database import get_connection

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def register_user(email, password):
    """Registers a normal patient account. Admins are created manually."""
    email = (email or "").strip().lower()

    if not EMAIL_PATTERN.match(email) or len(email) > 100:
        return False, "Enter a valid email address."
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters."

    password_hash = generate_password_hash(password)

    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (email, password, role) VALUES (%s, %s, %s)",
            (email, password_hash, "patient"),
        )
        connection.commit()
        return True, "Registration successful."

    except IntegrityError:
        connection.rollback()
        return False, "This email is already registered."

    except Exception:
        connection.rollback()
        return False, "Registration failed. Please try again."

    finally:
        cursor.close()
        connection.close()


def login_user(email, password):
    email = (email or "").strip().lower()

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id, email, password, role FROM users WHERE email = %s",
            (email,),
        )
        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password or ""):
            del user["password"]  # never pass the hash around
            return True, user

        return False, None

    finally:
        cursor.close()
        connection.close()
