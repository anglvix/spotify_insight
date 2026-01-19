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
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
USERS_FILE = os.path.join(DATASETS_DIR, "users.csv")
SPOTIFY_CSV = os.path.join(DATASETS_DIR, "spotify.csv")  # o teu dataset
CHAT_FILE = os.path.join(DATASETS_DIR, "chat.csv")
FAVOURITES_FILE = os.path.join(DATASETS_DIR, "favourites.csv")

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
    # Passa informação se o utilizador está logado (user ou admin)
    is_logged_in = 'user' in session and 'role' in session
    return render_template("landingpage.html", is_logged_in=is_logged_in)

@app.route("/home", methods=["GET"])  # página 'home' acessível mesmo estando autenticado
def home():
    """
    Página home pública. Permite aceder ao conteúdo de home mesmo quando o utilizador
    está autenticado (não redireciona para o dashboard).
    """
    # Passa informação se o utilizador está logado (user ou admin)
    is_logged_in = 'user' in session and 'role' in session
    return render_template("landingpage.html", is_logged_in=is_logged_in)

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
    # Ler favoritos do utilizador
    # -------------------------
    user_favourite_songs = set()
    if os.path.exists(FAVOURITES_FILE):
        with open(FAVOURITES_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['user'] == session['user']:
                    user_favourite_songs.add(row['song'])

    # -------------------------
    # Ler CSV do Spotify com Pandas
    # -------------------------
    if not os.path.exists(SPOTIFY_CSV):
        return "O dataset spotify.csv não foi encontrado na pasta datasets."

    df = pd.read_csv(SPOTIFY_CSV)

    # Obter filtros da tabela
    table_min_plays = request.args.get("table_min_plays")
    table_min_year = request.args.get("table_min_year")
    table_max_year = request.args.get("table_max_year")

    # Obter filtros do gráfico
    graph_min_plays = request.args.get("graph_min_plays")
    graph_min_year = request.args.get("graph_min_year")
    graph_max_year = request.args.get("graph_max_year")
    graph_top_artists = request.args.get("graph_top_artists", "10")

    # Filtrar dados para a TABELA
    df_table = df.copy()
    if table_min_plays:
        try:
            table_min_plays_int = int(table_min_plays)
            df_table = df_table[df_table["play_count"] >= table_min_plays_int]
        except ValueError:
            pass
    if table_min_year:
        try:
            table_min_year_int = int(table_min_year)
            df_table = df_table[df_table["year"] >= table_min_year_int]
        except ValueError:
            pass
    if table_max_year:
        try:
            table_max_year_int = int(table_max_year)
            df_table = df_table[df_table["year"] <= table_max_year_int]
        except ValueError:
            pass

    # Filtrar dados para o GRÁFICO
    df_graph = df.copy()
    if graph_min_plays:
        try:
            graph_min_plays_int = int(graph_min_plays)
            df_graph = df_graph[df_graph["play_count"] >= graph_min_plays_int]
        except ValueError:
            pass
    if graph_min_year:
        try:
            graph_min_year_int = int(graph_min_year)
            df_graph = df_graph[df_graph["year"] >= graph_min_year_int]
        except ValueError:
            pass
    if graph_max_year:
        try:
            graph_max_year_int = int(graph_max_year)
            df_graph = df_graph[df_graph["year"] <= graph_max_year_int]
        except ValueError:
            pass

    # Criar tabela HTML customizada com filtros nos cabeçalhos
    # Converter duração de ms para minutos para mostrar
    df_table_display = df_table.copy()
    if 'duration_ms' in df_table_display.columns:
        df_table_display['duration_min'] = (df_table_display['duration_ms'] / 60000).round(2)
        df_table_display = df_table_display.drop(columns=['duration_ms'])
    
    # Remover colunas de energia e dançabilidade
    columns_to_remove = ['energy', 'danceability']
    df_table_display = df_table_display.drop(columns=[col for col in columns_to_remove if col in df_table_display.columns], errors='ignore')
    
    # Traduzir nomes das colunas para português
    column_names = {
        'track_name': 'Música',
        'artist': 'Artista',
        'album': 'Álbum',
        'year': 'Ano',
        'play_count': 'Reproduções',
        'duration_min': 'Duração (min)'
    }
    df_table_display = df_table_display.rename(columns=column_names)
    
    # Colunas que não devem ter filtro
    no_filter_columns = ['Duração (min)', 'Reproduções']
    
    # Criar tabela HTML personalizada com dropdowns nos cabeçalhos
    table_html = '<table class="min-w-full divide-y divide-gray-200"><thead class="bg-gray-800"><tr>'
    
    # Adicionar coluna de favoritos como primeira coluna
    table_html += '''
        <th class="px-3 py-3 text-center text-xs font-medium text-gray-400 uppercase tracking-wider w-20">
            Favorito
        </th>
    '''
    
    # Criar cabeçalhos com ícone de filtro e ordenação
    for col_idx, col in enumerate(df_table_display.columns):
        # Verificar se esta coluna deve ter filtro
        has_filter = col not in no_filter_columns
        
        if has_filter:
            table_html += f'''
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider relative">
            <div class="flex items-center justify-between">
                <span onclick="sortTable({col_idx})" class="cursor-pointer hover:text-primary transition flex items-center">
                    {col}
                    <svg class="w-4 h-4 ml-1 sort-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/>
                    </svg>
                </span>
                <button onclick="toggleColumnFilter({col_idx})" type="button" class="ml-2 text-gray-500 hover:text-primary transition">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/>
                    </svg>
                </button>
            </div>
            <div id="filter-{col_idx}" class="hidden absolute z-10 mt-2 bg-gray-800 rounded-lg shadow-lg border border-white/10 p-3 min-w-[200px]">
                <input type="text" onkeyup="filterColumn({col_idx})" placeholder="Filtrar {col}..." 
                    class="w-full bg-gray-900 text-white px-3 py-2 rounded border border-white/10 text-sm focus:border-primary focus:outline-none">
            </div>
        </th>
            '''
        else:
            # Cabeçalho sem filtro, apenas com ordenação
            table_html += f'''
        <th class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
            <span onclick="sortTable({col_idx})" class="cursor-pointer hover:text-primary transition flex items-center">
                {col}
                <svg class="w-4 h-4 ml-1 sort-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/>
                </svg>
            </span>
        </th>
            '''
    
    table_html += '</tr></thead><tbody class="bg-gray-900 divide-y divide-gray-700">'
    
    # Adicionar linhas
    for _, row in df_table_display.iterrows():
        table_html += '<tr class="hover:bg-gray-800 transition">'
        song_name = row['Música'] if 'Música' in row else row.iloc[0]
        # Adicionar botão de favorito como primeira coluna
        is_favourite = song_name in user_favourite_songs
        
        if is_favourite:
            # Se já é favorito, mostrar coração preenchido e desabilitado
            table_html += f'''
        <td class="px-2 py-4 text-center w-20">
            <span class="text-2xl inline-block opacity-50" title="Já nos favoritos">
                ❤️
            </span>
        </td>
            '''
        else:
            # Se não é favorito, mostrar botão para adicionar
            table_html += f'''
        <td class="px-2 py-4 text-center w-20">
            <form method="POST" action="/favourites/add" class="inline">
                <input type="hidden" name="song" value="{song_name}">
                <button type="submit" class="text-2xl hover:scale-125 transition-transform duration-200 inline-block" title="Adicionar aos favoritos">
                    ❤️
                </button>
            </form>
        </td>
            '''
        for val in row:
            table_html += f'<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{val}</td>'
        table_html += '</tr>'
    
    table_html += '</tbody></table>'
    
    # Envolver numa caixa responsiva com sombra
    table_html = f'<div class="overflow-x-auto"><div class="align-middle inline-block min-w-full shadow overflow-hidden sm:rounded-lg">{table_html}</div></div>'

    # Calcular estatísticas a partir dos dados filtrados da tabela
    def format_number(num, is_decimal=False):
        if num >= 1000000:
            return f"{int(num/1000000)}M"
        elif num >= 1000:
            return f"{int(num/1000)}K"
        else:
            if is_decimal:
                return f"{num:.2f}"
            return str(int(num))
    
    total_streams = df_table['play_count'].sum() if 'play_count' in df_table.columns else 0
    # Calcular tempo total de audição: duração * plays de cada música
    if 'duration_ms' in df_table.columns and 'play_count' in df_table.columns:
        total_duration_ms = (df_table['duration_ms'] * df_table['play_count']).sum()
    else:
        total_duration_ms = 0
    total_minutes = total_duration_ms / 60000  # Converter ms para minutos
    total_tracks = len(df_table)
    total_artists = df_table['artist'].nunique() if 'artist' in df_table.columns else 0
    total_albums = df_table['album'].nunique() if 'album' in df_table.columns else 0
    
    # Calcular top géneros
    top_genres = []
    genre_graph_html = ""
    if 'genre' in df_table.columns and 'play_count' in df_table.columns:
        genre_stats = df_table.groupby('genre')['play_count'].sum().reset_index()
        genre_stats = genre_stats.sort_values('play_count', ascending=False).head(5)
        for _, row in genre_stats.iterrows():
            top_genres.append({
                'name': row['genre'],
                'plays': format_number(row['play_count'])
            })
        
        # Criar gráfico circular (pie chart) para os top 5 géneros
        if not genre_stats.empty:
            primary = "#34D399"  # tailwind green-400
            secondary = "#3B82F6"  # tailwind blue-500
            colors = ['#34D399', '#22C55E', '#10B981', '#2563EB', '#3B82F6']
            
            fig_genre = px.pie(
                genre_stats,
                values='play_count',
                names='genre',
                color_discrete_sequence=colors,
                template="plotly_dark"
            )
            fig_genre.update_traces(
                textposition='inside',
                textinfo='percent+label',
                textfont=dict(size=18, family="Inter, sans-serif", color="#ffffff"),
                hovertemplate="<b>%{label}</b><br>Reproduções: %{value}<extra></extra>",
                marker=dict(line=dict(color='#000000', width=2))
            )
            fig_genre.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", color="#e0e0e0", size=16),
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=False
            )
            genre_graph_html = fig_genre.to_html(full_html=False, include_plotlyjs='cdn')
    
    stats = {
        'total_streams': format_number(total_streams),
        'total_minutes': format_number(total_minutes, is_decimal=True),
        'total_tracks': total_tracks,
        'total_artists': total_artists,
        'total_albums': total_albums,
        'top_genres': top_genres
    }

    # Criar gráfico Plotly: Top N artistas por play_count
    if "artist" in df_graph.columns and "play_count" in df_graph.columns:
        try:
            top_n = int(graph_top_artists)
            top_n = max(1, min(top_n, 50))  # Limitar entre 1 e 50
        except (ValueError, TypeError):
            top_n = 10
        
        top_artists = df_graph.groupby("artist")["play_count"].sum().reset_index()
        top_artists = top_artists.sort_values("play_count", ascending=False).head(top_n)

        # Plotly: estilo escuro e paleta do site (Tailwind green-400 → blue-500)
        primary = "#34D399"  # tailwind green-400
        secondary = "#3B82F6"  # tailwind blue-500
        fig = px.bar(
            top_artists,
            x="artist",
            y="play_count",
            title=f"Top {top_n} Artistas",
            color="play_count",
            color_continuous_scale=[primary, secondary],
            template="plotly_dark",
            labels={"play_count": "Reproduções", "artist": "Artista"},
        )
        fig.update_traces(marker_line_width=0, opacity=0.95, hovertemplate="<b>%{x}</b><br>Reproduções: %{y}<extra></extra>")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", color="#e0e0e0"),
            title=dict(font=dict(size=30, color="#ffffff", family="Inter, sans-serif"), font_weight=700),
            margin=dict(l=40, r=20, t=50, b=80),
            coloraxis_colorbar=dict(title="Reproduções", tickfont=dict(color="#e0e0e0")),
        )
        fig.update_xaxes(tickangle=-45, showgrid=False, tickfont=dict(color="#e0e0e0"))
        fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color="#e0e0e0"))
        graph_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
    else:
        graph_html = "<p>CSV não tem colunas 'artist' e 'play_count'</p>"

    return render_template(
        "dashboard.html", 
        user=session["user"], 
        table=table_html, 
        graph=graph_html,
        genre_graph=genre_graph_html,
        stats=stats,
        table_min_plays=table_min_plays, 
        table_min_year=table_min_year, 
        table_max_year=table_max_year,
        graph_min_plays=graph_min_plays,
        graph_min_year=graph_min_year,
        graph_max_year=graph_max_year,
        graph_top_artists=graph_top_artists
    )

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

