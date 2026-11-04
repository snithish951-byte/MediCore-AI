import os
from flask import (
    Flask, render_template, request,
    redirect, url_for, session
)
from functools import wraps
from database import get_connection

app = Flask(__name__)

app.secret_key = "CHANGE_TO_YOUR_OWN_RANDOM_SECRET"


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db_cursor():

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    return connection, cursor


# ==========================================
# LOGIN PROTECTION
# ==========================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("home"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# DISEASE MATCHING
# ==========================================

def find_disease_matches(cursor, symptom_ids):

    if not symptom_ids:
        return []

    placeholders = ",".join(
        ["%s"] * len(symptom_ids)
    )

    query = f"""
        SELECT
            d.id,
            d.disease_name,
            d.description,
            d.precautions,
            COUNT(DISTINCT ds.symptom_id) AS matched_symptoms,
            ROUND(
                COUNT(DISTINCT ds.symptom_id) * 100.0 /
                NULLIF(
                    (
                        SELECT COUNT(*)
                        FROM disease_symptoms ds2
                        WHERE ds2.disease_id = d.id
                    ),
                    0
                ),
                2
            ) AS match_percentage

        FROM diseases d

        JOIN disease_symptoms ds
            ON d.id = ds.disease_id

        WHERE ds.symptom_id IN ({placeholders})

        GROUP BY
            d.id,
            d.disease_name,
            d.description,
            d.precautions

        ORDER BY
            matched_symptoms DESC,
            match_percentage DESC
    """

    cursor.execute(query, tuple(symptom_ids))

    return cursor.fetchall()


# ==========================================
# LOGIN
# ==========================================

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        connection = None
        cursor = None

        try:

            connection, cursor = get_db_cursor()

            cursor.execute(
                """
                SELECT id, email
                FROM users
                WHERE email = %s AND password = %s
                """,
                (email, password)
            )

            user = cursor.fetchone()

            if user:

                session.clear()
                session["user_id"] = user["id"]
                session["email"] = user["email"]

                return redirect(url_for("dashboard"))

            return render_template(
                "login.html",
                message="Invalid email or password."
            )

        except Exception as error:

            app.logger.exception("LOGIN ERROR")
            return "Login error. Check the IDLE Shell."

        finally:

            if cursor:
                cursor.close()

            if connection:
                connection.close()

    return render_template("login.html")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
@login_required
def logout():

    session.clear()

    return redirect(url_for("home"))


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    user = {
        "email": session.get("email"),
        "user_id": session.get("user_id")
    }

    return render_template(
        "dashboard.html",
        user=user
    )


# ==========================================
# PROFILE
# ==========================================

@app.route("/profile")
@login_required
def profile():

    connection = None
    cursor = None

    try:

        connection, cursor = get_db_cursor()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE id = %s
            """,
            (session["user_id"],)
        )

        user = cursor.fetchone()

        return render_template(
            "profile.html",
            user=user
        )

    except Exception:

        app.logger.exception("PROFILE ERROR")
        return "Profile error. Check the IDLE Shell."

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# MEDICAL HISTORY
# ==========================================

@app.route("/medical-history")
@login_required
def medical_history():

    connection = None
    cursor = None

    try:

        connection, cursor = get_db_cursor()

        cursor.execute(
            """
            SELECT *
            FROM patient_history
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (session["user_id"],)
        )

        history = cursor.fetchall()

        return render_template(
            "medical_history.html",
            history=history
        )

    except Exception:

        app.logger.exception("MEDICAL HISTORY ERROR")
        return "Medical history error. Check the IDLE Shell."

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# PREVIOUS RESULTS
# ==========================================

@app.route("/previous-results")
@login_required
def previous_results():

    connection = None
    cursor = None

    try:

        connection, cursor = get_db_cursor()

        cursor.execute(
            """
            SELECT *
            FROM diagnosis_records
            WHERE user_id = %s
            ORDER BY id DESC
            """,
            (session["user_id"],)
        )

        results = cursor.fetchall()

        return render_template(
            "previous_results.html",
            results=results
        )

    except Exception:

        app.logger.exception("PREVIOUS RESULTS ERROR")
        return "Previous results error. Check the IDLE Shell."

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# VIEW REPORT
# ==========================================

@app.route('/view-report/<int:report_id>')
def view_report(report_id):

    connection = None
    cursor = None

    try:

        connection, cursor = get_db_cursor()

        cursor.execute(
            """
            SELECT *
            FROM patient_history
            WHERE id = %s AND user_id = %s
            """,
            (report_id, session["user_id"])
        )

        report = cursor.fetchone()

        if not report:
            return "Report not found."

        return render_template(
            "view_report.html",
            report=report
        )

    except Exception:

        app.logger.exception("REPORT ERROR")
        return "Report error. Check the IDLE Shell."

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# SYMPTOM CHECKER
# ==========================================

