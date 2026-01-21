from flask import Flask, render_template, request, redirect, session
import csv
import os
import pandas as pd
import plotly.express as px
from datetime import datetime

app = Flask(__name__)
app.secret_key = "segredo_simples"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
USERS_FILE = os.path.join(DATASETS_DIR, "users.csv")
SPOTIFY_CSV = os.path.join(DATASETS_DIR, "spotify.csv")
CHAT_FILE = os.path.join(DATASETS_DIR, "chat.csv")
FAVOURITES_FILE = os.path.join(DATASETS_DIR, "favourites.csv")

def require_auth():
    """
    Verifica se o utilizador está autenticado.
    - Verifica se existe a chave 'user' na sessão.
    - Se não estiver autenticado, retorna um redirect para a página de login.
    - Se estiver autenticado, retorna None permitindo que a função continue.
    Utilizado como função auxiliar em todas as rotas que requerem autenticação.
    """
    if "user" not in session:
        return redirect("/login")
    return None

def require_admin():
    """
    Verifica se o utilizador tem permissões de administrador.
    - Verifica se o campo 'role' na sessão é igual a 'admin'.
    - Se não for administrador, retorna mensagem de erro com código HTTP 403.
    - Se for administrador, retorna None permitindo acesso à funcionalidade.
    Utilizado em todas as rotas do painel de administração.
    """
    if session.get("role") != "admin":
        return "Acesso negado", 403
    return None

def read_csv(filepath):
    """
    Lê um ficheiro CSV e retorna o conteúdo como lista de dicionários.
    - Cada linha do CSV é convertida num dicionário com as chaves sendo os cabeçalhos.
    - Se o ficheiro não existir, retorna uma lista vazia.
    - Utiliza codificação UTF-8 para suportar caracteres especiais.
    Função genérica reutilizável para ler qualquer ficheiro CSV do projecto.
    """
    if not os.path.exists(filepath):
        return []
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_csv(filepath, headers, rows):
    """
    Escreve dados num ficheiro CSV, sobrescrevendo o conteúdo existente.
    - Recebe o caminho do ficheiro, lista de cabeçalhos e lista de linhas.
    - Escreve primeiro a linha de cabeçalhos, depois todas as linhas de dados.
    - Utiliza modo 'w' que apaga conteúdo anterior e cria ficheiro novo.
    Utilizado para actualizar ficheiros CSV após modificações (ex: gestão de utilizadores).
    """
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

def append_csv(filepath, headers, row):
    """
    Adiciona uma nova linha ao final de um ficheiro CSV.
    - Se o ficheiro não existir, cria-o e escreve primeiro os cabeçalhos.
    - Se o ficheiro já existir, adiciona apenas a nova linha sem alterar dados existentes.
    - Utiliza modo 'a' (append) para preservar conteúdo anterior.
    Utilizado para adicionar novos registos (utilizadores, mensagens, favoritos).
    """
    file_exists = os.path.exists(filepath)
    with open(filepath, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)
        writer.writerow(row)

def format_number(num, is_decimal=False):
    """
    Formata números grandes para formato legível com abreviações.
    - Números >= 1.000.000 são convertidos para formato 'XM' (milhões).
    - Números >= 1.000 são convertidos para formato 'XK' (milhares).
    - Números menores são apresentados como inteiros ou com 2 casas decimais.
    - Parâmetro is_decimal define se mostra casas decimais para números pequenos.
    Utilizado nas estatísticas do dashboard para melhor visualização.
    """
    if num >= 1000000:
        return f"{int(num/1000000)}M"
    elif num >= 1000:
        return f"{int(num/1000)}K"
    return f"{num:.2f}" if is_decimal else str(int(num))

