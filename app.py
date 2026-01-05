from flask import Flask, render_template, request, redirect, session
import csv
import os
import pandas as pd
import plotly.express as px

app = Flask(__name__)
app.secret_key = "segredo_simples"

# -------------------------
# Caminhos
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(BASE_DIR, "users.csv")
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
SPOTIFY_CSV = os.path.join(DATASETS_DIR, "spotify.csv")  # o teu dataset

# -------------------------
# Funções de utilizadores
# -------------------------
def read_users():
    users = []
    if not os.path.exists(USERS_FILE):
        return users
    with open(USERS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.append(row)
    return users

def add_user(nome, email, password):
    file_exists = os.path.exists(USERS_FILE)
    with open(USERS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["id","nome","email","password","role"])
        users = read_users()
        new_id = len(users) + 1
        writer.writerow([new_id, nome, email, password, "user"])

# -------------------------
# Rotas
# -------------------------
@app.route("/", methods=["GET","POST"])
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        for user in read_users():
            if user["email"] == email and user["password"] == password:
                session["user"] = user["nome"]
                session["role"] = user["role"]
                return redirect("/dashboard")
        return "Login inválido"
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        password = request.form.get("password")
        for u in read_users():
            if u["email"] == email:
                return "Email já existe!"
        add_user(nome,email,password)
        return redirect("/login")
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    # -------------------------
    # Ler CSV do Spotify com Pandas
    # -------------------------
    if not os.path.exists(SPOTIFY_CSV):
        return "O dataset spotify.csv não foi encontrado na pasta datasets."

    df = pd.read_csv(SPOTIFY_CSV)

    # Criar tabela HTML
    table_html = df.head(20).to_html(classes="table table-striped", index=False)

    # Criar gráfico Plotly: Top 10 artistas por play_count
    if "artist" in df.columns and "play_count" in df.columns:
        top_artists = df.groupby("artist")["play_count"].sum().reset_index()
        top_artists = top_artists.sort_values("play_count", ascending=False).head(10)
        fig = px.bar(top_artists, x="artist", y="play_count", title="Top 10 Artistas")
        graph_html = fig.to_html(full_html=False)
    else:
        graph_html = "<p>CSV não tem colunas 'artist' e 'play_count'</p>"

    return render_template("dashboard.html", user=session["user"], table=table_html, graph=graph_html)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
