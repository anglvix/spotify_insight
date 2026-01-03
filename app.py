from flask import Flask, render_template, request, redirect, session
import pandas as pd
import plotly.express as px
import mysql.connector

app = Flask(__name__)
app.secret_key = "segredo_simples"

# Ativa debug para ver erros no terminal
app.debug = True

# -----------------------
# Função para ligar à base de dados MySQL
# -----------------------
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="", 
        database="spotify_insight"
    )

# -----------------------
# Página inicial
# -----------------------
@app.route("/")
def index():
    if "user" in session:
        return redirect("/dashboard")
    return redirect("/login")

# -----------------------
# Registo
# -----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nome = request.form["nome"]
        email = request.form["email"]
        password = request.form["password"]  # SEM HASH

        db = get_db()
        c = db.cursor()
        c.execute(
            "INSERT INTO users (nome,email,password,role) VALUES (%s,%s,%s,%s)",
            (nome,email,password,"user")
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
        c.execute(
            "SELECT * FROM users WHERE email=%s AND password=%s",
            (email, password)
        )
        user = c.fetchone()
        db.close()

        if user:
            session["user"] = user[1]
            session["role"] = user[4]
            return redirect("/dashboard")

        return "Email ou password errados!"

    return render_template("login.html")

# -----------------------
# Dashboard
# -----------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    df = pd.read_csv("datasets/spotify.csv")

    # Tabela simples
    table = df.head(20).to_html()

    # Gráfico Top 10 artistas
    top_artists = df.groupby("artist")["play_count"].sum().reset_index()
    fig = px.bar(
        top_artists.sort_values("play_count", ascending=False).head(10),
        x="artist",
        y="play_count",
        title="Top 10 Artistas Mais Ouvidos"
    )
    graph = fig.to_html(full_html=False)

    return render_template("dashboard.html", table=table, graph=graph)

# -----------------------
# Página Admin
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

# -----------------------
# Executar app
# -----------------------
if __name__ == "__main__":
    app.run(debug=True)
