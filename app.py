from flask import Flask, render_template, request, redirect, session
import pandas as pd
import plotly.express as px
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "segredo_simples"

# ------------------------ MySQL
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="spotify_insight"
    )

@app.route("/")
def index():
    return redirect("/login")

# -----------------------
# Registo
# -----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        db = get_db()
        c = db.cursor()
        c.execute(
            "INSERT INTO users VALUES (NULL,%s,%s,%s,%s)",
            (nome, email, password, "user")
        )
        db.commit()
        db.close()
        return redirect("/login")

    return render_template("register.html")

# -----------------------
# Login
# -----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = c.fetchone()
        db.close()

        if user and check_password_hash(user[3], password):
            session["user"] = user[1]
            session["role"] = user[4]
            return redirect("/dashboard")

    return render_template("login.html")

# -----------------------
# Dashboard
# -----------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    df = pd.read_csv("datasets/spotify.csv")

    table = df.head(20).to_html()

    top = df.groupby("artist")["play_count"].sum().reset_index()
    fig = px.bar(top.sort_values("play_count", ascending=False).head(10),
                 x="artist", y="play_count",
                 title="Top 10 Artistas")
    graph = fig.to_html(full_html=False)

    return render_template("dashboard.html", table=table, graph=graph)

# -----------------------
# Admin
# -----------------------
@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/dashboard")

    db = get_db()
    c = db.cursor()
    c.execute("SELECT id,nome,email,role FROM users")
    users = c.fetchall()
    db.close()

    return render_template("admin.html", users=users)

# -----------------------
# Logout
# -----------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

app.run(debug=True)