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
    """
    Lê o ficheiro CSV de utilizadores e retorna uma lista de dicionários.
    Cada dicionário representa um utilizador com as chaves: id, nome, email, password, role.
    Se o ficheiro não existir, retorna uma lista vazia.
    """
    users = []
    if not os.path.exists(USERS_FILE):
        return users
    with open(USERS_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.append(row)
    return users

def add_user(nome, email, password, role="user"):
    """
    Adiciona um novo utilizador ao ficheiro CSV.
    - Escreve o cabeçalho se o ficheiro ainda não existir.
    - Gera um novo id incremental com base no número atual de utilizadores.
    - `role` por defeito é 'user'; pode ser definido para 'admin'.

    Nota: neste projecto as passwords são guardadas em texto simples (não recomendado para produção).
    """
    file_exists = os.path.exists(USERS_FILE)
    with open(USERS_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["id","nome","email","password","role"])
        users = read_users()
        new_id = len(users) + 1
        writer.writerow([new_id, nome, email, password, role])

# função para escrever utilizadores
def write_users(users_list):
    """
    Sobrescreve o ficheiro de utilizadores com a lista fornecida.
    Espera uma lista de dicionários com as chaves: id, nome, email, password, role.
    Esta função é usada para persistir alterações realizadas no painel de administração
    (promover/demover/apagar utilizadores).
    """
    # users_list: list of dicts with keys id,nome,email,password,role
    with open(USERS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id','nome','email','password','role'])
        for u in users_list:
            writer.writerow([u['id'], u['nome'], u['email'], u.get('password',''), u.get('role','user')])

# -------------------------
# Rotas
# -------------------------
@app.route("/", methods=["GET"])
def root_landing():
    """
    Rota raiz '/'. Mostra a página de landing mesmo que o utilizador esteja autenticado.
    Isto permite ao utilizador aceder à página pública de apresentação sem ser
    automaticamente redirecionado para o dashboard.
    """
    return render_template("landingpage.html")

@app.route("/home", methods=["GET"])  # página 'home' acessível mesmo estando autenticado
def home():
    """
    Página home pública. Permite aceder ao conteúdo de home mesmo quando o utilizador
    está autenticado (não redireciona para o dashboard).
    """
    return render_template("landingpage.html")

@app.route("/login", methods=["GET","POST"])
def login():
    """
    Rota de autenticação.
    - GET: apresenta o formulário de login.
    - POST: valida credenciais contra os utilizadores guardados no CSV.
    Em caso de sucesso guarda `user` e `role` na sessão e redireciona para /dashboard.
    """
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
    """
    Rota para registar novos utilizadores (página pública).
    - Valida se o email já existe e, em caso afirmativo, devolve erro.
    - Caso contrário chama `add_user` para persistir o novo utilizador e redireciona para /login.
    """
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
    """
    Página principal do utilizador autenticado.
    - Verifica sessão e exige autenticação.
    - Lê o dataset de Spotify usando pandas e gera uma tabela HTML com classes Tailwind.
    - Gera um gráfico Plotly (Top 10 artistas) com tema escuro e cores do site.
    - Passa `table_html` e `graph_html` para o template `dashboard.html`.
    """
    if "user" not in session:
        return redirect("/login")

    # -------------------------
    # Ler CSV do Spotify com Pandas
    # -------------------------
    if not os.path.exists(SPOTIFY_CSV):
        return "O dataset spotify.csv não foi encontrado na pasta datasets."

    df = pd.read_csv(SPOTIFY_CSV)

    # Criar tabela HTML (com estilo Tailwind)
    table_html = df.head(20).to_html(classes="min-w-full divide-y divide-gray-200", index=False)
    # Estilizar cabeçalho e células com classes Tailwind
    table_html = table_html.replace('<thead>', '<thead class="bg-gray-800">')
    table_html = table_html.replace('<th>', '<th class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">')
    table_html = table_html.replace('<td>', '<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">')
    # Remover atributo border (pandas adiciona border="1")
    table_html = table_html.replace('border="1"', '')
    # Envolver numa caixa responsiva com sombra
    table_html = f'<div class="overflow-x-auto"><div class="align-middle inline-block min-w-full shadow overflow-hidden sm:rounded-lg">{table_html}</div></div>'

    # Criar gráfico Plotly: Top 10 artistas por play_count
    if "artist" in df.columns and "play_count" in df.columns:
        top_artists = df.groupby("artist")["play_count"].sum().reset_index()
        top_artists = top_artists.sort_values("play_count", ascending=False).head(10)

        # Plotly: estilo escuro e paleta do site (Tailwind green-400 → blue-500)
        primary = "#34D399"  # tailwind green-400
        secondary = "#3B82F6"  # tailwind blue-500
        fig = px.bar(
            top_artists,
            x="artist",
            y="play_count",
            title="Top 10 Artistas",
            color="play_count",
            color_continuous_scale=[primary, secondary],
            template="plotly_dark",
            labels={"play_count": "Plays", "artist": "Artista"},
        )
        fig.update_traces(marker_line_width=0, opacity=0.95, hovertemplate="<b>%{x}</b><br>Plays: %{y}<extra></extra>")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#e0e0e0"),
            title=dict(font=dict(size=18, color=primary)),
            margin=dict(l=40, r=20, t=50, b=80),
            coloraxis_colorbar=dict(title="Plays", tickfont=dict(color="#e0e0e0")),
        )
        fig.update_xaxes(tickangle=-45, showgrid=False, tickfont=dict(color="#e0e0e0"))
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color="#e0e0e0"))
        graph_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graph_html = "<p>CSV não tem colunas 'artist' e 'play_count'</p>"

    return render_template("dashboard.html", user=session["user"], table=table_html, graph=graph_html)