def apply_filters(df, min_plays=None, min_year=None, max_year=None):
    """
    Aplica filtros de reproduções e anos a um DataFrame do pandas.
    - min_plays: filtra músicas com número de reproduções >= valor especificado.
    - min_year: filtra músicas com ano >= valor especificado.
    - max_year: filtra músicas com ano <= valor especificado.
    - Trata erros de conversão de tipo silenciosamente (ignora filtros inválidos).
    - Retorna o DataFrame filtrado ou original se filtros forem inválidos.
    Reutilizado tanto para filtrar tabela como gráficos no dashboard.
    """
    if min_plays:
        try:
            df = df[df["play_count"] >= int(min_plays)]
        except (ValueError, TypeError):
            pass
    if min_year:
        try:
            df = df[df["year"] >= int(min_year)]
        except (ValueError, TypeError):
            pass
    if max_year:
        try:
            df = df[df["year"] <= int(max_year)]
        except (ValueError, TypeError):
            pass
    return df

def read_users():
    """
    Lê o ficheiro CSV de utilizadores e retorna uma lista de dicionários.
    Cada dicionário representa um utilizador com as chaves: id, nome, email, password, role.
    Se o ficheiro não existir, retorna uma lista vazia.
    Função específica que utiliza read_csv() para ler o ficheiro users.csv.
    """
    return read_csv(USERS_FILE)

def add_user(nome, email, password, role="user"):
    """
    Adiciona um novo utilizador ao ficheiro CSV.
    - Gera automaticamente um ID incremental baseado no número de utilizadores existentes.
    - O parâmetro role é opcional e tem valor padrão 'user'.
    - Pode ser definido como 'admin' para criar administradores.
    - Escreve os cabeçalhos automaticamente se o ficheiro não existir.
    Nota: As passwords são guardadas em texto simples (não recomendado para produção).
    """
    new_id = len(read_users()) + 1
    append_csv(USERS_FILE, ["id","nome","email","password","role"], [new_id, nome, email, password, role])

def write_users(users_list):
    """
    Sobrescreve completamente o ficheiro de utilizadores com a lista fornecida.
    - Recebe uma lista de dicionários com as chaves: id, nome, email, password, role.
    - Converte cada dicionário numa linha do CSV.
    - Utiliza valores padrão para campos opcionais (password vazio, role 'user').
    Utilizado no painel de administração para persistir alterações após promover/rebaixar/apagar utilizadores.
    """
    rows = [[u['id'], u['nome'], u['email'], u.get('password',''), u.get('role','user')] for u in users_list]
    write_csv(USERS_FILE, ['id','nome','email','password','role'], rows)

# -------------------------
# Rotas
# -------------------------
@app.route("/", methods=["GET"])
@app.route("/home", methods=["GET"])
def home():
    """
    Página de landing pública.
    - Acessível mesmo quando o utilizador está autenticado.
    - Apresenta a página inicial do website com informações sobre o projecto.
    - Passa informação se o utilizador está autenticado para adaptar a navegação.
    Responde tanto à rota raiz '/' como à rota '/home'.
    """
    is_logged_in = 'user' in session and 'role' in session
    return render_template("landingpage.html", is_logged_in=is_logged_in)

