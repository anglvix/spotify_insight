CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    email VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    role VARCHAR(20)
);

CREATE TABLE datasets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100),
    ficheiro VARCHAR(200)
);

CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(100)
);

CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    dataset_id INT,
    texto TEXT,
    data TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    mensagem TEXT,
    lida BOOLEAN DEFAULT FALSE
);

INSERT INTO users (nome,email,password,role)
VALUES ('Admin','admin@teste.com','1234','admin');
