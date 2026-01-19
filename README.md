# Spotify Insight

Aplicação web desenvolvida com Flask para análise e visualização de dados do Spotify. Permite aos utilizadores explorar estatísticas musicais, gerir favoritos e interagir através de um sistema de chat.

## 🚀 Como Executar o Projeto

### Pré-requisitos

- Python 3.7 ou superior instalado
- Acesso à linha de comandos (CMD, PowerShell ou Terminal)

### Passo 1: Instalar Dependências

O projeto utiliza as seguintes bibliotecas Python:
- **Flask** - Framework web
- **Pandas** - Manipulação e análise de dados
- **Plotly** - Visualização de dados interativa

Para instalar todas as dependências automaticamente, execute o seguinte comando na raiz do projeto:

```bash
pip install flask pandas plotly
```

Ou, se preferir usar o ficheiro de dependências:

```bash
pip install -r requirements.txt
```

### Passo 2: Iniciar o Servidor

Após instalar as dependências, inicie a aplicação com o comando:

```bash
python app.py
```

### Passo 3: Aceder à Aplicação

Abra o navegador e aceda a:

```
http://127.0.0.1:5000
```

ou

```
http://localhost:5000
```

## 📋 Funcionalidades

- **Dashboard**: Visualização de estatísticas musicais com gráficos interactivos
- **Favoritos**: Sistema de gestão de músicas favoritas
- **Chat**: Sistema de mensagens para utilizadores autenticados
- **Painel de Administração**: Gestão completa de utilizadores
- **Filtros**: Filtros avançados por reproduções, ano e pesquisa

## 👤 Credenciais de Acesso

### Conta de Administrador
- **E-mail**: admin@admin.com
- **Palavra-passe**: 1234

### Criar Nova Conta
Os utilizadores podem registar-se directamente através da página de registo.

## 📁 Estrutura do Projeto

```
spotify_insight/
├── app.py                 # Aplicação principal Flask
├── requirements.txt       # Dependências do projeto
├── datasets/              # Ficheiros CSV com dados
│   ├── users.csv         # Utilizadores registados
│   ├── spotify.csv       # Dataset de músicas do Spotify
│   ├── chat.csv          # Mensagens do chat
│   └── favourites.csv    # Músicas favoritas dos utilizadores
├── templates/            # Templates HTML
│   ├── landingpage.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── favourites.html
│   ├── chat.html
│   ├── admin.html
│   └── navbar.html
└── static/              # Ficheiros estáticos
    ├── style.css
    └── images/
```

## 🛠️ Tecnologias Utilizadas

- **Backend**: Flask (Python)
- **Frontend**: HTML5, Tailwind CSS
- **Visualização**: Plotly Express
- **Análise de Dados**: Pandas
- **Armazenamento**: CSV