@app.route("/login", methods=["GET","POST"])
def login():
    """
    Rota de autenticação de utilizadores.
    - GET: apresenta o formulário de login.
    - POST: valida credenciais (email e password) contra os utilizadores no CSV.
    - Em caso de sucesso, guarda 'user' (nome) e 'role' na sessão.
    - Redireciona para o dashboard após login bem-sucedido.
    - Retorna mensagem de erro se credenciais forem inválidas.
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
    Rota de registo de novos utilizadores.
    - GET: apresenta o formulário de registo.
    - POST: valida se o email já está registado.
    - Se o email for único, cria novo utilizador com role 'user' por defeito.
    - Redireciona para a página de login após registo bem-sucedido.
    - Retorna mensagem de erro se o email já existir.
    Página pública acessível sem autenticação.
    """
    if request.method == "POST":
        nome = request.form.get("nome")
        email = request.form.get("email")
        password = request.form.get("password")
        if any(u["email"] == email for u in read_users()):
            return "Email já existe!"
        add_user(nome, email, password)
        return redirect("/login")
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    """
    Página principal do utilizador autenticado (Dashboard).
    - Requer autenticação obrigatória.
    - Lê o dataset do Spotify (spotify.csv) e apresenta estatísticas e gráficos.
    - Suporta filtros independentes para tabela e gráficos (reproduções, anos).
    - Gera tabela HTML interactiva com botões de favoritos, ordenação e filtros.
    - Cria gráfico de pizza dos top 5 géneros musicais.
    - Cria gráfico de barras dos top N artistas (configurável).
    - Calcula estatísticas: total de reproduções, minutos, músicas, artistas e álbuns.
    - Identifica músicas favoritas do utilizador para indicar na tabela.
    """
    auth_check = require_auth()
    if auth_check:
        return auth_check

    if not os.path.exists(SPOTIFY_CSV):
        return "O dataset spotify.csv não foi encontrado na pasta datasets."

    user_favourite_songs = {row['song'] for row in read_csv(FAVOURITES_FILE) if row['user'] == session['user']}
    df = pd.read_csv(SPOTIFY_CSV)

    table_min_plays = request.args.get('table_min_plays')
    table_min_year = request.args.get('table_min_year')
    table_max_year = request.args.get('table_max_year')
    graph_min_plays = request.args.get('graph_min_plays')
    graph_min_year = request.args.get('graph_min_year')
    graph_max_year = request.args.get('graph_max_year')
    graph_top_artists = request.args.get("graph_top_artists", "10")

    df_table = apply_filters(df.copy(), table_min_plays, table_min_year, table_max_year)
    df_graph = apply_filters(df.copy(), graph_min_plays, graph_min_year, graph_max_year)

    df_table_display = df_table.copy()
    if 'duration_ms' in df_table_display.columns:
        df_table_display['duration_min'] = (df_table_display['duration_ms'] / 60000).round(2)
        df_table_display = df_table_display.drop(columns=['duration_ms'])
    
    df_table_display = df_table_display.drop(columns=['energy', 'danceability'], errors='ignore')
    df_table_display = df_table_display.rename(columns={
        'track_name': 'Música', 'artist': 'Artista', 'album': 'Álbum',
        'year': 'Ano', 'play_count': 'Reproduções', 'duration_min': 'Duração (min)'
    })

    table_html = build_table_html(df_table_display, user_favourite_songs)
    stats = calculate_stats(df_table)
    genre_graph_html = create_genre_chart(df_table)
    graph_html = create_artist_chart(df_graph, graph_top_artists)

    return render_template("dashboard.html", user=session["user"], table=table_html, graph=graph_html,
                         genre_graph=genre_graph_html, stats=stats, 
                         table_min_plays=table_min_plays, table_min_year=table_min_year, table_max_year=table_max_year,
                         graph_min_plays=graph_min_plays, graph_min_year=graph_min_year, graph_max_year=graph_max_year,
                         graph_top_artists=graph_top_artists)

