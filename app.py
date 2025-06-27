from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
import datetime
from flask import send_file
from io import BytesIO
import pdfkit  # Ensure you have wkhtmltopdf installed for pdfkit to work

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'KuiMaina1',
    'database': 'rental_management'
}

# Load tenants from the DB
def load_tenants():
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tenants ORDER BY unit_number")
    tenants = cursor.fetchall()
    cursor.close()
    conn.close()
    return tenants

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/tenants")
def view_tenants():
    tenants = load_tenants()
    return render_template("view_tenants.html", tenants=tenants)

@app.route("/add-tenant", methods=["GET", "POST"])
def add_tenant():
    if request.method == "POST":
        unit = request.form['unit']
        meter = request.form['meter']
        reading = int(request.form['reading'])

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO tenants (unit_number, meter_number, previous_reading, current_reading)
                VALUES (%s, %s, %s, %s)
            """, (unit, meter, reading, reading))
            conn.commit()
            flash("Tenant added successfully!", "success")
        except Error as e:
            flash(f"Error adding tenant: {e}", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("view_tenants"))
    return render_template("add_tenant.html")

# Handles GET and POST methods for /record-readings
# Retrieves tenant data and processes new readings from the form
# Validates that current reading is not less than the previous
# Calculates usage and bill amount per tenant
# Updates readings in the database
# Displays a bill summary after successful submission
# Includes flash message feedback for errors and validation

@app.route("/record-readings", methods=["GET", "POST"])
def record_readings():
    tenants = load_tenants()

    if request.method == "POST":
        updates = []
        bills = []
        for tenant in tenants:
            unit = tenant["unit_number"]
            prev = tenant["previous_reading"]
            current = int(request.form.get(f"reading_{unit}", prev))

            if current < prev:
                flash(f"Error for Unit {unit}: current reading cannot be less than previous.", "danger")
                return redirect(url_for("record_readings"))

            usage = current - prev
            bill = usage * WATER_RATE_PER_UNIT  # no base fee in your code
            updates.append((current, current, unit))
            bills.append({
                "unit": unit,
                "meter": tenant["meter_number"],
                "previous": prev,
                "current": current,
                "usage": usage,
                "bill": bill
            })

        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            for new_prev, new_curr, unit in updates:
                cursor.execute("""
                    UPDATE tenants
                    SET previous_reading = %s, current_reading = %s
                    WHERE unit_number = %s
                """, (new_prev, new_curr, unit))
            conn.commit()
            cursor.close()
            conn.close()
        except Error as e:
            flash(f"Database update failed: {e}", "danger")
            return redirect(url_for("record_readings"))

        return render_template("bill_summary.html", bills=bills, currency=CURRENCY_SYMBOL)

    return render_template("record_readings.html", tenants=tenants)


# Fetches tenant data from the database based on unit number
# Calculates water usage and total amount due
# Renders invoice template with billing details
# Includes error handling for non-existent tenants with flash messaging
# Prepares for potential PDF generation with tools like pdfkit or WeasyPrint
@app.route("/invoice/<unit>")
def generate_invoice(unit):
    # Fetch tenant data
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM tenants WHERE unit_number = %s", (unit,))
    tenant = cursor.fetchone()
    cursor.close()
    conn.close()

    if not tenant:
        flash("Tenant not found", "danger")
        return redirect(url_for("view_tenants"))

    usage = tenant['current_reading'] - tenant['previous_reading']
    amount_due = usage * WATER_RATE_PER_UNIT

    return render_template("invoice.html", tenant=tenant, usage=usage, bill=amount_due, currency=CURRENCY_SYMBOL)