from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
import datetime

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