def build_table_html(df, user_favourite_songs):
    """
    Constrói a tabela HTML completa com funcionalidades interactivas.
    - Recebe um DataFrame com dados das músicas e conjunto de favoritos do utilizador.
    - Cria cabeçalhos com ícones de ordenação para todas as colunas.
    - Adiciona filtros por coluna (excepto Duração e Reproduções).
    - Primeira coluna mostra botão de favorito (coração).
    - Botões ficam desactivados (opacidade reduzida) se música já for favorita.
    - Utiliza classes Tailwind CSS para estilização consistente.
    - Retorna HTML completo pronto para inserir no template.
    """
    no_filter_columns = ['Duração (min)', 'Reproduções']
    table_html = '<table class="min-w-full divide-y divide-gray-200"><thead class="bg-gray-800"><tr>'
    table_html += '<th class="px-3 py-3 text-center text-xs font-medium text-gray-400 uppercase tracking-wider w-20">Favorito</th>'
    
    for col_idx, col in enumerate(df.columns):
        has_filter = col not in no_filter_columns
        sort_icon = '<svg class="w-4 h-4 ml-1 sort-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4"/></svg>'
        
        if has_filter:
            filter_icon = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/></svg>'
            table_html += f'''<th class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider relative">
                <div class="flex items-center justify-between">
                    <span onclick="sortTable({col_idx})" class="cursor-pointer hover:text-primary transition flex items-center">{col}{sort_icon}</span>
                    <button onclick="toggleColumnFilter({col_idx})" type="button" class="ml-2 text-gray-500 hover:text-primary transition">{filter_icon}</button>
                </div>
                <div id="filter-{col_idx}" class="hidden absolute z-10 mt-2 bg-gray-800 rounded-lg shadow-lg border border-white/10 p-3 min-w-[200px]">
                    <input type="text" onkeyup="filterColumn({col_idx})" placeholder="Filtrar {col}..." class="w-full bg-gray-900 text-white px-3 py-2 rounded border border-white/10 text-sm focus:border-primary focus:outline-none">
                </div></th>'''
        else:
            table_html += f'<th class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider"><span onclick="sortTable({col_idx})" class="cursor-pointer hover:text-primary transition flex items-center">{col}{sort_icon}</span></th>'
    
    table_html += '</tr></thead><tbody class="bg-gray-900 divide-y divide-gray-700">'
    
    for _, row in df.iterrows():
        song_name = row['Música'] if 'Música' in row else row.iloc[0]
        is_favourite = song_name in user_favourite_songs
        table_html += '<tr class="hover:bg-gray-800 transition">'
        
        if is_favourite:
            table_html += '<td class="px-2 py-4 text-center w-20"><span class="text-2xl inline-block opacity-50" title="Já nos favoritos">❤️</span></td>'
        else:
            table_html += f'''<td class="px-2 py-4 text-center w-20"><form method="POST" action="/favourites/add" class="inline">
                <input type="hidden" name="song" value="{song_name}">
                <button type="submit" class="text-2xl hover:scale-125 transition-transform duration-200 inline-block" title="Adicionar aos favoritos">❤️</button>
                </form></td>'''
        
        for val in row:
            table_html += f'<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{val}</td>'
        table_html += '</tr>'
    
    table_html += '</tbody></table>'
    return f'<div class="overflow-x-auto"><div class="align-middle inline-block min-w-full shadow overflow-hidden sm:rounded-lg">{table_html}</div></div>'

def calculate_stats(df):
    """
    Calcula estatísticas a partir do DataFrame de músicas.
    - Total de reproduções: soma de todos os play_count.
    - Total de minutos: (duração de cada música * reproduções) convertido para minutos.
    - Total de músicas: número de linhas no DataFrame.
    - Total de artistas: contagem de artistas únicos.
    - Total de álbuns: contagem de álbuns únicos.
    - Top 5 géneros: ordena géneros por reproduções e selecciona os 5 primeiros.
    - Formata números grandes com abreviações (K, M) para melhor visualização.
    Retorna dicionário com todas as estatísticas formatadas.
    """
    total_streams = df['play_count'].sum() if 'play_count' in df.columns else 0
    total_duration_ms = (df['duration_ms'] * df['play_count']).sum() if 'duration_ms' in df.columns and 'play_count' in df.columns else 0
    
    top_genres = []
    if 'genre' in df.columns and 'play_count' in df.columns:
        genre_stats = df.groupby('genre')['play_count'].sum().sort_values(ascending=False).head(5)
        top_genres = [{'name': name, 'plays': format_number(plays)} for name, plays in genre_stats.items()]
    
    return {
        'total_streams': format_number(total_streams),
        'total_minutes': format_number(total_duration_ms / 60000, is_decimal=True),
        'total_tracks': len(df),
        'total_artists': df['artist'].nunique() if 'artist' in df.columns else 0,
        'total_albums': df['album'].nunique() if 'album' in df.columns else 0,
        'top_genres': top_genres
    }