@app.route("/symptom-checker", methods=["GET", "POST"])
@login_required
def symptom_checker():

    connection = None
    cursor = None

    try:

        connection, cursor = get_db_cursor()

        cursor.execute(
            """
            SELECT id, symptom_name
            FROM symptoms
            ORDER BY symptom_name
            """
        )

        symptoms = cursor.fetchall()

        message = None

        if request.method == "POST":

            selected = request.form.getlist("symptoms")

            if not selected:

                message = "Please select at least one symptom."

            else:

                try:

                    symptom_ids = list(set(
                        int(value) for value in selected
                    ))

                    valid_ids = {
                        int(item["id"]) for item in symptoms
                    }

                    if not set(symptom_ids).issubset(valid_ids):
                        raise ValueError

                except (ValueError, TypeError):

                    symptom_ids = []
                    message = "Invalid symptom selection."

                if symptom_ids:

                    results = find_disease_matches(
                        cursor,
                        symptom_ids
                    )

                    return render_template(
                        "symptom_results.html",
                        results=results
                    )

        return render_template(
            "symptom_checker.html",
            symptoms=symptoms,
            message=message
        )

    except Exception:

        app.logger.exception("SYMPTOM CHECKER ERROR")

        return (
            "Symptom Checker could not load. "
            "Please check the IDLE Shell for the exact error."
        )

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# PATIENT ASSESSMENT
# ==========================================

@app.route("/patient-assessment", methods=["GET", "POST"])
@login_required
def patient_assessment():

    if request.method == "GET":

        return render_template("patient_assessment.html")

    connection = None
    cursor = None

    try:

        patient_name = request.form.get(
            "patient_name", ""
        ).strip()

        gender = request.form.get("gender", "")
        age = request.form.get("age", "")
        symptoms_text = request.form.get(
            "symptoms", ""
        ).strip()

        if not patient_name or not symptoms_text:
            return "Patient name and symptoms are required."

        age_value = int(age) if age else None

        if age_value is not None and not 0 <= age_value <= 120:
            return "Please enter a valid age."

        connection, cursor = get_db_cursor()

        cursor.execute(
            """
            SELECT id, symptom_name
            FROM symptoms
            """
        )

        all_symptoms = cursor.fetchall()

        patient_text = symptoms_text.lower()

        matched = [
            symptom for symptom in all_symptoms
            if symptom["symptom_name"].strip().lower()
            in patient_text
        ]

        symptom_ids = [
            item["id"] for item in matched
        ]

        results = find_disease_matches(
            cursor,
            symptom_ids
        )

        if results:

            diagnosis = results[0]["disease_name"]
            confidence = results[0]["match_percentage"]

        else:

            diagnosis = "No matching condition found"
            confidence = None

        cursor.execute(
            """
            INSERT INTO patient_history
            (
                user_id,
                patient_name,
                age,
                gender,
                symptoms,
                previous_diseases,
                diagnosis_result
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                session["user_id"],
                patient_name,
                age_value,
                gender,
                symptoms_text,
                request.form.get("previous_diseases", ""),
                diagnosis
            )
        )

        cursor.execute(
            """
            INSERT INTO diagnosis_records
            (
                user_id,
                result,
                confidence
            )
            VALUES (%s, %s, %s)
            """,
            (
                session["user_id"],
                diagnosis,
                confidence
            )
        )

        connection.commit()

        patient = {
            "patient_name": patient_name,
            "gender": gender,
            "age": age,
            "temperature": request.form.get("temperature", ""),
            "blood_pressure": request.form.get("blood_pressure", ""),
            "blood_sugar": request.form.get("blood_sugar", ""),
            "blood_group": request.form.get("blood_group", ""),
            "pulse_rate": request.form.get("pulse_rate", ""),
            "saturation": request.form.get("saturation", ""),
            "heart_rate": request.form.get("heart_rate", ""),
            "ecg": request.form.get("ecg", ""),
            "symptoms": symptoms_text
        }

        return render_template(
            "analysis.html",
            patient=patient,
            matched=matched,
            results=results
        )

    except ValueError:

        return "Please enter a valid age."

    except Exception:

        if connection:
            connection.rollback()

        app.logger.exception("PATIENT ASSESSMENT ERROR")

        return "Assessment error. Check the IDLE Shell."

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ==========================================
# RUN APPLICATION
# ==========================================
if __name__ == "__main__":

    print("MEDICORE AI STARTING...")

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        use_reloader=False,
        threaded=True
    )