@app.route("/admin")
def admin():
    """
    Página de administração.
    - Requer que o utilizador tenha o `role` igual a 'admin' na sessão.
    - Recupera a lista de utilizadores e passa para o template admin.html.
    """
    if session.get("role") != "admin":
        return "Acesso negado", 403
    users = read_users()
    return render_template("admin.html", user=session.get("user"), users=users)

@app.route("/admin/promote/<user_id>", methods=["POST"])
def admin_promote(user_id):
    """
    Promove um utilizador para administrador (role = 'admin').
    - Apenas acessível a administradores.
    - Actualiza o ficheiro CSV através de `write_users`.
    """
    if session.get("role") != "admin":
        return "Acesso negado", 403
    users = read_users()
    for u in users:
        if u['id'] == user_id:
            u['role'] = 'admin'
            break
    write_users(users)
    return redirect("/admin")

@app.route("/admin/demote/<user_id>", methods=["POST"])
def admin_demote(user_id):
    """
    Rebaixa um administrador para utilizador comum (role = 'user').
    - Protecção para não remover o último administrador existente.
    - Apenas acessível a administradores.
    """
    if session.get("role") != "admin":
        return "Acesso negado", 403
    users = read_users()
    admins = [u for u in users if u.get('role') == 'admin']
    for u in users:
        if u['id'] == user_id:
            if u['role'] != 'admin':
                break
            if len(admins) <= 1:
                return "Não pode remover o último administrador", 400
            u['role'] = 'user'
            break
    write_users(users)
    return redirect("/admin")

@app.route("/admin/delete/<user_id>", methods=["POST"])
def admin_delete(user_id):
    """
    Apaga um utilizador.
    - Previne apagar a própria conta.
    - Previne apagar o último administrador do sistema.
    - Apenas acessível a administradores.
    """
    if session.get("role") != "admin":
        return "Acesso negado", 403
    users = read_users()
    # evitar apagar a si próprio
    for u in users:
        if u['id'] == user_id and u['nome'] == session.get('user'):
            return "Não pode apagar a sua própria conta", 400
    admins = [u for u in users if u.get('role') == 'admin']
    to_delete = None
    for u in users:
        if u['id'] == user_id:
            to_delete = u
            break
    if to_delete and to_delete.get('role') == 'admin' and len(admins) <=1:
        return "Não pode apagar o último administrador", 400
    users = [u for u in users if u['id'] != user_id]
    write_users(users)
    return redirect("/admin")

@app.route("/admin/create", methods=["POST"])
def admin_create():
    """
    Permite que um administrador crie um novo utilizador via painel de administração.
    - Valida que o email é único.
    - Guarda o novo utilizador com a role seleccionada.
    - Apenas acessível a administradores.
    """
    if session.get("role") != "admin":
        return "Acesso negado", 403
    nome = request.form.get("nome")
    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role", "user")
    # validar email unico
    for u in read_users():
        if u.get('email') == email:
            return "Email já existe!", 400
    add_user(nome, email, password, role)
    return redirect("/admin")

@app.route("/logout")
def logout():
    """
    Limpa a sessão do utilizador (logout) e redireciona para a página de login.
    """
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    # Executa a app em modo de desenvolvimento (debug=True) localmente.
    app.run(debug=True)