def create_genre_chart(df):
    """
    Cria gráfico de pizza (pie chart) dos top 5 géneros musicais.
    - Agrupa dados por género e soma as reproduções.
    - Ordena por reproduções decrescentes e selecciona os 5 primeiros.
    - Utiliza paleta de cores verde-azul (#34D399 → #3B82F6) do tema do site.
    - Configura tema escuro do Plotly para combinar com o design.
    - Remove legenda e mostra percentagens dentro das fatias.
    - Retorna HTML do gráfico pronto para inserir no template.
    - Retorna string vazia se não houver dados ou colunas necessárias.
    """
    if 'genre' not in df.columns or 'play_count' not in df.columns:
        return ""
    
    genre_stats = df.groupby('genre')['play_count'].sum().reset_index().sort_values('play_count', ascending=False).head(5)
    if genre_stats.empty:
        return ""
    
    fig = px.pie(genre_stats, values='play_count', names='genre',
                 color_discrete_sequence=['#34D399', '#22C55E', '#10B981', '#2563EB', '#3B82F6'],
                 template="plotly_dark")
    fig.update_traces(textposition='inside', textinfo='percent+label',
                     textfont=dict(size=18, family="Inter, sans-serif", color="#ffffff"),
                     hovertemplate="<b>%{label}</b><br>Reproduções: %{value}<extra></extra>",
                     marker=dict(line=dict(color='#000000', width=2)))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(family="Inter, sans-serif", color="#e0e0e0", size=16),
                     margin=dict(l=20, r=20, t=20, b=20), showlegend=False)
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

def create_artist_chart(df, graph_top_artists):
    """
    Cria gráfico de barras dos top N artistas mais ouvidos.
    - Agrupa dados por artista e soma as reproduções.
    - Ordena por reproduções decrescentes e selecciona os N primeiros.
    - O número de artistas (N) é configurável entre 1 e 50.
    - Utiliza escala de cores do verde ao azul para colorir barras.
    - Configura tema escuro com fundo transparente.
    - Inclui hover interactivo mostrando nome e reproduções.
    - Rótulos do eixo X inclinados a 45° para melhor legibilidade.
    - Retorna HTML do gráfico ou mensagem de erro se colunas não existirem.
    """
    if "artist" not in df.columns or "play_count" not in df.columns:
        return "<p>CSV não tem colunas 'artist' e 'play_count'</p>"
    
    try:
        top_n = max(1, min(int(graph_top_artists), 50))
    except (ValueError, TypeError):
        top_n = 10
    
    top_artists = df.groupby("artist")["play_count"].sum().reset_index().sort_values("play_count", ascending=False).head(top_n)
    
    fig = px.bar(top_artists, x="artist", y="play_count", title=f"Top {top_n} Artistas",
                color="play_count", color_continuous_scale=["#34D399", "#3B82F6"], template="plotly_dark",
                labels={"play_count": "Reproduções", "artist": "Artista"})
    fig.update_traces(marker_line_width=0, opacity=0.95, hovertemplate="<b>%{x}</b><br>Reproduções: %{y}<extra></extra>")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                     font=dict(family="Inter, sans-serif", color="#e0e0e0"),
                     title=dict(font=dict(size=30, color="#ffffff", family="Inter, sans-serif"), font_weight=700),
                     margin=dict(l=40, r=20, t=50, b=80),
                     coloraxis_colorbar=dict(title="Reproduções", tickfont=dict(color="#e0e0e0")))
    fig.update_xaxes(tickangle=-45, showgrid=False, tickfont=dict(color="#e0e0e0"))
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", tickfont=dict(color="#e0e0e0"))
    return fig.to_html(full_html=False, include_plotlyjs='cdn')