@app.route("/chat")
def chat():
    """
    Página de chat.
    - Requer autenticação (verifica se o utilizador está na sessão).
    - Disponível apenas para utilizadores autenticados.
    - Lê e apresenta todas as mensagens do ficheiro chat.csv.
    """
    if "user" not in session:
        return redirect("/login")
    
    messages = []
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                messages.append(row)
    
    return render_template("chat.html", user=session["user"], messages=messages)

@app.route("/chat/send", methods=["POST"])
def chat_send():
    """
    Envia uma nova mensagem para o chat.
    - Requer autenticação.
    - Guarda a mensagem no ficheiro chat.csv com id, user, time e message.
    - Redireciona de volta para a página de chat.
    """
    if "user" not in session:
        return redirect("/login")
    
    message = request.form.get("message")
    if not message:
        return redirect("/chat")
    
    from datetime import datetime
    
    # Ler mensagens existentes para gerar novo id
    messages = []
    file_exists = os.path.exists(CHAT_FILE)
    if file_exists:
        with open(CHAT_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                messages.append(row)
    
    new_id = len(messages) + 1
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Escrever nova mensagem
    with open(CHAT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["id", "user", "time", "message"])
        writer.writerow([new_id, session["user"], current_time, message])
    
    return redirect("/chat")

@app.route("/favourites")
def favourites():
    """
    Página de favoritos.
    - Requer autenticação (verifica se o utilizador está na sessão).
    - Mostra apenas os favoritos do utilizador logado.
    - Busca informações detalhadas de cada música no spotify.csv.
    - Suporta filtros de reproduções mínimas e intervalo de anos.
    """
    if "user" not in session:
        return redirect("/login")
    
    # Obter filtros do formulário
    min_plays = request.args.get('min_plays', type=int)
    min_year = request.args.get('min_year', type=int)
    max_year = request.args.get('max_year', type=int)
    
    user_favourites = []
    if os.path.exists(FAVOURITES_FILE):
        with open(FAVOURITES_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['user'] == session['user']:
                    user_favourites.append(row)
    
    # Ler spotify.csv para obter informações detalhadas das músicas
    enriched_favourites = []
    if os.path.exists(SPOTIFY_CSV) and user_favourites:
        df = pd.read_csv(SPOTIFY_CSV)
        
        for fav in user_favourites:
            song_name = fav['song']
            # Procurar a música no dataset
            song_data = df[df['track_name'] == song_name]
            
            if not song_data.empty:
                # Pegar a primeira ocorrência
                song_info = song_data.iloc[0]
                
                # Aplicar filtros
                play_count = song_info.get('play_count', 0)
                year = song_info.get('year', 0)
                
                # Verificar filtro de reproduções mínimas
                if min_plays and play_count < min_plays:
                    continue
                
                # Verificar filtro de ano mínimo
                if min_year and year < min_year:
                    continue
                
                # Verificar filtro de ano máximo
                if max_year and year > max_year:
                    continue
                
                enriched_fav = {
                    'id': fav['id'],
                    'song': song_name,
                    'artist': song_info.get('artist', 'N/A'),
                    'album': song_info.get('album', 'N/A'),
                    'year': song_info.get('year', 'N/A'),
                    'play_count': song_info.get('play_count', 'N/A'),
                    'duration_min': round(song_info.get('duration_ms', 0) / 60000, 2) if 'duration_ms' in song_info else 'N/A',
                    'genre': song_info.get('genre', 'N/A')
                }
                enriched_favourites.append(enriched_fav)
            else:
                # Caso a música não seja encontrada, adicionar só com o nome (sem filtros)
                enriched_favourites.append({
                    'id': fav['id'],
                    'song': song_name,
                    'artist': 'N/A',
                    'album': 'N/A',
                    'year': 'N/A',
                    'play_count': 'N/A',
                    'duration_min': 'N/A',
                    'genre': 'N/A'
                })
    
    return render_template("favourites.html", 
                         user=session["user"], 
                         favourites=enriched_favourites,
                         min_plays=min_plays,
                         min_year=min_year,
                         max_year=max_year)

@app.route("/favourites/add", methods=["POST"])
def favourites_add():
    """
    Adiciona uma música aos favoritos do utilizador.
    - Requer autenticação.
    - Guarda no ficheiro favourites.csv com id, user e song.
    """
    if "user" not in session:
        return redirect("/login")
    
    song = request.form.get("song")
    if not song:
        return redirect("/dashboard")
    
    # Ler favoritos existentes para gerar novo id
    favourites = []
    file_exists = os.path.exists(FAVOURITES_FILE)
    if file_exists:
        with open(FAVOURITES_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                favourites.append(row)
    
    new_id = len(favourites) + 1
    
    # Escrever novo favorito
    with open(FAVOURITES_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["id", "user", "song"])
        writer.writerow([new_id, session["user"], song])
    
    return redirect("/favourites")

@app.route("/favourites/remove/<fav_id>", methods=["POST"])
def favourites_remove(fav_id):
    """
    Remove uma música dos favoritos.
    - Apenas o dono do favorito pode removê-lo.
    """
    if "user" not in session:
        return redirect("/login")
    
    favourites = []
    if os.path.exists(FAVOURITES_FILE):
        with open(FAVOURITES_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Manter apenas os favoritos que não correspondem ao id a remover
                # ou que não pertencem ao utilizador atual (segurança)
                if row['id'] != fav_id or row['user'] != session['user']:
                    favourites.append(row)
    
    # Reescrever o ficheiro sem o favorito removido
    with open(FAVOURITES_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'user', 'song'])
        for fav in favourites:
            writer.writerow([fav['id'], fav['user'], fav['song']])
    
    return redirect("/favourites")

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