@app.route("/admin")
def admin():
    """
    Página de administração do sistema.
    - Requer permissões de administrador (role = 'admin').
    - Lista todos os utilizadores registados no sistema.
    - Permite promover utilizadores a administrador.
    - Permite rebaixar administradores a utilizadores comuns.
    - Permite apagar utilizadores (com restrições de segurança).
    - Permite criar novos utilizadores directamente.
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
    return render_template("admin.html", user=session.get("user"), users=read_users())

@app.route("/admin/promote/<user_id>", methods=["POST"])
def admin_promote(user_id):
    """
    Promove um utilizador comum para administrador.
    - Requer permissões de administrador.
    - Altera o campo 'role' do utilizador para 'admin'.
    - Actualiza o ficheiro CSV com a alteração.
    - Redireciona de volta para o painel de administração.
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
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
    Rebaixa um administrador para utilizador comum.
    - Requer permissões de administrador.
    - Altera o campo 'role' de 'admin' para 'user'.
    - Verifica se não é o último administrador do sistema.
    - Impede remoção do último admin para manter acesso ao painel.
    - Actualiza o ficheiro CSV e redireciona para o painel.
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
    users = read_users()
    admins = [u for u in users if u.get('role') == 'admin']
    
    for u in users:
        if u['id'] == user_id and u['role'] == 'admin':
            if len(admins) <= 1:
                return "Não pode remover o último administrador", 400
            u['role'] = 'user'
            break
    write_users(users)
    return redirect("/admin")

@app.route("/admin/delete/<user_id>", methods=["POST"])
def admin_delete(user_id):
    """
    Apaga um utilizador do sistema.
    - Requer permissões de administrador.
    - Impede que o administrador apague a própria conta.
    - Impede apagar o último administrador do sistema.
    - Remove o utilizador da lista e actualiza o ficheiro CSV.
    - Redireciona para o painel após eliminação bem-sucedida.
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
    users = read_users()
    
    user_to_delete = next((u for u in users if u['id'] == user_id), None)
    if user_to_delete:
        if user_to_delete['nome'] == session.get('user'):
            return "Não pode apagar a sua própria conta", 400
        if user_to_delete.get('role') == 'admin' and sum(1 for u in users if u.get('role') == 'admin') <= 1:
            return "Não pode apagar o último administrador", 400
    
    users = [u for u in users if u['id'] != user_id]
    write_users(users)
    return redirect("/admin")

@app.route("/admin/create", methods=["POST"])
def admin_create():
    """
    Cria um novo utilizador via painel de administração.
    - Requer permissões de administrador.
    - Valida que o email é único no sistema.
    - Permite escolher a role (user ou admin) para o novo utilizador.
    - Adiciona o utilizador ao ficheiro CSV.
    - Retorna erro se o email já estiver registado.
    - Redireciona para o painel após criação bem-sucedida.
    """
    admin_check = require_admin()
    if admin_check:
        return admin_check
    
    nome = request.form.get("nome")
    email = request.form.get("email")
    password = request.form.get("password")
    role = request.form.get("role", "user")
    
    if any(u.get('email') == email for u in read_users()):
        return "Email já existe!", 400
    add_user(nome, email, password, role)
    return redirect("/admin")

@app.route("/chat")
def chat():
    """
    Página de chat para utilizadores autenticados.
    - Requer autenticação obrigatória.
    - Lê todas as mensagens guardadas no ficheiro chat.csv.
    - Apresenta mensagens com nome do utilizador, hora e conteúdo.
    - Destaca mensagens do administrador com cor diferente.
    - Permite aos utilizadores enviar novas mensagens.
    """
    auth_check = require_auth()
    if auth_check:
        return auth_check
    return render_template("chat.html", user=session["user"], messages=read_csv(CHAT_FILE))

@app.route("/chat/send", methods=["POST"])
def chat_send():
    """
    Envia uma nova mensagem para o chat.
    - Requer autenticação obrigatória.
    - Recebe a mensagem do formulário.
    - Gera ID único incremental para a mensagem.
    - Regista timestamp actual no formato 'AAAA-MM-DD HH:MM:SS'.
    - Guarda mensagem no ficheiro chat.csv com: id, user, time, message.
    - Redireciona de volta para a página do chat.
    """
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    message = request.form.get("message")
    if not message:
        return redirect("/chat")
    
    new_id = len(read_csv(CHAT_FILE)) + 1
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    append_csv(CHAT_FILE, ["id", "user", "time", "message"], [new_id, session["user"], current_time, message])
    return redirect("/chat")

@app.route("/favourites")
def favourites():
    """
    Página de gestão de músicas favoritas.
    - Requer autenticação obrigatória.
    - Lista apenas os favoritos do utilizador actual.
    - Enriquece dados com informações do spotify.csv (artista, álbum, ano, etc).
    - Suporta filtros opcionais: reproduções mínimas, ano mínimo e máximo.
    - Apresenta tabela formatada com botão de remover para cada favorito.
    - Mostra mensagem se não houver favoritos guardados.
    """
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    min_plays = request.args.get('min_plays', type=int)
    min_year = request.args.get('min_year', type=int)
    max_year = request.args.get('max_year', type=int)
    
    user_favourites = [row for row in read_csv(FAVOURITES_FILE) if row['user'] == session['user']]
    enriched_favourites = []
    
    if user_favourites and os.path.exists(SPOTIFY_CSV):
        df = pd.read_csv(SPOTIFY_CSV)
        
        for fav in user_favourites:
            song_data = df[df['track_name'] == fav['song']]
            
            if not song_data.empty:
                song_info = song_data.iloc[0]
                play_count = song_info.get('play_count', 0)
                year = song_info.get('year', 0)
                
                if (min_plays and play_count < min_plays) or (min_year and year < min_year) or (max_year and year > max_year):
                    continue
                
                enriched_favourites.append({
                    'id': fav['id'],
                    'song': fav['song'],
                    'artist': song_info.get('artist', 'N/A'),
                    'album': song_info.get('album', 'N/A'),
                    'year': song_info.get('year', 'N/A'),
                    'play_count': song_info.get('play_count', 'N/A'),
                    'duration_min': round(song_info.get('duration_ms', 0) / 60000, 2) if 'duration_ms' in song_info else 'N/A'
                })
            else:
                enriched_favourites.append({
                    'id': fav['id'], 'song': fav['song'], 'artist': 'N/A', 
                    'album': 'N/A', 'year': 'N/A', 'play_count': 'N/A', 'duration_min': 'N/A'
                })
    
    return render_template("favourites.html", user=session["user"], favourites=enriched_favourites,
                         min_plays=min_plays, min_year=min_year, max_year=max_year)

@app.route("/favourites/add", methods=["POST"])
def favourites_add():
    """
    Adiciona uma música aos favoritos do utilizador.
    - Requer autenticação obrigatória.
    - Recebe o nome da música do formulário.
    - Gera ID único incremental.
    - Guarda no ficheiro favourites.csv com: id, user, song.
    - Redireciona para a página de favoritos.
    Chamado pelos botões de coração na tabela do dashboard.
    """
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    song = request.form.get("song")
    if song:
        new_id = len(read_csv(FAVOURITES_FILE)) + 1
        append_csv(FAVOURITES_FILE, ["id", "user", "song"], [new_id, session["user"], song])
    return redirect("/favourites")

@app.route("/favourites/remove/<fav_id>", methods=["POST"])
def favourites_remove(fav_id):
    """
    Remove uma música dos favoritos.
    - Requer autenticação obrigatória.
    - Apenas o dono do favorito pode removê-lo (verificação de segurança).
    - Lê todos os favoritos, filtra removendo apenas o especificado.
    - Reescreve o ficheiro CSV sem o favorito removido.
    - Redireciona de volta para a página de favoritos.
    Chamado pelos botões 'Remover' na tabela de favoritos.
    """
    auth_check = require_auth()
    if auth_check:
        return auth_check
    
    favourites = [row for row in read_csv(FAVOURITES_FILE) 
                  if row['id'] != fav_id or row['user'] != session['user']]
    rows = [[fav['id'], fav['user'], fav['song']] for fav in favourites]
    write_csv(FAVOURITES_FILE, ['id', 'user', 'song'], rows)
    return redirect("/favourites")

@app.route("/logout")
def logout():
    """
    Termina a sessão do utilizador (logout).
    - Limpa todos os dados da sessão (nome e role).
    - Redireciona para a página de login.
    - Após logout, o utilizador precisa autenticar-se novamente.
    """
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
    # Executa a app em modo de desenvolvimento (debug=True) localmente.
    app.run(debug=True)
